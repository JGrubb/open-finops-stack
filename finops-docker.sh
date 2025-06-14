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

# Run the command with proper volume mounts
echo "Running: finops $*"
docker run --rm \
    -v "$(pwd)/data:/data" \
    -v "$(pwd)/config.toml:/app/config.toml:ro" \
    -v "$(pwd)/tmp:/tmp" \
    finops-pipeline "$@"