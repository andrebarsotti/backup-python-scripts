#!/usr/bin/env python3
import os
import sys
import tarfile
import argparse
import logging
from logging_config import setup_logging
from progress_file_wrapper import ProgressFileWrapper
from shared_utils import (
    load_azure_environment_variables,
    ensure_directory,
    validate_directory_path,
)
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import ResourceNotFoundError
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

__all__ = [
    'get_size',
    'get_output_directory',
    'create_tgz_backup',
    'ensure_container_exists',
    'create_backup',
    'upload_backup_to_azure',
    'cleanup_local_backup',
    'main',
]


def get_size(start_path='.'):
    """
    Calculate the total size of the directory including its subdirectories.

    Handles broken symlinks and inaccessible files gracefully.

    :param start_path: Path of the directory to calculate the size of.
    :return: Total size in bytes.
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                # Skip symlinks and only count regular files
                if os.path.isfile(fp) and not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
            except OSError:
                # Skip files that can't be accessed
                logging.warning(f"Cannot access file for size calculation: {fp}")
    return total_size


def get_output_directory():
    """
    Get output directory from BACKUP_OUTPUT_DIR environment variable.

    :return: Path to output directory, or None to use current directory.
    """
    return os.getenv('BACKUP_OUTPUT_DIR') or None


def _add_file_to_tar(tar, filepath, directory, progress_bar, skipped_files):
    """
    Add a single file to the tar archive, handling errors gracefully.

    :param tar: The tar file object.
    :param filepath: The full path to the file to add.
    :param directory: The base directory for relative path calculation.
    :param progress_bar: The progress bar to update.
    :param skipped_files: List to append skipped files to.
    """
    # Skip symlinks to avoid potential issues
    if os.path.islink(filepath):
        logging.debug(f"Skipping symlink: {filepath}")
        return

    try:
        tarinfo = tar.gettarinfo(filepath, arcname=os.path.relpath(filepath, directory))
        with open(filepath, "rb") as file:
            tar.addfile(tarinfo, file)
            progress_bar.update(tarinfo.size)
    except FileNotFoundError:
        # File was deleted between os.walk and open
        skipped_files.append(filepath)
        logging.warning(f"File disappeared during backup: {filepath}")
    except PermissionError:
        skipped_files.append(filepath)
        logging.warning(f"Permission denied for file: {filepath}")
    except OSError as e:
        skipped_files.append(filepath)
        logging.warning(f"Cannot read file {filepath}: {e}")


def create_tgz_backup(directory, output_filename):
    """
    Create a compressed tar.gz backup of the specified directory.

    Handles files that are deleted or modified during backup gracefully.

    :param directory: The directory to backup.
    :param output_filename: The name of the output tar.gz file.
    """
    logging.info(f"Creating backup for directory: {directory}")
    total_size = get_size(directory)
    progress_bar = tqdm(total=total_size, unit='B', unit_scale=True, desc="Creating Backup")
    skipped_files = []

    with tarfile.open(name=output_filename, mode="w:gz", compresslevel=9) as tar:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                _add_file_to_tar(tar, filepath, directory, progress_bar, skipped_files)

    progress_bar.close()

    if skipped_files:
        logging.warning(f"Backup completed with {len(skipped_files)} skipped files")
    logging.info(f"Backup created: {output_filename}")


def ensure_container_exists(blob_service_client, container_name):
    """
    Ensure the specified Azure Blob Storage container exists. Create it if it doesn't.

    :param blob_service_client: BlobServiceClient instance.
    :param container_name: Name of the Azure container.
    """
    logging.info(f"Checking if Azure container {container_name} exists.")
    container_client = blob_service_client.get_container_client(container_name)
    try:
        container_client.get_container_properties()
        logging.info(f"Container {container_name} already exists.")
    except ResourceNotFoundError:
        logging.info(f"Container {container_name} does not exist, creating it.")
        container_client.create_container()
        logging.info(f"Container {container_name} created.")


def parse_command_line_arguments():
    """
    Parse and validate command line arguments.

    :return: Tuple of (directory, output_dir) where output_dir may be None.
    :raise ValueError: if directory path is invalid.
    """
    parser = argparse.ArgumentParser(description="Backup a directory and upload to Azure Blob Storage.")
    parser.add_argument('directory', type=str, help='The directory to backup')
    parser.add_argument('-o', '--output-dir', type=str, default=None,
                        help='Directory to save the backup tar file before upload (default: current directory)')
    args = parser.parse_args()

    # Validate directory path for security and correctness
    validated_directory = validate_directory_path(args.directory, "backup directory")
    logging.info(f"Command line arguments parsed: directory={validated_directory}, output_dir={args.output_dir}")

    return str(validated_directory), args.output_dir


def create_backup(directory, output_dir=None):
    """
    Create a backup for the specified directory and return the backup filepath and filename.

    :param directory: The directory to backup.
    :param output_dir: Optional directory to save the backup file (default: current directory).
    :return: Tuple of (backup_filepath, backup_filename) where filepath is the full path
             for local file operations and filename is just the name for Azure blob.
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    backup_filename = f"{os.path.basename(directory)}_{timestamp}.tgz"

    if output_dir:
        backup_filepath = os.path.join(output_dir, backup_filename)
    else:
        backup_filepath = backup_filename

    create_tgz_backup(directory, backup_filepath)
    return backup_filepath, backup_filename


def upload_backup_to_azure(blob_service_client, container_name, backup_filepath, blob_name):
    """
    Upload the backup file to Azure Blob Storage.

    :param blob_service_client: BlobServiceClient instance.
    :param container_name: Name of the Azure container.
    :param backup_filepath: Full path to the local backup file.
    :param blob_name: Name to use for the blob in Azure (typically just the filename).
    """
    ensure_container_exists(blob_service_client, container_name)

    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    with open(backup_filepath, "rb") as data:
        file_size = data.seek(0, 2)  # Seek to end of file to get its size
        data.seek(0)  # Reset to beginning

        progress_bar = tqdm(total=file_size, unit='B', unit_scale=True, desc=blob_name)

        # Wrap the file with the progress bar
        progress_file = ProgressFileWrapper(data, progress_bar)

        # Upload the file to Azure Blob Storage
        blob_client.upload_blob(progress_file, overwrite=True,
                                content_settings=ContentSettings(content_type='application/octet-stream'))

        progress_bar.close()


def cleanup_local_backup(backup_filepath):
    """
    Remove the local backup file to save space after upload.

    :param backup_filepath: Full path to the backup file to remove.
    """
    logging.info(f"Cleaning up local backup file: {backup_filepath}")
    os.remove(backup_filepath)
    logging.info("Local backup file removed")


def main():
    """
    Main entry point of the script.

    Returns:
        int: Exit code (0 for success, 1 for failure).
    """
    setup_logging('backup-azure')
    try:
        connection_string, container_name = load_azure_environment_variables()
        directory, cli_output_dir = parse_command_line_arguments()

        # Determine output directory: CLI takes precedence over env var
        output_dir = cli_output_dir or get_output_directory()
        if output_dir:
            ensure_directory(output_dir, "output directory")
            logging.info(f"Using output directory: {output_dir}")

        backup_filepath, backup_filename = create_backup(directory, output_dir)

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        upload_backup_to_azure(blob_service_client, container_name, backup_filepath, backup_filename)

        cleanup_local_backup(backup_filepath)
        logging.info("Backup completed successfully")
        return 0
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

