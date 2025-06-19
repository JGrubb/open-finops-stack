# Phase 1: Monorepo Structure

## Goal
Reorganize the current codebase into a modular structure while maintaining all existing functionality. This phase focuses on file organization and import cleanup without changing external interfaces.

## Current Structure Analysis

### What We Have Now
```
src/
├── cli/
│   └── main.py                 # CLI with AWS commands mixed in
├── core/
│   ├── config.py              # Configuration management
│   ├── state.py               # State tracking
│   └── utils.py               # Utilities
├── pipelines/
│   └── aws/
│       ├── pipeline.py        # AWS CUR pipeline
│       └── manifest.py        # AWS manifest handling
```

### Problems to Solve
- AWS code mixed with core framework
- CLI doesn't support plugin discovery
- No clear separation between reusable and AWS-specific code
- Single package structure

## Target Structure

### New Directory Layout
```
core/
├── __init__.py
├── config.py                  # Moved from src/core/config.py
├── state.py                   # Moved from src/core/state.py  
├── utils.py                   # Moved from src/core/utils.py
├── cli/
│   ├── __init__.py
│   ├── main.py                # New: Plugin discovery framework
│   └── base.py                # New: Base command classes
└── setup.py                   # New: Core package definition

vendors/
└── aws/
    ├── __init__.py
    ├── pipeline.py            # Moved from src/pipelines/aws/pipeline.py
    ├── manifest.py            # Moved from src/pipelines/aws/manifest.py
    ├── cli.py                 # Extracted from src/cli/main.py
    └── setup.py               # New: AWS package definition

docker/
├── (existing docker files)
└── setup.py                   # New: Docker package definition

tests/
├── core/                      # Core framework tests
├── vendors/
│   └── aws/                   # AWS-specific tests
└── integration/               # Cross-package tests
```

## Implementation Tasks

### Task 1: Create New Directory Structure
**Time Estimate**: 15 minutes

```bash
# Create new directories
mkdir -p core/cli
mkdir -p vendors/aws
mkdir -p docker
mkdir -p tests/core
mkdir -p tests/vendors/aws
mkdir -p tests/integration
```

### Task 2: Move Core Framework Files
**Time Estimate**: 30 minutes

#### 2.1 Move Core Utilities
```bash
# Move core files
cp src/core/config.py core/config.py
cp src/core/state.py core/state.py  
cp src/core/utils.py core/utils.py

# Create __init__.py files
touch core/__init__.py
touch core/cli/__init__.py
```

#### 2.2 Update Core Imports
Update imports in moved files to reflect new structure:
- `from ...core.config import Config` → `from .config import Config`
- Remove relative imports where possible

### Task 3: Extract and Move AWS Code
**Time Estimate**: 45 minutes

#### 3.1 Move AWS Pipeline Code
```bash
# Move AWS pipeline files
cp src/pipelines/aws/pipeline.py vendors/aws/pipeline.py
cp src/pipelines/aws/manifest.py vendors/aws/manifest.py

# Create __init__.py
touch vendors/aws/__init__.py
```

#### 3.2 Extract AWS CLI Commands
Create `vendors/aws/cli.py` by extracting AWS commands from `src/cli/main.py`:

```python
# vendors/aws/cli.py
"""AWS CLI commands for Open FinOps Stack."""

import argparse
from pathlib import Path

from ...core.config import Config
from .pipeline import run_aws_pipeline
from .manifest import ManifestLocator


class AWSCommands:
    """AWS vendor commands."""
    
    def add_subparser(self, subparsers):
        """Add AWS subcommands to the CLI."""
        aws_parser = subparsers.add_parser('aws', help='AWS Cost and Usage Report pipelines')
        aws_subparsers = aws_parser.add_subparsers(dest='aws_command', help='AWS commands')
        
        # Add import-cur command
        self._add_import_cur_command(aws_subparsers)
        # Add other AWS commands...
    
    def _add_import_cur_command(self, subparsers):
        """Add the import-cur command."""
        # Move existing import-cur logic here
        pass
```

#### 3.3 Update AWS Imports
Update imports in AWS files:
- `from ...core.config import AWSConfig` → `from ...core.config import AWSConfig`
- `from ...core.state import LoadStateTracker` → `from ...core.state import LoadStateTracker`

### Task 4: Create New Core CLI Framework
**Time Estimate**: 45 minutes

#### 4.1 Create Base CLI Framework
```python
# core/cli/base.py
"""Base classes for CLI commands."""

from abc import ABC, abstractmethod


class VendorCommands(ABC):
    """Base class for vendor command implementations."""
    
    @abstractmethod
    def add_subparser(self, subparsers):
        """Add vendor subcommands to the CLI parser."""
        pass


class BaseCommand(ABC):
    """Base class for individual commands."""
    
    @abstractmethod
    def run(self, args):
        """Execute the command."""
        pass
```

#### 4.2 Create Plugin Discovery System
```python
# core/cli/main.py
"""Main CLI entry point with plugin discovery."""

import argparse
import sys
from typing import Dict, Type

from .base import VendorCommands


class FinOpsCLI:
    """Main CLI with plugin discovery."""
    
    def __init__(self):
        self.vendors: Dict[str, Type[VendorCommands]] = {}
        self._discover_vendors()
    
    def _discover_vendors(self):
        """Discover available vendor plugins."""
        # For Phase 1, manually register AWS
        # Phase 2 will add automatic discovery
        try:
            from ...vendors.aws.cli import AWSCommands
            self.vendors['aws'] = AWSCommands
        except ImportError:
            pass  # AWS not installed
    
    def run(self):
        """Run the CLI."""
        parser = self._create_parser()
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            sys.exit(0)
        
        # Execute vendor command
        vendor = self.vendors.get(args.command)
        if vendor:
            vendor_instance = vendor()
            vendor_instance.execute(args)
        else:
            print(f"Vendor '{args.command}' not available")
            sys.exit(1)
    
    def _create_parser(self):
        """Create the main argument parser."""
        parser = argparse.ArgumentParser(
            description='Open FinOps Stack - FOCUS-first FinOps platform'
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Let each vendor add its subcommands
        for name, vendor_class in self.vendors.items():
            vendor_instance = vendor_class()
            vendor_instance.add_subparser(subparsers)
        
        return parser


def main():
    """CLI entry point."""
    cli = FinOpsCLI()
    cli.run()
```

### Task 5: Move and Update Tests
**Time Estimate**: 30 minutes

#### 5.1 Organize Test Files
```bash
# Move core tests
cp tests/unit/test_config.py tests/core/
cp tests/unit/test_utils.py tests/core/

# Move AWS tests  
cp tests/unit/test_aws_*.py tests/vendors/aws/
cp tests/integration/test_aws_*.py tests/vendors/aws/

# Keep integration tests that span multiple vendors
cp tests/integration/test_end_to_end.py tests/integration/
```

#### 5.2 Update Test Imports
Update import statements in test files to match new structure.

### Task 6: Update Main Entry Point
**Time Estimate**: 15 minutes

Update the main `finops` script to use the new CLI:
```python
#!/usr/bin/env python3
"""Open FinOps Stack CLI entry point."""

from core.cli.main import main

if __name__ == '__main__':
    main()
```

## Verification Checklist

### Functionality Tests
- [ ] `./finops aws import-cur` works exactly as before
- [ ] `./finops aws list-manifests` works
- [ ] All existing CLI commands function normally
- [ ] Configuration loading works
- [ ] State tracking works
- [ ] Database operations work

### Code Quality Tests  
- [ ] All imports resolve correctly
- [ ] No circular import dependencies
- [ ] Python can import all modules without errors
- [ ] All tests pass (run `python -m pytest`)

### Structure Validation
- [ ] Core framework has no AWS-specific imports
- [ ] AWS vendor code only imports from core (never reverse)
- [ ] Each package directory has proper `__init__.py` files
- [ ] File organization matches target structure

## Common Issues and Solutions

### Import Errors
**Problem**: `ModuleNotFoundError` or `ImportError`
**Solution**: Check relative vs absolute imports, ensure `__init__.py` files exist

### Circular Dependencies  
**Problem**: Core imports vendor code or vendor imports between vendors
**Solution**: Vendors should only import from core, never from each other

### Test Failures
**Problem**: Tests can't find modules or data files
**Solution**: Update test imports and paths to match new structure

## Success Criteria

- [ ] All existing functionality works without changes to user interface
- [ ] Core framework is cleanly separated from AWS code
- [ ] New directory structure is implemented
- [ ] All tests pass
- [ ] Code is ready for Phase 2 (multi-package setup)

## Next Steps

After Phase 1 completion:
1. Review the new structure with stakeholders
2. Ensure all verification criteria are met
3. Proceed to [Phase 2: Multi-Package Setup](./phase-2-multi-package-setup.md)

---

**Estimated Time**: 2-3 hours  
**Dependencies**: None  
**Deliverable**: Restructured codebase with modular architecture