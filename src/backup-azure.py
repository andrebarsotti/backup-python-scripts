#!/usr/bin/env python3
import os
import tarfile
import argparse
import logging
from azure.storage.blob import BlobServiceClient
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Suppress logs from the Azure SDK
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
    logging.getLogger('azure.storage.blob').setLevel(logging.WARNING)    

def get_size(start_path='.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def create_tgz_backup(directory, output_filename):
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

def upload_to_azure(blob_service_client, container_name, blob_name, file_path):
    logging.info(f"Uploading {file_path} to Azure container {container_name} as blob {blob_name}")
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    with open(file_path, "rb") as data:
        blob_client.upload_blob(data)
    logging.info(f"Upload complete for blob: {blob_name}")

def load_environment_variables():
    load_dotenv()
    connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    container_name = os.getenv('AZURE_CONTAINER_NAME')

    if not connection_string or not container_name:
        logging.error("Azure environment variables are not set properly")
        raise ValueError("Please set the AZURE_STORAGE_CONNECTION_STRING and AZURE_CONTAINER_NAME environment variables.")
    
    logging.info("Environment variables loaded successfully")
    return connection_string, container_name

def parse_command_line_arguments():
    parser = argparse.ArgumentParser(description="Backup a directory and upload to Azure Blob Storage.")
    parser.add_argument('directory', type=str, help='The directory to backup')
    args = parser.parse_args()
    logging.info(f"Command line arguments parsed: {args.directory}")

    return args.directory

def create_backup(directory):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    backup_filename = f"{os.path.basename(directory)}_{timestamp}.tgz"
    create_tgz_backup(directory, backup_filename)
    return backup_filename

def upload_backup_to_azure(blob_service_client, container_name, backup_filename):
    upload_to_azure(blob_service_client, container_name, backup_filename, backup_filename)

def cleanup_local_backup(backup_filename):
    logging.info(f"Cleaning up local backup file: {backup_filename}")
    os.remove(backup_filename)
    logging.info("Local backup file removed")

def main():
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
