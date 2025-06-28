# Installation Guide

The Open FinOps Stack uses a modular architecture that allows you to install only the components you need. This guide covers all installation scenarios.

## 🎯 Choose Your Installation Method

### For Most Users: Full Development Setup
- **Who**: Users who want everything working immediately
- **What**: All components (core, AWS, Docker)
- **When**: Development, testing, or full platform usage

### For Advanced Users: Selective Installation  
- **Who**: Users with specific cloud vendors or minimal requirements
- **What**: Only core + specific vendor packages
- **When**: Production deployments with specific needs

### For Developers: Component-by-Component
- **Who**: Contributors, plugin developers, or integrators
- **What**: Individual packages for targeted development
- **When**: Working on specific components or creating plugins

## 🚀 Full Development Setup (Recommended)

This is the easiest way to get started with the complete Open FinOps Stack.

### Prerequisites
- Python 3.8 or higher
- Git
- AWS CLI configured (for AWS functionality)
- Docker (optional, for visualization layer)

### Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/JGrubb/open-finops-stack.git
cd open-finops-stack

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install all components
pip install -e ./core/ ./vendors/aws/ ./docker/

# 4. Verify installation
./finops --help
```

### Expected Output
```
✓ Loaded vendor plugin: aws
usage: finops [-h] [--config CONFIG] {aws} ...

Open FinOps Stack - FOCUS-first FinOps platform

positional arguments:
  {aws}                 Available commands
    aws                 AWS Cost and Usage Report pipelines
```

### Test Your Installation
```bash
# Check AWS commands
./finops aws --help

# Test configuration (optional)
./finops aws list-manifests

# Start visualization (optional)
docker-compose up -d
```

## 📦 Production Installation (Future)

> **Note**: This requires packages to be published to PyPI. Currently in development mode only.

Once published to PyPI, you'll be able to use these installation methods:

### Complete Platform
```bash
# Everything included - works out of the box
pip install open-finops
```

### AWS-Only Installation
```bash
# Core framework + AWS vendor only
pip install open-finops[aws]
```

### Core Framework Only
```bash
# Just the core framework (for developers/integrators)
pip install open-finops[core]
```

### Multiple Vendors
```bash
# Future: Core + multiple vendors
pip install open-finops[aws,azure,gcp]
```

## 🔧 Development Mode (Component-by-Component)

For contributors and plugin developers who want to work on specific components.

### Core Framework Only
```bash
# Install just the core framework
pip install -e ./core/

# Test core functionality
python -c "import core; print('Core installed successfully')"
```

### Add AWS Functionality
```bash
# Core must be installed first
pip install -e ./vendors/aws/

# Test AWS plugin
./finops aws --help
```

### Add Docker Support
```bash
# Core must be installed first  
pip install -e ./docker/

# Verify Docker package
python -c "import docker; print('Docker package installed')"
```

## 🧪 Development Installation for Contributors

If you're contributing to the Open FinOps Stack:

### Setup Development Environment
```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/open-finops-stack.git
cd open-finops-stack

# Create feature branch
git checkout -b feature/your-feature-name

# Install in development mode
pip install -e ./core/ ./vendors/aws/ ./docker/

# Install development dependencies
pip install -r requirements-dev.txt  # If it exists

# Run tests to verify setup
python -m pytest tests/
```

### Testing Your Changes
```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/unit/          # Unit tests only
python -m pytest tests/integration/   # Integration tests only
python -m pytest tests/vendors/aws/   # AWS-specific tests

# Test CLI functionality
./finops aws --help
./finops aws list-manifests
```

## 🔍 Troubleshooting

### Common Issues

#### "finops command not found"
**Problem**: CLI entry point not working
**Solution**: 
```bash
# Check if core package is installed
pip list | grep open-finops-core

# If not installed, install core package
pip install -e ./core/

# Verify entry point
which finops
```

#### "Vendor 'aws' not available"
**Problem**: AWS plugin not installed or not discovered
**Solution**:
```bash
# Check if AWS package is installed
pip list | grep open-finops-aws

# If not installed, install AWS package
pip install -e ./vendors/aws/

# Check for plugin discovery
./finops --help  # Should show "✓ Loaded vendor plugin: aws"
```

#### "ModuleNotFoundError: No module named 'core'"
**Problem**: Import path issues or missing core package
**Solution**:
```bash
# Ensure you're in the right directory
pwd  # Should be in open-finops-stack/

# Reinstall core package
pip install -e ./core/

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

#### Plugin Discovery Issues
**Problem**: Plugins not loading automatically
**Solution**:
The system has fallback discovery for development mode. This warning is normal:
```
/path/to/core/cli/main.py:23: UserWarning: pkg_resources is deprecated...
```

If plugins still don't load:
```bash
# Check entry points registration
pip show open-finops-aws

# Manual verification
python -c "
import pkg_resources
for ep in pkg_resources.iter_entry_points('open_finops.vendors'):
    print(f'Found plugin: {ep.name} -> {ep.module_name}')
"
```

### Virtual Environment Issues

#### "Permission denied" errors
**Solution**: Use virtual environment
```bash
python -m venv venv
source venv/bin/activate
pip install -e ./core/ ./vendors/aws/ ./docker/
```

# Solution**: Use virtual environment
```bash
uv venv
source .venv/bin/activate
pip install -e ./core/ ./vendors/aws/ ./docker/
```

#### Conflicting package versions
**Solution**: Clean virtual environment
```bash
deactivate
rm -rf .venv
uv venv
source .venv/bin/activate
pip install -e ./core/ ./vendors/aws/ ./docker/

## 📋 Installation Verification Checklist

Use this checklist to verify your installation is working correctly:

### Basic Installation
- [ ] `pip list | grep open-finops` shows installed packages
- [ ] `./finops --help` shows help message
- [ ] `./finops --help` shows "✓ Loaded vendor plugin: aws"

### AWS Functionality
- [ ] `./finops aws --help` shows AWS commands
- [ ] `./finops aws list-manifests` runs without errors (may need config)
- [ ] AWS commands appear in main help: `./finops --help`

### Configuration
- [ ] Can create config.toml file
- [ ] `./finops --config config.toml aws --help` works
- [ ] Environment variables recognized (if set)

### Advanced Features
- [ ] `docker-compose up -d` starts Metabase (if Docker installed)
- [ ] Database directory created: `ls data/`
- [ ] Tests pass: `python -m pytest tests/`

## 🆘 Getting Help

If you're still having issues:

### Check Documentation
- [Plugin Development Guide](./PLUGIN_DEVELOPMENT.md)
- [Migration Guide](./MIGRATION.md) (for existing users)
- [Architecture Documentation](./architecture/)

### Report Issues
1. Include your installation method
2. Copy the full error message
3. Include output of:
   ```bash
   pip list | grep open-finops
   ./finops --help
   python --version
   ```

### Community Support
- GitHub Issues: [Report bugs or request features](https://github.com/JGrubb/open-finops-stack/issues)
- Discussions: [Ask questions or share use cases](https://github.com/JGrubb/open-finops-stack/discussions)

---

**Next Steps**: After installation, see the [Configuration Guide](./CONFIGURATION.md) to set up your cloud providers and start importing billing data.