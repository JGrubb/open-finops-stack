#!/bin/bash
# Docker wrapper for Open FinOps Stack pipeline commands
# Usage: ./finops-docker.sh aws import-cur

set -e

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check if config.toml exists
if [ ! -f "./config.toml" ]; then
    echo "Warning: config.toml not found in current directory"
    echo "Make sure you have a valid configuration file"
fi

# Create data directory if it doesn't exist
mkdir -p ./data
mkdir -p ./tmp

# Build the image if it doesn't exist
if ! docker image inspect finops-pipeline &> /dev/null; then
    echo "Building FinOps pipeline Docker image..."
    docker build -t finops-pipeline .
fi

# Run the command with proper volume mounts and environment variables
echo "Running: finops $*"
docker run --rm \
    -v "$(pwd)/data:/data" \
    -v "$(pwd)/config.toml:/app/config.toml:ro" \
    -v "$(pwd)/tmp:/tmp" \
    -e AWS_ACCESS_KEY_ID \
    -e AWS_SECRET_ACCESS_KEY \
    -e AWS_SESSION_TOKEN \
    -e AWS_REGION \
    -e AWS_PROFILE \
    -e OPEN_FINOPS_AWS_BUCKET \
    -e OPEN_FINOPS_AWS_PREFIX \
    -e OPEN_FINOPS_AWS_EXPORT_NAME \
    -e OPEN_FINOPS_AWS_CUR_VERSION \
    -e OPEN_FINOPS_DATA_DIR \
    finops-pipeline "$@"