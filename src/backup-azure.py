#!/usr/bin/env python3
import os
import tarfile
import argparse
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

def create_tgz_backup(directory, output_filename):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(directory, arcname=os.path.basename(directory))

def upload_to_azure(blob_service_client, container_name, blob_name, file_path):
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    with open(file_path, "rb") as data:
        blob_client.upload_blob(data)

def main():
    # Load environment variables from .env file
    load_dotenv()
    connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    container_name = os.getenv('AZURE_CONTAINER_NAME')

    if not connection_string or not container_name:
        raise ValueError("Please set the AZURE_STORAGE_CONNECTION_STRING and AZURE_CONTAINER_NAME environment variables.")

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Backup a directory and upload to Azure Blob Storage.")
    parser.add_argument('directory', type=str, help='The directory to backup')
    args = parser.parse_args()

    directory = args.directory
    backup_filename = f"{os.path.basename(directory)}.tgz"

    # Create a backup
    create_tgz_backup(directory, backup_filename)

    # Connect to Azure Blob Storage
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    # Upload the backup file to Azure Blob Storage
    upload_to_azure(blob_service_client, container_name, backup_filename, backup_filename)

    # Cleanup the local backup file
    os.remove(backup_filename)

if __name__ == "__main__":
    main()
