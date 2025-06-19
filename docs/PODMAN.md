# Podman Deployment Guide

This guide covers deploying the Open FinOps Stack using Podman, an open-source container runtime that serves as a drop-in replacement for Docker Desktop.

## Why Podman?

- **No licensing requirements**: Completely open source, no Docker Desktop licensing concerns
- **Daemonless architecture**: More secure, no root daemon running
- **Docker-compatible**: Works with existing Dockerfiles and docker-compose files
- **Rootless containers**: Run containers without root privileges by default

## Prerequisites

### macOS
```bash
# Install Podman and podman-compose
brew install podman podman-compose

# Initialize and start Podman machine
podman machine init
podman machine start
```

### Linux
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install podman podman-compose

# RHEL/Fedora
sudo dnf install podman podman-compose
```

## Local Development Setup

### 1. Verify Podman Installation
```bash
# Check Podman version
podman --version

# Check machine status (macOS only)
podman machine list

# Test with hello-world
podman run hello-world
```

### 2. Run the Open FinOps Stack
```bash
# Start all services
podman-compose up -d

# Check running containers
podman ps

# View logs
podman-compose logs -f

# Stop services
podman-compose down
```

### 3. Access Services
- **Metabase**: http://localhost:3000
- **Database**: DuckDB at `./data/finops.duckdb`

## Using the CLI with Podman

### Option 1: Containerized CLI (Recommended)
```bash
# Create podman wrapper script
cat > finops-podman.sh << 'EOF'
#!/bin/bash
podman run --rm -it \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config.toml:/app/config.toml:ro \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN \
  open-finops-cli "$@"
EOF

chmod +x finops-podman.sh

# Use the CLI
./finops-podman.sh aws import-cur
./finops-podman.sh aws list-exports
```

### Option 2: Build and Run Locally
```bash
# Build the CLI container
podman build -t open-finops-cli -f docker/cli/Dockerfile .

# Run commands
podman run --rm -v $(pwd)/data:/app/data open-finops-cli aws import-cur
```

## Production Deployment

### Single VM Setup

1. **Install Podman on your VM**:
```bash
# For Ubuntu/Debian
sudo apt-get update
sudo apt-get install podman podman-compose
```

2. **Clone the repository**:
```bash
git clone https://github.com/JGrubb/open-finops-stack.git
cd open-finops-stack
```

3. **Configure environment**:
```bash
# Copy example config
cp config.toml.example config.toml

# Edit with your AWS credentials and bucket details
nano config.toml
```

4. **Set up systemd services**:
```bash
# Create systemd service for Metabase stack
sudo tee /etc/systemd/system/open-finops.service << EOF
[Unit]
Description=Open FinOps Stack
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/open-finops-stack
ExecStart=/usr/bin/podman-compose up
ExecStop=/usr/bin/podman-compose down
Restart=always
User=finops

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable open-finops
sudo systemctl start open-finops
```

5. **Set up automated imports** (optional):
```bash
# Create cron job for daily imports
crontab -e
# Add: 0 2 * * * cd /opt/open-finops-stack && ./finops-podman.sh aws import-cur
```

## Container Registry Notes

When pulling images, Podman may ask which registry to use. Select:
- `docker.io` for Docker Hub images (metabase/metabase, postgres)
- `quay.io` for Podman-specific images

## Running Metabase Natively (Apple Silicon Workaround)

Due to DuckDB driver compatibility issues with ARM64 containers, you can run Metabase natively on macOS while still using Podman for PostgreSQL:

### 1. Start only PostgreSQL in Podman
```bash
podman-compose up -d postgres
```

### 2. Download and run Metabase natively
```bash
# Download Metabase (one-time)
curl -LO https://downloads.metabase.com/v0.50.26/metabase.jar

# Run Metabase
./scripts/metabase/run-metabase-native.sh
```

### 3. Configure DuckDB in Metabase
- Go to http://localhost:3000
- Complete initial setup
- Add Database → DuckDB
- Database path: `/absolute/path/to/your/data/finops.duckdb`

Note: Use the absolute path to your DuckDB file, not a relative path.

## Troubleshooting

### Podman Machine Issues (macOS)
```bash
# If machine won't start
podman machine stop
podman machine rm
podman machine init --cpus 2 --memory 4096
podman machine start
```

### Permission Issues
```bash
# For volume mounts on Linux
podman unshare chown -R $UID:$GID ./data
```

### Network Issues
```bash
# List networks
podman network ls

# Recreate default network
podman network create podman-compose_default
```

## Differences from Docker

1. **No Docker daemon**: Podman runs containers directly
2. **Rootless by default**: More secure but may need `podman unshare` for some operations
3. **Systemd integration**: Better integration with systemd on Linux
4. **Pod concept**: Podman can group containers into pods (Kubernetes-style)

## Security Best Practices

1. **Run rootless**: Default on most installations
2. **Use secrets**: `podman secret create` for sensitive data
3. **Limit resources**: Use `--memory` and `--cpus` flags
4. **Regular updates**: Keep Podman and images updated

## Next Steps

- Configure Metabase to connect to your DuckDB database
- Set up monitoring with health checks
- Create backup strategies for your data
- Explore Podman's Kubernetes compatibility with `podman generate kube`