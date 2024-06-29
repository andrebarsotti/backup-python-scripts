#!/usr/bin/env python3
import os
import argparse
import logging
from datetime import datetime, timedelta, timezone
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Suppress logs from the Azure SDK
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
    logging.getLogger('azure.storage.blob').setLevel(logging.WARNING)    

def remove_old_blobs(blob_service_client, container_name, days):
    logging.info(f"Removing blobs older than {days} days from container: {container_name}")
    container_client = blob_service_client.get_container_client(container_name)
    blobs_list = container_client.list_blobs()

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    logging.info(f"Cutoff date: {cutoff_date}")
    
    for blob in blobs_list:
        blob_client = container_client.get_blob_client(blob)
        blob_properties = blob_client.get_blob_properties()
        blob_last_modified = blob_properties['last_modified']

        # Ensure both are offset-aware for proper comparison
        if blob_last_modified < cutoff_date:
            logging.info(f"Deleting blob: {blob.name}, Last Modified: {blob_last_modified}")
            blob_client.delete_blob()

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
    parser = argparse.ArgumentParser(description="Remove old files from Azure Blob Storage.")
    parser.add_argument('days', type=int, help='The number of days to retain files')
    args = parser.parse_args()
    logging.info(f"Command line arguments parsed: {args.days} days")

    return args.days

def main():
    setup_logging()
    try:
        connection_string, container_name = load_environment_variables()
        days = parse_command_line_arguments()

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        remove_old_blobs(blob_service_client, container_name, days)
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
