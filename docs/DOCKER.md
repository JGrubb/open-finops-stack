# Docker Deployment Guide

This guide covers deploying the Open FinOps Stack using Docker, eliminating the need for Python virtual environment setup.

## Quick Start

### Option 1: Docker Wrapper Script (Recommended)

```bash
# Make the wrapper executable
chmod +x finops-docker.sh

# Import AWS CUR data
./finops-docker.sh aws import-cur

# List available manifests  
./finops-docker.sh aws list-manifests

# Run tests
./finops-docker.sh --help
```

### Option 2: Direct Docker Commands

```bash
# Build the pipeline image
docker build -t finops-pipeline .

# Import AWS CUR data
docker run --rm \
  -v $(pwd)/data:/data \
  -v $(pwd)/config.toml:/app/config.toml:ro \
  finops-pipeline aws import-cur

# List available manifests
docker run --rm \
  -v $(pwd)/config.toml:/app/config.toml:ro \
  finops-pipeline aws list-manifests
```

### Option 3: Docker Compose (Full Stack)

```bash
# Start Metabase only
docker-compose up -d

# Include pipeline service
docker-compose -f docker-compose.yml -f docker-compose.pipeline.yml up -d

# Run one-off import job
docker-compose -f docker-compose.yml -f docker-compose.pipeline.yml run aws-import

# Run manifest listing
docker-compose -f docker-compose.yml -f docker-compose.pipeline.yml run aws-list
```

## Prerequisites

1. **Docker**: Install Docker Desktop from [docker.com](https://docker.com)
2. **Configuration**: Create `config.toml` with your AWS settings (see [SETUP.md](../SETUP.md))

## Directory Structure

The Docker deployment expects this directory structure:

```
/
├── config.toml              # Your configuration (required)
├── data/                    # Database and output files (auto-created)
├── tmp/                     # Temporary test data (auto-created) 
├── finops-docker.sh         # Docker wrapper script
├── docker-compose.yml       # Metabase service
├── docker-compose.pipeline.yml  # Pipeline service extension
└── Dockerfile               # Pipeline image definition
```

## Volume Mounts

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./data/` | `/data` | DuckDB database and output files |
| `./config.toml` | `/app/config.toml` | Configuration (read-only) |
| `./tmp/` | `/tmp` | Temporary test data |

## Environment Variables

The Docker container supports these environment variables:

- `OPEN_FINOPS_DATA_DIR`: Data directory path (default: `/data`)
- `OPEN_FINOPS_AWS_*`: AWS configuration overrides
- `AWS_ACCESS_KEY_ID`: AWS credentials
- `AWS_SECRET_ACCESS_KEY`: AWS credentials
- `AWS_DEFAULT_REGION`: AWS region

## Usage Examples

### AWS CUR Import

```bash
# Using wrapper script
./finops-docker.sh aws import-cur --start-date 2024-01 --end-date 2024-03

# Using docker directly
docker run --rm \
  -v $(pwd)/data:/data \
  -v $(pwd)/config.toml:/app/config.toml:ro \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  finops-pipeline aws import-cur --start-date 2024-01
```

### Development and Testing

```bash
# Run tests in container
docker run --rm \
  -v $(pwd):/app \
  -w /app \
  finops-pipeline python -m pytest tests/

# Interactive shell for debugging
docker run --rm -it \
  -v $(pwd)/data:/data \
  -v $(pwd)/config.toml:/app/config.toml:ro \
  finops-pipeline bash
```

### Complete Stack Deployment

```bash
# Start everything
docker-compose -f docker-compose.yml -f docker-compose.pipeline.yml up -d

# Check logs
docker-compose logs finops-pipeline
docker-compose logs metabase

# Import data
docker-compose run aws-import

# Access Metabase
open http://localhost:3000
```

## Troubleshooting

### Common Issues

**"config.toml not found"**
- Create `config.toml` in the current directory
- See [SETUP.md](../SETUP.md) for configuration examples

**"Permission denied"**
- Make sure Docker has access to the current directory
- On Linux, you may need to adjust file permissions: `chmod 755 ./data`

**"AWS credentials not found"**
- Set AWS environment variables or configure AWS CLI
- Mount your AWS credentials: `-v ~/.aws:/root/.aws:ro`

**"Database locked"**
- Stop any running Metabase containers: `docker-compose down`
- The DuckDB file can only be accessed by one process at a time

### Build Issues

**"Image not found"**
```bash
# Rebuild the image
docker build -t finops-pipeline . --no-cache
```

**"Dependencies failed to install"**
```bash
# Check requirements.txt exists and is valid
cat requirements.txt

# Build with verbose output
docker build -t finops-pipeline . --progress=plain
```

## Performance Considerations

- **Database Location**: The `/data` volume should be on fast storage (SSD)
- **Memory**: DuckDB operations can be memory-intensive for large datasets
- **Networking**: AWS S3 access speed affects import performance

## Security Notes

- Configuration file contains sensitive AWS credentials
- Use environment variables or AWS IAM roles in production
- The container runs as root by default - consider using USER directive for production

## Customization

### Custom Base Image

To use a different Python version or add system packages:

```dockerfile
FROM python:3.12-slim  # Different Python version

# Add custom system packages
RUN apt-get update && apt-get install -y \
    your-package-here \
    && rm -rf /var/lib/apt/lists/*
```

### Development Mode

For development with code changes:

```bash
# Mount source code for live editing
docker run --rm -it \
  -v $(pwd):/app \
  -w /app \
  finops-pipeline bash
```

## Integration with CI/CD

Example GitHub Actions workflow:

```yaml
name: Test Docker Build
on: [push, pull_request]

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: docker build -t finops-pipeline .
      - name: Test CLI
        run: docker run --rm finops-pipeline --help
```

## Next Steps

1. **Import your data**: Configure AWS credentials and run import
2. **Explore with Metabase**: Connect to your DuckDB database  
3. **Build dashboards**: Create custom visualizations
4. **Scale up**: Consider production deployment options

For more information, see:
- [SETUP.md](../SETUP.md) - Initial configuration
- [VISUALIZATION.md](VISUALIZATION.md) - Metabase setup
- [README.md](../README.md) - Project overview