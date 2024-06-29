# Azure Backup Management

This project provides scripts to manage backups with Azure Blob Storage. It includes functionality to back up a local directory to Azure Blob Storage and to clean up old backups from Azure Blob Storage.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Usage](#usage)
  - [Backup Script](#backup-script)
  - [Cleanup Script](#cleanup-script)
- [Docker Setup](#docker-setup)
- [Contributing](#contributing)
- [License](#license)

## Overview

This project aims to facilitate the backup of local directories to Azure Blob Storage. It includes two main scripts:

1. **`backup-azure.py`**: This script backs up a specified local directory to Azure Blob Storage.
2. **`cleanup-azure.py`**: This script removes old files from Azure Blob Storage based on a specified retention period.

## Prerequisites

Before you begin, ensure you have the following installed on your machine:

- Python 3.6 or higher
- Docker (for setting up Azurite, an Azure Storage emulator)

## Setup

1. **Install required Python packages:**

    Create and activate a virtual environment (optional, but recommended):

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

    Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

2. **Set up environment variables:**

   Create a `.env` file in the root of the repository with the following content:

    ```env
    AZURE_STORAGE_CONNECTION_STRING=<your_connection_string>
    AZURE_CONTAINER_NAME=<your_container_name>
    ```

## Usage

### Backup Script

The `backup-azure.py` script backs up a specified local directory to Azure Blob Storage.

**Command:**

```bash
python src/backup-azure.py <directory_to_backup>
```

**Example:**

```bash
python src/backup-azure.py /path/to/local/directory
```

**Code Overview:**

- `main()` function (lines 59-71) orchestrates loading environment variables, parsing command-line arguments, creating the backup, uploading it to Azure, and cleaning up local backups.
- `load_environment_variables()` function (lines 25-35) loads the necessary Azure environment variables.
- `parse_command_line_arguments()` function (lines 37-43) parses the command line and retrieves the directory to be backed up.

### Cleanup Script

The `cleanup-azure.py` script removes old files from Azure Blob Storage based on a specified retention period (in days).

**Command:**

```bash
python src/cleanup-azure.py <days>
```

**Example:**

```bash
python src/cleanup-azure.py 30
```

**Code Overview:**

- `main()` function (lines 41-45) handles loading environment variables, parsing command-line arguments, connecting to the Azure Blob Storage, and removing old blobs.
- `load_environment_variables()` function (from `backup-azure.py`, lines 25-35) loads Azure environment variables.
- `parse_command_line_arguments()` function (lines 31-36) parses the command line and retrieves the retention period.
- `remove_old_blobs()` function (lines 7-20) handles the deletion of blobs older than the specified number of days.

## Docker Setup

This project includes a `docker-compose.dev.yml` file to set up Azurite, an Azure Storage emulator, for development and testing.

**Starting Azurite:**

```bash
docker-compose -f docker-compose.dev.yml up -d
```

This will start Azurite and expose the necessary ports. You can then use Azurite's connection string in your `.env` file for local development.

## Build the Docker Image

```shell
docker build -t azure-backup-cleanup .
```

## Run the Docker Container

```shell
docker run --rm \
           -e AZURE_STORAGE_CONNECTION_STRING='<your_connection_string>' \
           -e AZURE_CONTAINER_NAME='<your_container_name>' \
           -e RETENTION_PERIOD_DAYS=<retention_days> \
           -e BACKUP_DIRECTORY='<path_to_backup_directory>' \
           -v <path_to_backup_directory>:/backup \
           --add-host=host.docker.internal:host-gateway \
           azure-backup-cleanup
```

## Environment Variables

- **AZURE_STORAGE_CONNECTION_STRING**: Connection string for Azure Storage, the default assume that you are using Azurite on localhost.
- **AZURE_CONTAINER_NAME**: The name of the Azure container where backups will be stored, the deafult is `backup`.
- **RETENTION_PERIOD_DAYS**: Number of days to retain backups, the default is 30.
- **BACKUP_DIRECTORY**: The directory where backups are stored on the image, the default is `/backup`.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository.
2. Create a new branch with your feature or bug fix.
3. Commit your changes.
4. Push the branch to your forked repository.
5. Create a Pull Request with a detailed description of your changes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
