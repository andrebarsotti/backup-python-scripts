# andrebarsotti/azure-blob-backup

This Docker image provides a solution for managing backups with Azure Blob Storage. It supports backing up local directories to Azure Blob Storage and cleaning up old backups based on a defined retention period.

## Features

- Backup local directories to Azure Blob Storage.
- Clean up old backups from Azure Blob Storage based on a specified retention period.

## Environment Variables

Configure the following environment variables to set up the container:

- **AZURE_STORAGE_CONNECTION_STRING**: Connection string for Azure Storage.
- **AZURE_CONTAINER_NAME**: Name of the Azure container where backups will be stored. Default is `backup`.
- **RETENTION_PERIOD_DAYS**: Number of days to retain backups. Default is 30.
- **BACKUP_DIRECTORY**: The directory where backups are stored on the image. Default is `/backup`.

## Usage

### Running the Docker Container

To run the Docker container with the required environment variables, use:

```bash
docker run --rm \
           -e AZURE_STORAGE_CONNECTION_STRING='<your_connection_string>' \
           -e AZURE_CONTAINER_NAME='<your_container_name>' \
           -e RETENTION_PERIOD_DAYS=<retention_days> \
           -e BACKUP_DIRECTORY='<path_to_backup_directory>' \
           -v <path_to_backup_directory>:/backup \
           --add-host=host.docker.internal:host-gateway \
           andrebarsotti/azure-blob-backup
```

### Example

To back up a directory and clean up old backups older than 30 days, you might use:

```bash
docker run --rm \
           -e AZURE_STORAGE_CONNECTION_STRING='your_azure_connection_string' \
           -e AZURE_CONTAINER_NAME='backup' \
           -e RETENTION_PERIOD_DAYS=30 \
           -e BACKUP_DIRECTORY='/backup' \
           -v /path/to/local/directory:/backup \
           --add-host=host.docker.internal:host-gateway \
           andrebarsotti/azure-blob-backup
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.
