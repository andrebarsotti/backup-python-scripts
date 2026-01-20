# CLAUDE.MD - AI Assistant Guide

## Project Overview

This is an Azure Backup Management system that provides automated backup and cleanup functionality for local directories using Azure Blob Storage. The project is containerized with Docker and supports both local development (using Azurite emulator) and production Azure environments.

**Key Capabilities:**
- Create compressed tar.gz backups of local directories
- Upload backups to Azure Blob Storage with progress tracking
- Automated cleanup of old backups based on retention policies
- Docker containerization for easy deployment
- Support for local development with Azurite emulator

## Architecture & Components

### Core Scripts

1. **backup-azure.py** (src/backup-azure.py:1-184)
   - Main backup orchestration script
   - Creates compressed tar.gz archives of specified directories
   - Uploads backups to Azure Blob Storage with progress bars
   - Cleans up local backup files after successful upload
   - Entry point: `main()` function at line 164

2. **cleanup-azure.py** (src/cleanup-azure.py:1-113)
   - Retention policy enforcement script
   - Removes blobs older than specified retention period
   - Uses timezone-aware datetime comparisons
   - Entry point: `main()` function at line 92

3. **progress_file_wrapper.py** (src/progress_file_wrapper.py)
   - Utility for displaying upload progress
   - Wraps file objects to track bytes transferred

4. **logging_config.py** (src/logging_config.py)
   - Shared logging configuration module
   - Configurable file logging via LOG_DIR environment variable
   - Supports dual output: console + file (for docker logs compatibility)
   - Graceful fallback to console-only if file logging fails

### Docker Configuration

- **Base Image:** python:3.12.4-alpine
- **Entry Point:** scripts/entry-point.sh
- **Default Container:** Azurite emulator for local development
- **Network:** Uses host.docker.internal for accessing local Azurite

## Code Structure

```
/home/user/backup-python-scripts/
├── src/
│   ├── backup-azure.py          # Main backup script
│   ├── cleanup-azure.py         # Cleanup script
│   ├── logging_config.py        # Shared logging configuration
│   └── progress_file_wrapper.py # Progress tracking utility
├── scripts/
│   └── entry-point.sh           # Docker entrypoint
├── Dockerfile                   # Container definition
├── docker-compose.dev.yml       # Local development setup
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (not committed)
└── README.md                    # User documentation
```

## Key Functions Reference

### backup-azure.py

- **`get_output_directory()`** (line 30)
  - Gets output directory from BACKUP_OUTPUT_DIR environment variable
  - Returns: Path to output directory, or None for current directory

- **`ensure_output_directory(output_dir)`** (line 39)
  - Creates output directory if it doesn't exist
  - Verifies write permissions with test file
  - Raises ValueError if directory cannot be created or is not writable

- **`create_tgz_backup(directory, output_filename)`** (line 57)
  - Creates compressed tar.gz backup with progress tracking
  - Uses compression level 9 for maximum compression
  - Returns: None (creates file on disk)

- **`create_backup(directory, output_dir=None)`** (line 133)
  - Creates backup for specified directory
  - Returns: Tuple of (backup_filepath, backup_filename)
  - filepath: Full path for local file operations
  - filename: Just the name for Azure blob

- **`upload_backup_to_azure(blob_service_client, container_name, backup_filepath, blob_name)`** (line 154)
  - Uploads backup file to Azure with progress bar
  - Automatically creates container if it doesn't exist
  - Uses ProgressFileWrapper for upload tracking
  - backup_filepath: Local file path to upload
  - blob_name: Name for the blob in Azure (typically just the filename)

- **`ensure_container_exists(blob_service_client, container_name)`** (line 62)
  - Checks for container existence
  - Creates container if missing
  - Idempotent operation

- **`load_environment_variables()`** (line 80)
  - Loads .env file
  - Validates required variables: AZURE_STORAGE_CONNECTION_STRING, AZURE_CONTAINER_NAME
  - Raises ValueError if variables are missing

### cleanup-azure.py

- **`remove_old_blobs(blob_service_client, container_name, days)`** (line 11)
  - Deletes blobs older than specified retention period
  - Uses timezone-aware datetime for accurate comparisons
  - Logs each deletion operation

### logging_config.py

- **`get_log_directory()`** (line 17)
  - Determines log directory from LOG_DIR environment variable
  - Returns None if LOG_DIR is empty string (disables file logging)
  - Defaults to `/var/log/backup-scripts` in Docker, `./logs` standalone

- **`ensure_log_directory(log_dir)`** (line 38)
  - Creates log directory if it doesn't exist
  - Verifies write permissions with test file
  - Returns True if directory is writable, False otherwise

- **`setup_logging(script_name)`** (line 56)
  - Configures console handler (always enabled)
  - Configures file handler (if LOG_DIR is set and writable)
  - Log files named: `{script_name}_{YYYY-MM-DD}.log`
  - Suppresses Azure SDK noise

## Environment Variables

Required variables (must be set in .env or environment):

```env
AZURE_STORAGE_CONNECTION_STRING  # Azure connection string or Azurite default
AZURE_CONTAINER_NAME             # Container name (default: backup)
RETENTION_PERIOD_DAYS            # Days to retain backups (default: 30)
BACKUP_DIRECTORY                 # Directory to backup (default: /backup)
LOG_DIR                          # Log directory (default: /var/log/backup-scripts in Docker, ./logs standalone)
BACKUP_OUTPUT_DIR                # Output directory for backup tar files before upload (default: current directory)
```

**LOG_DIR Options:**
- Set to a path: Logs written to `{LOG_DIR}/{script}_{date}.log`
- Set to empty string (`LOG_DIR=""`): Disables file logging
- Unset: Uses default based on environment detection

**BACKUP_OUTPUT_DIR Options:**
- Set to a path: Backup tar files created in specified directory
- Unset: Uses current directory (default behavior)
- Can be overridden by `-o/--output-dir` CLI argument

**Azurite Default Connection String:**
```
AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;DefaultEndpointsProtocol=http;BlobEndpoint=http://host.docker.internal:10000/devstoreaccount1;QueueEndpoint=http://host.docker.internal:10001/devstoreaccount1;TableEndpoint=http://host.docker.internal:10002/devstoreaccount1;
```

## Development Guidelines

### Code Style
- Python 3.12+ compatible
- Uses type hints in docstrings (Google-style)
- Comprehensive logging with INFO level
- Azure SDK logs suppressed to WARNING level
- All functions have descriptive docstrings

### Logging Strategy
- Centralized in `logging_config.py` module (shared by all scripts)
- Dual output: console (always) + file (configurable via LOG_DIR)
- Format: `'%(asctime)s - %(levelname)s - %(message)s'`
- Daily log files: `{script_name}_{YYYY-MM-DD}.log`
- Azure SDK noise suppressed for cleaner output
- Graceful fallback to console-only if file logging fails
- Key operations logged: backup creation, uploads, deletions

### Error Handling
- All main functions wrapped in try/except blocks
- Errors logged before re-raising or exiting
- Validation of environment variables before operations

## Common Tasks

### Adding New Backup Features
1. Add function to backup-azure.py
2. Update `main()` to call new function
3. Add appropriate logging
4. Update README.md usage section

### Modifying Retention Logic
- Edit `remove_old_blobs()` in cleanup-azure.py (line 20)
- Ensure timezone-aware datetime usage
- Test with Azurite before production deployment

### Adding New Environment Variables
1. Update Dockerfile default ENV values
2. Update load_environment_variables() functions
3. Document in README.md Environment Variables section
4. Update example .env in documentation

### Testing Locally
1. Start Azurite: `docker-compose -f docker-compose.dev.yml up -d`
2. Create .env with Azurite connection string
3. Run scripts directly: `python src/backup-azure.py /path/to/backup`
4. With custom output directory: `python src/backup-azure.py /path/to/backup -o /tmp/backups`
5. Verify with Azure Storage Explorer

## Docker Operations

### Building
```bash
docker build -t andrebarsotti/azure-blob-backup .
```

### Running
```bash
docker run --rm \
  -e AZURE_STORAGE_CONNECTION_STRING='<connection_string>' \
  -e AZURE_CONTAINER_NAME='<container_name>' \
  -e RETENTION_PERIOD_DAYS=<days> \
  -e BACKUP_DIRECTORY='<directory>' \
  -e BACKUP_OUTPUT_DIR='/tmp/backups' \
  -v <local_path>:/backup \
  -v <log_path>:/var/log/backup-scripts \
  --add-host=host.docker.internal:host-gateway \
  andrebarsotti/azure-blob-backup
```

**Note:** Mount a volume to `/var/log/backup-scripts` to persist logs outside the container. Set `BACKUP_OUTPUT_DIR` to control where temporary backup tar files are created before upload.

## Dependencies

**Key Libraries:**
- `azure-storage-blob`: Azure Blob Storage operations
- `python-dotenv`: Environment variable management
- `tqdm`: Progress bar display
- `argparse`: Command-line argument parsing

See requirements.txt for complete dependency list.

## Branch Strategy

- **Main Branch:** Production-ready code
- **Feature Branches:** Use `claude/<feature-name>-<session-id>` pattern
- All changes should be committed and pushed to feature branches
- Create pull requests for merging to main

## Testing Checklist

When making changes, verify:
- [ ] Scripts run successfully with Azurite locally
- [ ] Progress bars display correctly during operations
- [ ] Logging output is clear and informative
- [ ] Log files created in LOG_DIR with correct naming
- [ ] File logging gracefully fails with warning if directory not writable
- [ ] Environment variables are properly validated
- [ ] Docker image builds without errors
- [ ] Entry point script executes both backup and cleanup
- [ ] Error handling works for missing variables/permissions

## Known Patterns

### Backup Filename Format
- Pattern: `{directory_basename}_{timestamp}.tgz`
- Timestamp format: `YYYYMMDDHHMMSS`
- Example: `mydata_20260120143052.tgz`

### Log Filename Format
- Pattern: `{script_name}_{date}.log`
- Date format: `YYYY-MM-DD`
- Example: `backup-azure_2026-01-20.log`

### Blob Deletion Logic
- Uses `last_modified` property of blobs
- Compares with `datetime.now(timezone.utc) - timedelta(days=days)`
- Timezone-aware comparison required for accuracy

### Progress Tracking
- Two progress bars: one for backup creation, one for upload
- Uses tqdm library
- ProgressFileWrapper enables upload progress tracking

## Security Considerations

- Never commit .env files with real credentials
- Use Azure Key Vault for production credentials
- Azurite credentials are public (development only)
- Container creates with default permissions
- Connection strings should be mounted as secrets in production

## Future Enhancement Ideas

- Add incremental backup support
- Implement backup verification/integrity checks
- Add email notifications for backup failures
- Support for multiple backup destinations
- Backup encryption before upload
- Restore functionality
- Backup metadata tracking (size, duration, file count)
