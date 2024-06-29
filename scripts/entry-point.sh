#!/bin/sh

# Check if the Python scripts are present in the src directory
if [ ! -f "/app/backup-azure.py" ] || [ ! -f "/app/cleanup-azure.py" ]; then
    echo "Python scripts not found in the app directory."
    exit 1
fi

# Check if the required environment variables are set
if [ -z "$AZURE_STORAGE_CONNECTION_STRING" ] || [ -z "$AZURE_CONTAINER_NAME" ]; then
    echo "Please set the AZURE_STORAGE_CONNECTION_STRING and AZURE_CONTAINER_NAME environment variables."
    exit 1
fi

# Check if BACKUP_DIRECTORY environment variable is set
if [ -z "$BACKUP_DIRECTORY" ]; then
    echo "Please set the BACKUP_DIRECTORY environment variable."
    exit 1
fi

# Check if RETENTION_PERIOD_DAYS environment variable is set
if [ -z "$RETENTION_PERIOD_DAYS" ]; then
    echo "Please set the RETENTION_PERIOD_DAYS environment variable."
    exit 1
fi

# Function to run the backup script
run_backup_script() {
    echo "Running backup script with BACKUP_DIRECTORY=${BACKUP_DIRECTORY}..."
    python3 /app/backup-azure.py "$BACKUP_DIRECTORY"
    if [ $? -eq 0 ]; then
        echo "Backup script ran successfully."
    else
        echo "Backup script encountered an error."
        exit 1
    fi
}

# Function to run the cleanup script
run_cleanup_script() {
    echo "Running cleanup script with RETENTION_PERIOD_DAYS=${RETENTION_PERIOD_DAYS}..."
    python3 /app/cleanup-azure.py "$RETENTION_PERIOD_DAYS"
    if [ $? -eq 0 ]; then
        echo "Cleanup script ran successfully."
    else
        echo "Cleanup script encountered an error."
        exit 1
    fi
}

# Run the backup and cleanup scripts
run_backup_script
run_cleanup_script

echo "Scripts executed successfully."
