# Use the official Python 3.12 image as the base image
FROM python:3.12.4-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV AZURE_STORAGE_CONNECTION_STRING="AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;DefaultEndpointsProtocol=http;BlobEndpoint=http://host.docker.internal:10000/devstoreaccount1;QueueEndpoint=http://host.docker.internal:10001/devstoreaccount1;TableEndpoint=http://host.docker.internal:10002/devstoreaccount1;"
ENV AZURE_CONTAINER_NAME=backup
ENV RETENTION_PERIOD_DAYS=30
ENV BACKUP_DIRECTORY=/backup

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt /app/

# Install the required dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source files
COPY src/ /app/

# Copy the script to run the application
COPY scripts/entry-point.sh /app/
RUN chmod +x /app/entry-point.sh

# Command to run the application (You can change this according to your application entry point)
CMD ["ash", "entry-point.sh"]
