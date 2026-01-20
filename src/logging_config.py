#!/usr/bin/env python3
"""
Shared logging configuration module for backup scripts.

Provides configurable file logging with LOG_DIR environment variable support.
"""
import os
import logging
from datetime import datetime
from pathlib import Path

DEFAULT_LOG_DIR = "/var/log/backup-scripts"
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'


def get_log_directory():
    """
    Determine the log directory based on LOG_DIR environment variable.

    Returns:
        str or None: Path to log directory, or None if file logging is disabled.
        - If LOG_DIR is explicitly empty string: returns None (disable file logging)
        - If LOG_DIR is set: returns that value
        - If running in Docker: returns DEFAULT_LOG_DIR
        - Otherwise: returns './logs' for standalone execution
    """
    log_dir = os.getenv('LOG_DIR')
    if log_dir == '':  # Explicitly empty = disable file logging
        return None
    if log_dir:
        return log_dir
    # Default based on environment
    if os.path.exists('/.dockerenv'):
        return DEFAULT_LOG_DIR
    return './logs'


def ensure_log_directory(log_dir):
    """
    Create the log directory if it doesn't exist and verify write access.

    Args:
        log_dir: Path to the log directory.

    Returns:
        bool: True if directory exists and is writable, False otherwise.
    """
    try:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        test_file = Path(log_dir) / '.write_test'
        test_file.touch()
        test_file.unlink()
        return True
    except (PermissionError, OSError):
        return False


def setup_logging(script_name):
    """
    Configure logging with both console and optional file handlers.

    Logs always go to console (for docker logs compatibility).
    File logging is enabled based on LOG_DIR environment variable.

    Args:
        script_name: Name of the script (used for log file naming).
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # Console handler (always)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)

    # File handler (optional)
    log_dir = get_log_directory()
    if log_dir and ensure_log_directory(log_dir):
        date_str = datetime.now().strftime('%Y-%m-%d')
        log_path = Path(log_dir) / f"{script_name}_{date_str}.log"
        try:
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(file_handler)
            logging.info(f"Logging to file: {log_path}")
        except (PermissionError, OSError) as e:
            logging.warning(f"Cannot create log file: {e}. Using console only.")
    elif log_dir:
        logging.warning(f"Cannot write to log directory '{log_dir}'. Using console only.")

    # Suppress Azure SDK noise
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
    logging.getLogger('azure.storage.blob').setLevel(logging.WARNING)
