#!/usr/bin/env python3
import os
import tarfile
import argparse
import logging
from progress_file_wrapper import ProgressFileWrapper
from azure.storage.blob import BlobServiceClient, ContentSettings
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm

def setup_logging():
    """
    Configure the logging settings.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Suppress logs from the Azure SDK
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
    logging.getLogger('azure.storage.blob').setLevel(logging.WARNING)


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

    :return: The directory to backup.
    """
    parser = argparse.ArgumentParser(description="Backup a directory and upload to Azure Blob Storage.")
    parser.add_argument('directory', type=str, help='The directory to backup')
    args = parser.parse_args()
    logging.info(f"Command line arguments parsed: {args.directory}")

    return args.directory


def create_backup(directory):
    """
    Create a backup for the specified directory and return the backup filename.

    :param directory: The directory to backup.
    :return: The name of the backup file.
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    backup_filename = f"{os.path.basename(directory)}_{timestamp}.tgz"
    create_tgz_backup(directory, backup_filename)
    return backup_filename


def upload_backup_to_azure(blob_service_client, container_name, backup_filename):
    """
    Upload the backup file to Azure Blob Storage.

    :param blob_service_client: BlobServiceClient instance.
    :param container_name: Name of the Azure container.
    :param backup_filename: The name of the backup file to upload.
    """
    ensure_container_exists(blob_service_client, container_name)
    
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=backup_filename)
    
    with open(backup_filename, "rb") as data:
        file_size = data.seek(0, 2)  # Seek to end of file to get its size
        data.seek(0)  # Reset to beginning
        
        progress_bar = tqdm(total=file_size, unit='B', unit_scale=True, desc=backup_filename)
        
        # Wrap the file with the progress bar
        progress_file = ProgressFileWrapper(data, progress_bar)
        
        # Upload the file to Azure Blob Storage
        blob_client.upload_blob(progress_file, overwrite=True, 
                                content_settings=ContentSettings(content_type='application/octet-stream'))
        
        progress_bar.close()


def cleanup_local_backup(backup_filename):
    """
    Remove the local backup file to save space after upload.

    :param backup_filename: The name of the backup file to remove.
    """
    logging.info(f"Cleaning up local backup file: {backup_filename}")
    os.remove(backup_filename)
    logging.info("Local backup file removed")


def main():
    """
    Main entry point of the script.
    """
    setup_logging()
    try:
        connection_string, container_name = load_environment_variables()
        directory = parse_command_line_arguments()
        backup_filename = create_backup(directory)

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        upload_backup_to_azure(blob_service_client, container_name, backup_filename)

        cleanup_local_backup(backup_filename)
    except Exception as e:
        logging.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
   
