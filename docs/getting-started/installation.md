---
layout: page
title: Installation
parent: Getting Started
---

# Installation Guide

## Docker Installation (Recommended)

The easiest way to get started is with Docker. This method requires no Python setup and works consistently across all platforms.

### Prerequisites
- Docker Desktop or Docker Engine
- Docker Compose
- 4GB+ RAM available for containers

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/JGrubb/open-finops-stack.git
   cd open-finops-stack
   ```

2. **Configure your AWS credentials**
   ```bash
   # Copy example configuration
   cp config.toml.example config.toml
   
   # Edit with your AWS details
   vim config.toml
   ```

3. **Start the stack**
   ```bash
   # Import your first data
   ./finops-docker.sh aws import-cur
   
   # Start Metabase dashboards
   docker-compose up -d
   ```

4. **Access dashboards**
   - Open http://localhost:3000
   - Login with default credentials (admin/admin)
   - Start exploring your cost data!

## Python Development Installation

For development work or if you prefer Python environments:

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)

### Installation Steps

1. **Clone and setup environment**
   ```bash
   git clone https://github.com/JGrubb/open-finops-stack.git
   cd open-finops-stack
   
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   uv pip sync requirements.txt requirements-dev.txt
   ```

3. **Configure and test**
   ```bash
   cp config.toml.example config.toml
   # Edit config.toml with your settings
   
   # Test installation
   python -m core.cli.main aws list-manifests
   ```

## Verification

### Test Docker Installation
```bash
# Check containers are running
docker-compose ps

# Test CLI access
./finops-docker.sh aws list-manifests

# Check Metabase
curl http://localhost:3000/api/health
```

### Test Python Installation
```bash
# Run test suite
python run_tests.py

# Test CLI
python -m core.cli.main aws list-manifests

# Check database
ls -la data/finops.duckdb
```

## Troubleshooting

### Common Docker Issues

**Container fails to start**
- Check Docker has enough memory (4GB+ recommended)
- Verify ports 3000 and 5432 are not in use
- Check Docker logs: `docker-compose logs`

**Permission denied on finops-docker.sh**
```bash
chmod +x finops-docker.sh
```

### Common Python Issues

**Import errors**
- Ensure virtual environment is activated
- Reinstall requirements: `pip install -r requirements.txt`

**AWS credential issues**
- Verify AWS CLI is configured: `aws sts get-caller-identity`
- Check config.toml has correct bucket/prefix settings

## Next Steps

- [Configure AWS integration](configuration.md)
- [Run your first import](quick-start.md)
- [Set up production deployment](../deployment/production.md)