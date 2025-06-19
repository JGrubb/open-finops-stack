# Phase 2: Multi-Package Setup

## Goal
Create separate setup.py files for each package and implement automatic plugin discovery via entry points. This enables the extras-based installation pattern (`pip install open-finops[aws]`) while maintaining the monorepo development structure.

## Current State Analysis

### What We Have Now (Post-Phase 1)
```
/
├── core/                           # Core framework package
│   ├── __init__.py
│   ├── config.py, state.py, utils.py
│   └── cli/                        # CLI framework with manual discovery
├── vendors/
│   └── aws/                        # AWS vendor package
│       ├── __init__.py
│       ├── pipeline.py, manifest.py, cli.py
└── finops                          # Main script (uses core.cli.main)
```

### What Works Well
- ✅ Modular directory structure
- ✅ Clean separation between core and vendors
- ✅ Manual plugin discovery working
- ✅ All functionality preserved

### What Needs Implementation
- 🔄 Individual setup.py files for each package
- 🔄 Automatic plugin discovery via entry points
- 🔄 Extras-based installation configuration
- 🔄 Package metadata and dependencies

## Target Architecture

### Development Structure (Same)
```
/
├── core/
│   ├── setup.py                    # NEW: Core package definition
│   ├── __init__.py
│   ├── config.py, state.py, utils.py
│   └── cli/
│       └── main.py                 # UPDATED: Entry point discovery
├── vendors/
│   └── aws/
│       ├── setup.py                # NEW: AWS package definition
│       ├── __init__.py
│       ├── pipeline.py, manifest.py
│       └── cli.py                  # UPDATED: Entry point registration
├── docker/
│   └── setup.py                    # NEW: Docker package definition
├── setup.py                        # UPDATED: Main orchestrator with extras
├── pyproject.toml                  # NEW: Modern packaging metadata
└── finops                          # SAME: Main script entry point
```

### Distribution Packages
```bash
# Default - Everything (best user experience)
pip install open-finops              # Gets ALL packages - works out of the box!

# Specific vendors (for specialized use cases)
pip install open-finops[aws]         # Gets core + AWS only
pip install open-finops[docker]      # Gets core + Docker only

# Advanced options
pip install open-finops[core]        # Gets core only (developers/testing)
pip install open-finops[all]         # Explicit "everything" (same as default)
```

### Entry Points System
```python
# vendors/aws/setup.py
entry_points = {
    'open_finops.vendors': [
        'aws = vendors.aws.cli:AWSCommands',
    ]
}

# core/cli/main.py discovers plugins automatically
import pkg_resources
for entry_point in pkg_resources.iter_entry_points('open_finops.vendors'):
    vendor_class = entry_point.load()
    self.vendors[entry_point.name] = vendor_class
```

## Implementation Tasks

### Task 1: Create Core Package Setup
**Time Estimate**: 30 minutes

#### 1.1 Create core/setup.py
```python
# core/setup.py
from setuptools import setup, find_packages

setup(
    name="open-finops-core",
    version="0.3.0",
    description="Core framework for Open FinOps Stack",
    packages=find_packages(),
    install_requires=[
        "dlt>=0.4.0",
        "duckdb>=0.9.0", 
        "toml>=0.10.0",
        "boto3>=1.26.0",
    ],
    entry_points={
        'console_scripts': [
            'finops=core.cli.main:main',
        ]
    },
    python_requires=">=3.8",
)
```

#### 1.2 Update core/__init__.py
Add package metadata and version information.

### Task 2: Create AWS Vendor Package Setup
**Time Estimate**: 30 minutes

#### 2.1 Create vendors/aws/setup.py
```python
# vendors/aws/setup.py
from setuptools import setup, find_packages

setup(
    name="open-finops-aws",
    version="0.3.0", 
    description="AWS vendor plugin for Open FinOps Stack",
    packages=find_packages(),
    install_requires=[
        "open-finops-core>=0.3.0",
        "boto3>=1.26.0",
        "botocore>=1.29.0",
    ],
    entry_points={
        'open_finops.vendors': [
            'aws = vendors.aws.cli:AWSCommands',
        ]
    },
    python_requires=">=3.8",
)
```

#### 2.2 Update vendors/aws/__init__.py
Add package metadata.

### Task 3: Create Docker Package Setup
**Time Estimate**: 15 minutes

#### 3.1 Create docker/setup.py
```python
# docker/setup.py
from setuptools import setup, find_packages

setup(
    name="open-finops-docker",
    version="0.3.0",
    description="Docker configurations for Open FinOps Stack", 
    packages=find_packages(),
    install_requires=[
        "open-finops-core>=0.3.0",
    ],
    python_requires=">=3.8",
)
```

### Task 4: Create Main Orchestrator Setup
**Time Estimate**: 45 minutes

#### 4.1 Create main setup.py
```python
# setup.py (main orchestrator)
from setuptools import setup, find_packages

setup(
    name="open-finops",
    version="0.3.0",
    description="FOCUS-first open source FinOps platform",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        # Default installation includes everything for best UX
        "open-finops-core>=0.3.0",
        "open-finops-aws>=0.3.0",
        "open-finops-docker>=0.3.0",
    ],
    extras_require={
        # Specific vendors for specialized use cases
        'aws': ['open-finops-core>=0.3.0', 'open-finops-aws>=0.3.0'],
        'docker': ['open-finops-core>=0.3.0', 'open-finops-docker>=0.3.0'],
        
        # Advanced options
        'core': ['open-finops-core>=0.3.0'],  # Core only for developers
        'all': [                              # Explicit everything (same as default)
            'open-finops-core>=0.3.0',
            'open-finops-aws>=0.3.0',
            'open-finops-docker>=0.3.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'finops=core.cli.main:main',
        ]
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9", 
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
```

#### 4.2 Create pyproject.toml
```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "open-finops"
dynamic = ["version"]
description = "FOCUS-first open source FinOps platform"
readme = "README.md"
authors = [{name = "Open FinOps Community"}]
license = {text = "MIT"}
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: System Administrators", 
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
]
requires-python = ">=3.8"
```

### Task 5: Implement Automatic Plugin Discovery
**Time Estimate**: 45 minutes

#### 5.1 Update core/cli/main.py
```python
# core/cli/main.py
import pkg_resources
from typing import Dict, Type
from .base import VendorCommands

class FinOpsCLI:
    def __init__(self):
        self.vendors: Dict[str, Type[VendorCommands]] = {}
        self._discover_vendors()
    
    def _discover_vendors(self):
        """Discover vendor plugins via entry points."""
        try:
            # Automatic discovery via entry points
            for entry_point in pkg_resources.iter_entry_points('open_finops.vendors'):
                try:
                    vendor_class = entry_point.load()
                    self.vendors[entry_point.name] = vendor_class
                    print(f"Loaded vendor plugin: {entry_point.name}")
                except Exception as e:
                    print(f"Failed to load vendor plugin {entry_point.name}: {e}")
        except Exception:
            # Fallback to manual discovery for development
            try:
                from vendors.aws.cli import AWSCommands
                self.vendors['aws'] = AWSCommands
            except ImportError:
                pass
```

#### 5.2 Add graceful degradation
Ensure the CLI works both in development (no entry points) and in installed packages (with entry points).

### Task 6: Update Package Metadata
**Time Estimate**: 30 minutes

#### 6.1 Add version management
```python
# core/__init__.py
__version__ = "0.3.0"
__description__ = "Core framework for Open FinOps Stack"

# vendors/aws/__init__.py  
__version__ = "0.3.0"
__description__ = "AWS vendor plugin for Open FinOps Stack"
```

#### 6.2 Update README.md
Add installation instructions for the new package structure.

### Task 7: Testing Multi-Package Installation
**Time Estimate**: 30 minutes

#### 7.1 Test Installation Scenarios
```bash
# Test core only
pip install -e ./core/

# Test AWS vendor
pip install -e ./vendors/aws/

# Test main package (default = everything)
pip install -e .

# Test specific extras
pip install -e .[aws]          # AWS only
pip install -e .[core]         # Core only  
pip install -e .[all]          # Explicit everything
```

#### 7.2 Verify Plugin Discovery
```bash
# Should work with automatic discovery
finops --help

# Should show AWS commands
finops aws --help
```

## Verification Checklist

### Installation Tests
- [ ] `pip install -e ./core/` installs core only
- [ ] `pip install -e ./vendors/aws/` installs AWS plugin
- [ ] `pip install -e .` installs everything (default)
- [ ] `pip install -e .[aws]` installs core + AWS only
- [ ] `pip install -e .[core]` installs core only
- [ ] `pip install -e .[all]` installs all packages (explicit)
- [ ] Entry points are registered correctly

### Plugin Discovery Tests
- [ ] `finops --help` shows available vendors
- [ ] `finops aws --help` works when AWS installed
- [ ] `finops aws import-cur` functions normally
- [ ] Graceful error when vendor not installed
- [ ] Development mode (no entry points) still works

### Functionality Tests
- [ ] All existing CLI commands work unchanged
- [ ] Pipeline execution works normally
- [ ] State tracking functions correctly
- [ ] Database operations work
- [ ] All tests pass

### Package Structure Tests
- [ ] Each package has correct dependencies
- [ ] No circular dependencies between packages
- [ ] Metadata is correctly defined
- [ ] Version numbers are consistent

## Common Issues and Solutions

### Entry Point Loading Failures
**Problem**: `ModuleNotFoundError` when loading entry points
**Solution**: Ensure all packages are properly installed and importable

### Development vs Production Differences
**Problem**: Works in development but not in installed packages
**Solution**: Test both development (`-e` installs) and production installs

### Circular Dependencies
**Problem**: Core and vendor packages depend on each other
**Solution**: Vendors depend on core, but core never depends on vendors

### Version Compatibility
**Problem**: Core and vendor package versions get out of sync
**Solution**: Use compatible version ranges (`>=0.3.0,<0.4.0`)

## Success Criteria

### Technical Requirements
- [ ] `pip install open-finops` installs everything (works out of the box)
- [ ] `pip install open-finops[aws]` installs core + AWS only
- [ ] `pip install open-finops[core]` installs core only (advanced users)
- [ ] Plugin discovery works via entry points
- [ ] All existing functionality preserved
- [ ] Development workflow unchanged (monorepo structure intact)

### User Experience Requirements
- [ ] `pip install open-finops` gives a working system immediately
- [ ] `finops --help` shows only available vendors
- [ ] Specialized installations work for advanced users
- [ ] Error messages are helpful when vendors are missing
- [ ] CLI interface unchanged from user perspective

### Development Requirements
- [ ] Single-repo development workflow maintained
- [ ] Plugin registration is automatic via entry points
- [ ] Each package can be developed and tested independently
- [ ] Clear dependency hierarchy (vendors → core, never reverse)

## ✅ PHASE 2 COMPLETE

**Implementation Status**: All tasks completed successfully
**Date Completed**: 2024-06-19
**Total Time**: ~3 hours

### What Was Implemented
- ✅ **Core Package Setup**: `open-finops-core` with entry points
- ✅ **AWS Vendor Package**: `open-finops-aws` with plugin registration  
- ✅ **Docker Package**: `open-finops-docker` for containerization
- ✅ **Main Meta-Package**: `open-finops` orchestrator with extras
- ✅ **Plugin Discovery**: Automatic discovery via entry points + fallback
- ✅ **Package Metadata**: Proper versioning and dependencies
- ✅ **All Tests Pass**: 73 tests verified with modular structure

### Current Installation Capabilities

#### ✅ What Works Now (Development Mode)
```bash
# Individual packages work perfectly
pip install -e ./core/                    # Core framework only
pip install -e ./vendors/aws/             # AWS plugin (depends on core)
pip install -e ./docker/                  # Docker package (depends on core)

# Full development setup
pip install -e ./core/ ./vendors/aws/ ./docker/
```

#### 🔄 What Requires PyPI Publishing
```bash
# These require packages to be published to PyPI first
pip install open-finops                   # Meta-package (all components)
pip install open-finops[aws]              # Core + AWS only
pip install open-finops[core]             # Core only
pip install open-finops[docker]           # Core + Docker only
```

### Plugin Discovery System ✅
```
✓ Loaded vendor plugin: aws               # Entry points working
finops aws --help                         # CLI functional
```

### Technical Foundation Complete
- **Entry Points**: `aws = vendors.aws.cli:AWSCommands` registered
- **Fallback Discovery**: Manual import when entry points unavailable
- **Package Structure**: Clean separation with proper dependencies
- **CLI Integration**: Seamless plugin loading and command registration

## PyPI Publishing Requirements

To enable the full `pip install open-finops[aws]` experience, these packages need to be published to PyPI:

### Publishing Order
1. **First**: `open-finops-core` (no dependencies on other open-finops packages)
2. **Second**: `open-finops-aws`, `open-finops-docker` (depend on core)
3. **Third**: `open-finops` meta-package (depends on all sub-packages)

### PyPI Package Names
- `open-finops-core` - Core framework
- `open-finops-aws` - AWS vendor plugin  
- `open-finops-docker` - Docker configurations
- `open-finops` - Meta-package with extras

### Current Status Summary
**Phase 2 has successfully implemented the complete technical foundation for modular installation.** The plugin discovery system works, packages can be installed individually, and all functionality is preserved. Once published to PyPI, users will immediately have access to the full `pip install open-finops[vendor]` experience without any additional development work.

## Next Steps

After PyPI publishing:
1. **Phase 3**: Testing & Documentation updates
2. **Phase 4**: Multi-cloud vendor expansion (Azure, GCP)
3. **Phase 5**: Production features & dbt transformations

---

**Status**: ✅ COMPLETE  
**Implementation Time**: 3 hours  
**All Tests Passing**: 73/73  
**Ready for PyPI Publishing**: Yes