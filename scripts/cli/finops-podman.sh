#!/bin/bash
# Podman wrapper for Open FinOps Stack pipeline commands
# Usage: ./finops-podman.sh aws import-cur

set -e

# Check if Podman is available
if ! command -v podman &> /dev/null; then
    echo "Error: Podman is not installed or not in PATH"
    echo "Install with: brew install podman (macOS) or see https://podman.io/getting-started/installation"
    exit 1
fi

# Check if Podman machine is running (macOS only)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! podman machine list | grep -q "Currently running"; then
        echo "Error: Podman machine is not running"
        echo "Start with: podman machine start"
        exit 1
    fi
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
if ! podman image inspect finops-pipeline &> /dev/null; then
    echo "Building FinOps pipeline container image..."
    podman build -t finops-pipeline .
fi

# Run the command with proper volume mounts and environment variables
echo "Running: finops $*"
podman run --rm \
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