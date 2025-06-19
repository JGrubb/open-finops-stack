# PyPI Publishing Guide

This guide covers how to publish the Open FinOps Stack packages to PyPI, enabling users to install via `pip install open-finops[aws]`.

## 📋 Prerequisites

### Required Tools
```bash
# Install publishing tools
pip install build twine

# Verify tools
python -m build --help
twine --help
```

### PyPI Account Setup
1. Create account at [pypi.org](https://pypi.org)
2. Enable 2FA (required for new projects)
3. Create API token for publishing
4. Configure `~/.pypirc`:

```ini
[distutils]
index-servers = pypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-your-api-token-here
```

### Package Name Verification
Ensure these names are available on PyPI:
- `open-finops-core`
- `open-finops-aws` 
- `open-finops-docker`
- `open-finops` (meta-package)

## 🎯 Publishing Strategy

### Package Dependencies
The packages must be published in dependency order:

```
1. open-finops-core     (no open-finops dependencies)
2. open-finops-aws      (depends on open-finops-core)
3. open-finops-docker   (depends on open-finops-core)
4. open-finops          (depends on all above)
```

### Version Management
- **Synchronized versioning**: All packages use same version (e.g., 0.3.0)
- **Semantic versioning**: MAJOR.MINOR.PATCH format
- **Update all packages**: Even if only one package changes

## 🚀 Publishing Workflow

### Step 1: Pre-Publishing Checklist

#### Version Verification
```bash
# Check all setup.py files have same version
grep -r "version=" core/setup.py vendors/aws/setup.py docker/setup.py setup.py

# Check __init__.py files have same version  
grep -r "__version__" core/__init__.py vendors/aws/__init__.py docker/__init__.py
```

#### Quality Checks
```bash
# Run all tests
python -m pytest tests/

# Verify installations work
pip install -e ./core/ ./vendors/aws/ ./docker/
./finops --help

# Check for common issues
python -m flake8 core/ vendors/ docker/  # If you use flake8
```

#### Documentation Updates
- [ ] README.md reflects current version
- [ ] CHANGELOG.md updated with new features
- [ ] Installation instructions verified
- [ ] Plugin development guide current

### Step 2: Build Packages

#### Core Package
```bash
cd core/
python -m build
ls dist/  # Should show .tar.gz and .whl files
cd ..
```

#### AWS Package  
```bash
cd vendors/aws/
python -m build
ls dist/
cd ../..
```

#### Docker Package
```bash
cd docker/
python -m build  
ls dist/
cd ..
```

#### Meta-Package
```bash
# Main directory
python -m build
ls dist/
```

### Step 3: Test Uploads (Recommended)

Use TestPyPI before production:

```bash
# Upload to TestPyPI first
twine upload --repository testpypi core/dist/*
twine upload --repository testpypi vendors/aws/dist/*
twine upload --repository testpypi docker/dist/*
twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ open-finops-core
pip install --index-url https://test.pypi.org/simple/ open-finops[aws]
```

### Step 4: Production Publishing

#### Publish in Dependency Order
```bash
# 1. Core package (no dependencies)
twine upload core/dist/*

# 2. Vendor packages (depend on core)
twine upload vendors/aws/dist/*
twine upload docker/dist/*

# 3. Meta-package (depends on all)
twine upload dist/*
```

#### Verify Published Packages
```bash
# Check packages are available
pip search open-finops-core
pip search open-finops-aws
pip search open-finops

# Test installation
pip install open-finops[aws]
finops --help
```

## 🔄 Release Automation

### GitHub Actions Workflow
Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install build twine
    
    - name: Build packages
      run: |
        python -m build core/
        python -m build vendors/aws/
        python -m build docker/
        python -m build .
    
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: |
        twine upload core/dist/*
        twine upload vendors/aws/dist/*
        twine upload docker/dist/*
        twine upload dist/*
```

### Manual Release Process
```bash
# 1. Update version in all setup.py files
# 2. Update version in all __init__.py files  
# 3. Update CHANGELOG.md
# 4. Commit changes
git add .
git commit -m "Bump version to 0.3.1"

# 5. Create git tag
git tag v0.3.1
git push origin v0.3.1

# 6. Create GitHub release (triggers automation)
# OR manually publish using steps above
```

## 🛠 Troubleshooting

### Common Publishing Issues

#### "Package already exists"
**Problem**: Version already published to PyPI
**Solution**:
```bash
# Increment version in all setup.py files
# Rebuild and republish
```

#### "Invalid credentials"
**Problem**: PyPI authentication failing
**Solution**:
```bash
# Verify ~/.pypirc configuration
# Regenerate API token if needed
# Test with TestPyPI first
```

#### "Missing dependencies"
**Problem**: Core package not available when publishing vendors
**Solution**:
```bash
# Ensure core package published first
# Wait for PyPI propagation (can take few minutes)
# Verify dependency versions match
```

#### "Build failures"
**Problem**: Package building fails
**Solution**:
```bash
# Check setup.py for syntax errors
# Verify all required files included
# Test build locally first

python -m build --verbose core/
```

### Package Validation

#### Before Publishing
```bash
# Check package metadata
python setup.py check --metadata --strict

# Verify contents
tar -tzf dist/open-finops-core-0.3.0.tar.gz

# Test installation locally
pip install dist/open-finops-core-0.3.0.tar.gz
```

#### After Publishing
```bash
# Verify package available
pip index versions open-finops-core

# Test clean installation
pip install --upgrade open-finops[aws]
finops aws --help
```

## 📊 Version Management Strategy

### Semantic Versioning
- **MAJOR** (1.0.0): Breaking changes to CLI or API
- **MINOR** (0.X.0): New features, new vendor support
- **PATCH** (0.3.X): Bug fixes, documentation updates

### Release Cadence
- **Major releases**: Quarterly or as needed for breaking changes
- **Minor releases**: Monthly for new features
- **Patch releases**: As needed for critical fixes

### Version Synchronization
All packages should maintain synchronized versions:
```bash
# Update all versions simultaneously
./scripts/bump-version.sh 0.3.1  # If you create this script

# Or manually update:
# - core/setup.py
# - vendors/aws/setup.py  
# - docker/setup.py
# - setup.py
# - core/__init__.py
# - vendors/aws/__init__.py
# - docker/__init__.py
```

## 📈 Post-Publishing Tasks

### Documentation Updates
- [ ] Update README.md installation instructions
- [ ] Verify pip install examples work
- [ ] Update documentation links to reference published packages
- [ ] Update INSTALLATION.md with PyPI instructions

### Community Communication
- [ ] Announce release in GitHub discussions
- [ ] Update project status in README
- [ ] Share on relevant social media/forums
- [ ] Update any external documentation

### Monitoring
- [ ] Monitor PyPI download statistics
- [ ] Watch for user issues or feedback
- [ ] Monitor dependency security alerts
- [ ] Track usage patterns for future planning

## 🔒 Security Considerations

### API Token Management
- Use scoped tokens (project-specific)
- Store tokens securely in CI/CD secrets
- Rotate tokens regularly
- Never commit tokens to version control

### Package Security
- Enable 2FA on PyPI account
- Use verified email for package ownership
- Monitor for typosquatting attempts
- Include security contact in package metadata

### Dependency Security
- Regularly update dependencies
- Monitor security advisories
- Use `pip-audit` or similar tools
- Pin dependencies to known-good versions

## 🆘 Rollback Procedures

### If Bad Release is Published
PyPI doesn't allow deleting releases, but you can:

1. **Publish fixed version immediately**:
   ```bash
   # Increment patch version
   # Fix the issue
   # Publish new version
   ```

2. **Yank problematic version**:
   ```bash
   # On PyPI web interface, mark version as "yanked"
   # This prevents new installations but allows existing ones
   ```

3. **Communicate clearly**:
   - Update README with known issues
   - Post in GitHub issues
   - Update documentation

### Emergency Contacts
- Maintain list of PyPI project maintainers
- Ensure multiple people can publish if needed
- Document emergency procedures

---

**Next Steps**: After first PyPI publication, users will be able to use `pip install open-finops[aws]` and the full modular installation experience will be available.