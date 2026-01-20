#!/usr/bin/env python3
import os
import tarfile
import argparse
import logging
from logging_config import setup_logging
from progress_file_wrapper import ProgressFileWrapper
from azure.storage.blob import BlobServiceClient, ContentSettings
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm


def get_size(start_path='.'):
    """
    Calculate the total size of the directory including its subdirectories.

    :param start_path: Path of the directory to calculate the size of.
    :return: Total size in bytes.
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


def get_output_directory():
    """
    Get output directory from BACKUP_OUTPUT_DIR environment variable.

    :return: Path to output directory, or None to use current directory.
    """
    return os.getenv('BACKUP_OUTPUT_DIR') or None


def ensure_output_directory(output_dir):
    """
    Create output directory if it doesn't exist and verify write access.

    :param output_dir: Path to the output directory.
    :return: True if directory exists and is writable.
    :raise ValueError: if directory cannot be created or is not writable.
    """
    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        test_file = Path(output_dir) / '.write_test'
        test_file.touch()
        test_file.unlink()
        return True
    except (OSError) as e:
        raise ValueError(f"Cannot write to output directory '{output_dir}': {e}")


def create_tgz_backup(directory, output_filename):
    """
    Create a compressed tar.gz backup of the specified directory.

    :param directory: The directory to backup.
    :param output_filename: The name of the output tar.gz file.
    """
    logging.info(f"Creating backup for directory: {directory}")
    total_size = get_size(directory)
    progress_bar = tqdm(total=total_size, unit='B', unit_scale=True, desc="Creating Backup")
    
    with tarfile.open(name=output_filename, mode="w:gz", compresslevel=9) as tar:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                tarinfo = tar.gettarinfo(filepath, arcname=os.path.relpath(filepath, directory))
                with open(filepath, "rb") as file:
                    progress_bar.update(tarinfo.size)  # Updating progress bar with file size
                    tar.addfile(tarinfo, file)
    
        progress_bar.close()
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
    except Exception:
        logging.info(f"Container {container_name} does not exist, creating it.")
        container_client.create_container()
        logging.info(f"Container {container_name} created.")


def load_environment_variables():
    """
    Load Azure storage connection string and container name from the environment variables.

    :return: Tuple containing connection_string and container_name.
    :raise ValueError: if environment variables are not set.
    """
    load_dotenv()
    connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    container_name = os.getenv('AZURE_CONTAINER_NAME')

    if not connection_string or not container_name:
        logging.error("Azure environment variables are not set properly")
        raise ValueError("Please set the AZURE_STORAGE_CONNECTION_STRING and AZURE_CONTAINER_NAME environment variables.")
    
    logging.info("Environment variables loaded successfully")
    return connection_string, container_name

def parse_command_line_arguments():
    """
    Parse command line arguments.

    :return: Tuple of (directory, output_dir) where output_dir may be None.
    """
    parser = argparse.ArgumentParser(description="Backup a directory and upload to Azure Blob Storage.")
    parser.add_argument('directory', type=str, help='The directory to backup')
    parser.add_argument('-o', '--output-dir', type=str, default=None,
                        help='Directory to save the backup tar file before upload (default: current directory)')
    args = parser.parse_args()
    logging.info(f"Command line arguments parsed: directory={args.directory}, output_dir={args.output_dir}")

    return args.directory, args.output_dir


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
    """
    setup_logging('backup-azure')
    try:
        connection_string, container_name = load_environment_variables()
        directory, cli_output_dir = parse_command_line_arguments()

        # Determine output directory: CLI takes precedence over env var
        output_dir = cli_output_dir or get_output_directory()
        if output_dir:
            ensure_output_directory(output_dir)
            logging.info(f"Using output directory: {output_dir}")

        backup_filepath, backup_filename = create_backup(directory, output_dir)

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        upload_backup_to_azure(blob_service_client, container_name, backup_filepath, backup_filename)

        cleanup_local_backup(backup_filepath)
    except Exception as e:
        logging.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
   
