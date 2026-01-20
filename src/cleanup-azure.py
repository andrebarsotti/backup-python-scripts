#!/usr/bin/env python3
import sys
import argparse
import logging
from logging_config import setup_logging
from shared_utils import load_azure_environment_variables
from datetime import datetime, timedelta, timezone
from azure.storage.blob import BlobServiceClient

__all__ = [
    'remove_old_blobs',
    'parse_command_line_arguments',
    'main',
]


def positive_int(value):
    """
    Argparse type validator for positive integers.

    Args:
        value: The value to validate.

    Returns:
        int: The validated positive integer.

    Raises:
        argparse.ArgumentTypeError: If value is not a positive integer.
    """
    try:
        ivalue = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not valid; days must be provided as a positive integer")
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"'{value}' must be a positive integer (greater than 0)")
    return ivalue


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
    deleted_count = 0
    try:
        # Get the container client
        container_client = blob_service_client.get_container_client(container_name)

        # Calculate cutoff date
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        logging.info(f"Cutoff date: {cutoff_date}")

        # Iterate through blobs and delete if older than cutoff date
        # Use list_blobs() which already includes last_modified in blob properties
        for blob in container_client.list_blobs():
            # Access last_modified directly from blob iterator - no extra API call needed
            blob_last_modified = blob.last_modified

            if blob_last_modified < cutoff_date:
                logging.info(f"Deleting blob: {blob.name}, Last Modified: {blob_last_modified}")
                container_client.delete_blob(blob.name)
                deleted_count += 1

        logging.info(f"Cleanup complete: {deleted_count} blob(s) deleted")
    except Exception as e:
        logging.error(f"Failed to remove old blobs: {e}")
        raise


def parse_command_line_arguments():
    """
    Parses command-line arguments to get the number of days to retain blobs.

    Returns:
        int: The number of days to retain blobs.

    Raises:
        SystemExit: If days is not a positive integer.
    """
    parser = argparse.ArgumentParser(description="Remove old files from Azure Blob Storage.")
    parser.add_argument('days', type=positive_int,
                        help='The number of days to retain files (must be positive)')
    args = parser.parse_args()
    logging.info(f"Command line arguments parsed: {args.days} days")

    return args.days


def main():
    """
    Main function that sets up logging, loads environment variables, parses command-line arguments,
    and triggers the removal of old blobs from Azure Blob Storage.

    Returns:
        int: Exit code (0 for success, 1 for failure).
    """
    setup_logging('cleanup-azure')

    try:
        connection_string, container_name = load_azure_environment_variables()
        days = parse_command_line_arguments()

        # Initialize the BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)

        # Remove old blobs
        remove_old_blobs(blob_service_client, container_name, days)
        return 0
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())