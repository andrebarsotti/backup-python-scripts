#!/usr/bin/env python3
import os
import argparse
import logging
from logging_config import setup_logging
from datetime import datetime, timedelta, timezone
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv


def remove_old_blobs(blob_service_client, container_name, days):
    """
    Removes blobs older than the specified number of days from an Azure Blob Storage container.

    Args:
        blob_service_client (BlobServiceClient): The Azure BlobServiceClient object.
        container_name (str): The name of the Azure Blob Storage container.
        days (int): The number of days to retain blobs. Blobs older than this will be deleted.

    Raises:
        AzureError: If an issue occurs during blob operations.
    """
    logging.info(f"Removing blobs older than {days} days from container: {container_name}")
    try:
        # Get the container client
        container_client = blob_service_client.get_container_client(container_name)
        blobs_list = container_client.list_blobs()
        
        # Calculate cutoff date
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        logging.info(f"Cutoff date: {cutoff_date}")

        # Iterate through blobs and delete if older than cutoff date
        for blob in blobs_list:
            blob_client = container_client.get_blob_client(blob)
            blob_properties = blob_client.get_blob_properties()
            blob_last_modified = blob_properties['last_modified']

            # Ensure both dates are aware of timezone for proper comparison
            if blob_last_modified < cutoff_date:
                logging.info(f"Deleting blob: {blob.name}, Last Modified: {blob_last_modified}")
                blob_client.delete_blob()
    except Exception as e:
        logging.error(f"Failed to remove old blobs: {e}")
        raise

def load_environment_variables():
    """
    Loads environment variables from a .env file and retrieves essential Azure configuration.

    Returns:
        tuple: A tuple containing the Azure storage connection string and container name.

    Raises:
        ValueError: If the required environment variables are not set.
    """
    load_dotenv()
    
    # Retrieve environment variables
    connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    container_name = os.getenv('AZURE_CONTAINER_NAME')

    if not connection_string or not container_name:
        logging.error("Azure environment variables are not set properly")
        raise ValueError("Please set the AZURE_STORAGE_CONNECTION_STRING and AZURE_CONTAINER_NAME environment variables.")
    
    logging.info("Environment variables loaded successfully")
    return connection_string, container_name

def parse_command_line_arguments():
    """
    Parses command-line arguments to get the number of days to retain blobs.

    Returns:
        int: The number of days to retain blobs.
    """
    parser = argparse.ArgumentParser(description="Remove old files from Azure Blob Storage.")
    parser.add_argument('days', type=int, help='The number of days to retain files')
    args = parser.parse_args()
    logging.info(f"Command line arguments parsed: {args.days} days")
    
    return args.days
def main():
    """
    Main function that sets up logging, loads environment variables, parses command-line arguments,
    and triggers the removal of old blobs from Azure Blob Storage.
    """
    setup_logging('cleanup-azure')

    try:
        connection_string, container_name = load_environment_variables()
        days = parse_command_line_arguments()

        # Initialize the BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Remove old blobs
        remove_old_blobs(blob_service_client, container_name, days)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    main()