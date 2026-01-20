#!/usr/bin/env python3
"""
Shared utilities module for backup scripts.

Provides common functions used across backup and cleanup scripts.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

__all__ = [
    'load_azure_environment_variables',
    'ensure_directory',
    'validate_directory_path',
]


def load_azure_environment_variables():
    """
    Load Azure storage connection string and container name from environment variables.

    Returns:
        tuple: A tuple containing (connection_string, container_name).

    Raises:
        ValueError: If required environment variables are not set.
    """
    load_dotenv()
    connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    container_name = os.getenv('AZURE_CONTAINER_NAME')

    if not connection_string or not container_name:
        logging.error("Azure environment variables are not set properly")
        raise ValueError(
            "Please set the AZURE_STORAGE_CONNECTION_STRING and "
            "AZURE_CONTAINER_NAME environment variables."
        )

    logging.info("Environment variables loaded successfully")
    return connection_string, container_name


def ensure_directory(directory_path, purpose="directory"):
    """
    Create directory if it doesn't exist and verify write access.

    Args:
        directory_path: Path to the directory.
        purpose: Description of the directory's purpose (for error messages).

    Returns:
        bool: True if directory exists and is writable.

    Raises:
        ValueError: If directory cannot be created or is not writable.
    """
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        test_file = Path(directory_path) / '.write_test'
        test_file.touch()
        test_file.unlink()
        return True
    except (PermissionError, OSError) as e:
        raise ValueError(f"Cannot write to {purpose} '{directory_path}': {e}")


def validate_directory_path(path, argument_name="directory"):
    """
    Validate that a path exists and is a directory.

    Args:
        path: The path to validate.
        argument_name: Name of the argument (for error messages).

    Returns:
        Path: The validated path as a Path object.

    Raises:
        ValueError: If path doesn't exist, is not a directory, or contains
                   suspicious path traversal patterns.
    """
    # Check for path traversal attempts in the raw input
    if isinstance(path, (str, os.PathLike)):
        path_str = os.fspath(path)
        if '..' in path_str.split(os.sep):
            raise ValueError(
                f"Invalid {argument_name}: path traversal patterns not allowed"
            )

    path_obj = Path(path)

    if not path_obj.exists():
        raise ValueError(f"Invalid {argument_name}: path '{path}' does not exist")

    if not path_obj.is_dir():
        raise ValueError(f"Invalid {argument_name}: '{path}' is not a directory")

    # Resolve to absolute path to avoid ambiguity
    return path_obj.resolve()
