# Plugin Development Guide

This guide shows how to create new vendor plugins for the Open FinOps Stack. The modular architecture makes it easy to add support for new cloud providers, billing formats, or specialized data sources.

## 🎯 Plugin Architecture Overview

### Core Concepts
- **Plugins are packages**: Each vendor is a separate Python package
- **Entry point registration**: Plugins register themselves via setuptools entry points
- **Base class inheritance**: All plugins inherit from `VendorCommands`
- **Automatic discovery**: The CLI automatically finds and loads installed plugins

### Plugin Lifecycle
1. **Discovery**: CLI scans for entry points in `open_finops.vendors`
2. **Loading**: Plugin class is imported and instantiated
3. **Registration**: Plugin commands are added to CLI parser
4. **Execution**: User runs commands, plugin handles the request

## 🚀 Quick Start: Creating a GCP Plugin

Let's create a Google Cloud Platform plugin as an example.

### Step 1: Create Package Structure
```bash
mkdir -p vendors/gcp
cd vendors/gcp

# Create package files
touch __init__.py
touch setup.py
touch cli.py
touch pipeline.py
```

### Step 2: Define Package Metadata
Create `vendors/gcp/__init__.py`:
```python
"""Open FinOps Stack GCP Vendor Package.

This package provides Google Cloud Platform billing integration:
- Cloud Billing API data ingestion
- GCP-specific billing data transformations
- BigQuery export processing
"""

__version__ = "0.3.0"
__description__ = "GCP vendor plugin for Open FinOps Stack"
```

### Step 3: Create Setup Configuration
Create `vendors/gcp/setup.py`:
```python
"""Setup configuration for the GCP vendor package."""

from setuptools import setup, find_packages

setup(
    name="open-finops-gcp",
    version="0.3.0",
    description="GCP vendor plugin for Open FinOps Stack",
    packages=find_packages(),
    install_requires=[
        "open-finops-core>=0.3.0",
        "google-cloud-billing>=1.0.0",
        "google-cloud-bigquery>=3.0.0",
    ],
    entry_points={
        'open_finops.vendors': [
            'gcp = vendors.gcp.cli:GCPCommands',
        ]
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
)
```

### Step 4: Implement CLI Commands
Create `vendors/gcp/cli.py`:
```python
"""GCP CLI commands."""

import argparse
from core.cli.base import VendorCommands
from core.config import Config
from .pipeline import GCPPipeline


class GCPCommands(VendorCommands):
    """GCP vendor commands."""
    
    def add_subparser(self, subparsers):
        """Add GCP subcommands to the CLI."""
        parser = subparsers.add_parser(
            'gcp', 
            help='Google Cloud Platform billing pipelines'
        )
        
        gcp_subparsers = parser.add_subparsers(dest='gcp_command', help='GCP commands')
        
        # Import billing data command
        import_parser = gcp_subparsers.add_parser(
            'import-billing',
            help='Import GCP billing data from BigQuery'
        )
        import_parser.add_argument(
            '--project-id',
            required=True,
            help='GCP project ID containing billing export'
        )
        import_parser.add_argument(
            '--dataset-id', 
            required=True,
            help='BigQuery dataset containing billing data'
        )
        import_parser.add_argument(
            '--table-id',
            required=True, 
            help='BigQuery table with billing data'
        )
        
        # List projects command
        list_parser = gcp_subparsers.add_parser(
            'list-projects',
            help='List available GCP projects'
        )
    
    def execute(self, args):
        """Execute GCP commands."""
        if not hasattr(args, 'gcp_command') or not args.gcp_command:
            print("No GCP command specified. Use 'finops gcp --help' for options.")
            return
            
        config = Config.load()
        
        if args.gcp_command == 'import-billing':
            self._import_billing(args, config)
        elif args.gcp_command == 'list-projects':
            self._list_projects(args, config)
        else:
            print(f"Unknown GCP command: {args.gcp_command}")
    
    def _import_billing(self, args, config):
        """Import GCP billing data."""
        pipeline = GCPPipeline(config)
        
        print(f"Importing billing data from GCP project: {args.project_id}")
        print(f"Dataset: {args.dataset_id}, Table: {args.table_id}")
        
        # Run the import pipeline
        pipeline.import_billing_data(
            project_id=args.project_id,
            dataset_id=args.dataset_id,
            table_id=args.table_id
        )
        
        print("✅ GCP billing data import completed")
    
    def _list_projects(self, args, config):
        """List available GCP projects."""
        pipeline = GCPPipeline(config)
        projects = pipeline.list_projects()
        
        print("Available GCP projects:")
        for project in projects:
            print(f"  - {project['project_id']}: {project['name']}")
```

### Step 5: Implement Data Pipeline
Create `vendors/gcp/pipeline.py`:
```python
"""GCP billing data pipeline."""

import dlt
from typing import List, Dict, Any
from google.cloud import billing, bigquery
from core.state import StateManager
from core.utils import create_table_name


class GCPPipeline:
    """GCP billing data pipeline."""
    
    def __init__(self, config):
        self.config = config
        self.state_manager = StateManager(config)
        self.bq_client = bigquery.Client()
        self.billing_client = billing.CloudBillingClient()
    
    def import_billing_data(self, project_id: str, dataset_id: str, table_id: str):
        """Import billing data from BigQuery export."""
        
        # Create DLT pipeline
        pipeline = dlt.pipeline(
            pipeline_name="gcp_billing",
            destination="duckdb",
            dataset_name="gcp_billing"
        )
        
        # Extract data from BigQuery
        billing_data = self._extract_bigquery_data(project_id, dataset_id, table_id)
        
        # Transform data to standardized format
        transformed_data = self._transform_billing_data(billing_data)
        
        # Load data
        load_info = pipeline.run(
            transformed_data,
            table_name=create_table_name("gcp", "billing", project_id)
        )
        
        # Update state
        self.state_manager.update_load_state(
            vendor="gcp",
            export_name=f"{project_id}_{dataset_id}_{table_id}",
            load_info=load_info
        )
        
        return load_info
    
    def _extract_bigquery_data(self, project_id: str, dataset_id: str, table_id: str):
        """Extract billing data from BigQuery."""
        query = f"""
        SELECT 
            billing_account_id,
            service.description as service_name,
            sku.description as sku_description,
            project.id as project_id,
            usage_start_time,
            usage_end_time,
            cost,
            currency,
            usage.amount as usage_amount,
            usage.unit as usage_unit
        FROM `{project_id}.{dataset_id}.{table_id}`
        WHERE usage_start_time >= CURRENT_DATE() - 30
        ORDER BY usage_start_time DESC
        """
        
        query_job = self.bq_client.query(query)
        results = query_job.result()
        
        return [dict(row) for row in results]
    
    def _transform_billing_data(self, raw_data: List[Dict[str, Any]]):
        """Transform GCP billing data to standard format."""
        for record in raw_data:
            # Standardize field names
            record['vendor'] = 'gcp'
            record['billing_period'] = record['usage_start_time'].date()
            record['resource_id'] = record.get('project_id', 'unknown')
            record['effective_cost'] = record.get('cost', 0)
            record['billed_cost'] = record.get('cost', 0)
            
            # Convert timestamps to strings for DLT
            if 'usage_start_time' in record:
                record['usage_start_time'] = record['usage_start_time'].isoformat()
            if 'usage_end_time' in record:
                record['usage_end_time'] = record['usage_end_time'].isoformat()
        
        return raw_data
    
    def list_projects(self) -> List[Dict[str, str]]:
        """List available GCP projects."""
        # This is a simplified example
        # In practice, you'd use the Resource Manager API
        return [
            {"project_id": "example-project-1", "name": "Example Project 1"},
            {"project_id": "example-project-2", "name": "Example Project 2"},
        ]
```

### Step 6: Install and Test
```bash
# Install the new plugin
pip install -e ./vendors/gcp/

# Test plugin discovery
./finops --help
# Should show: ✓ Loaded vendor plugin: gcp

# Test GCP commands  
./finops gcp --help
./finops gcp list-projects
```

## 📋 Plugin Development Checklist

### Required Components
- [ ] `__init__.py` with version and description metadata
- [ ] `setup.py` with proper entry point registration
- [ ] `cli.py` inheriting from `VendorCommands`
- [ ] `pipeline.py` with data extraction/transformation logic
- [ ] Entry point in `open_finops.vendors` group

### CLI Integration
- [ ] Commands added via `add_subparser()` method
- [ ] Arguments and help text defined
- [ ] Command execution handled in `execute()` method
- [ ] Error handling and user feedback

### Data Pipeline Integration
- [ ] Uses DLT for data loading
- [ ] Integrates with core state management
- [ ] Follows table naming conventions
- [ ] Handles data transformation appropriately

### Testing
- [ ] Unit tests for CLI commands
- [ ] Integration tests for data pipeline
- [ ] Mock external APIs for testing
- [ ] Plugin discovery tests

## 🔧 Core Interfaces Reference

### VendorCommands Base Class
```python
from core.cli.base import VendorCommands

class YourVendorCommands(VendorCommands):
    def add_subparser(self, subparsers):
        """Add vendor commands to CLI parser."""
        pass
    
    def execute(self, args):
        """Execute vendor commands."""
        pass
```

### Configuration Integration
```python
from core.config import Config

# Load configuration
config = Config.load()

# Access vendor-specific config
vendor_config = config.get_vendor_config('your_vendor')

# Environment variable pattern: OPEN_FINOPS_YOUR_VENDOR_SETTING
```

### State Management
```python
from core.state import StateManager

state_manager = StateManager(config)

# Update load state after successful import
state_manager.update_load_state(
    vendor="your_vendor",
    export_name="your_export",
    load_info=load_info
)

# Check if data already loaded
if state_manager.is_already_loaded(vendor, export_name, date):
    print("Data already loaded, skipping...")
```

### Table Naming
```python
from core.utils import create_table_name

# Creates properly formatted table name
table_name = create_table_name("vendor", "type", "identifier")
# Example: "aws_billing_export_2024_03"
```

## 🧪 Testing Your Plugin

### Unit Testing
```python
# tests/vendors/your_vendor/test_cli.py
import pytest
from vendors.your_vendor.cli import YourVendorCommands

def test_add_subparser():
    """Test that subparser is added correctly."""
    # Test implementation
    pass

def test_command_execution():
    """Test command execution with mock args."""
    # Test implementation  
    pass
```

### Integration Testing
```python
# tests/integration/test_your_vendor_pipeline.py
import pytest
from vendors.your_vendor.pipeline import YourVendorPipeline

def test_data_import_end_to_end():
    """Test complete data import process."""
    # Test implementation with mocked APIs
    pass
```

### Manual Testing
```bash
# Test plugin discovery
./finops --help | grep your_vendor

# Test command structure
./finops your_vendor --help

# Test actual functionality (with real credentials)
./finops your_vendor import-data --help
```

## 📚 Best Practices

### Code Organization
- Keep CLI logic separate from data pipeline logic
- Use dependency injection for testability
- Follow existing code style and patterns
- Add comprehensive docstrings

### Error Handling
- Provide helpful error messages for users
- Handle API rate limits and retries gracefully
- Validate configuration before starting long operations
- Log errors for debugging

### Performance
- Use generators for large datasets
- Implement incremental loading where possible
- Cache API responses when appropriate
- Monitor memory usage for large imports

### Documentation
- Document all CLI commands and arguments
- Provide examples in docstrings
- Update this guide with new patterns
- Include configuration examples

## 🔄 Publishing Your Plugin

Once your plugin is ready, you can publish it to PyPI:

### Prepare for Publishing
```bash
# Update version in setup.py and __init__.py
# Ensure all dependencies are correctly specified
# Add comprehensive README.md
# Include LICENSE file
```

### Publish to PyPI
```bash
# Build distribution
python setup.py sdist bdist_wheel

# Upload to PyPI
twine upload dist/*
```

### Integration with Main Package
After publishing, add your plugin to the main `setup.py` extras:
```python
extras_require={
    'your_vendor': ['open-finops-core>=0.3.0', 'open-finops-your-vendor>=0.3.0'],
    'all': [
        'open-finops-core>=0.3.0',
        'open-finops-aws>=0.3.0', 
        'open-finops-your-vendor>=0.3.0',  # Add your plugin
        'open-finops-docker>=0.3.0',
    ],
}
```

## 🆘 Getting Help

### Development Questions
- Check existing vendor implementations for patterns
- Review core interfaces in `core/cli/base.py`
- Look at AWS plugin as reference implementation

### Technical Issues
- Use GitHub Issues for bug reports
- Include minimal reproduction steps
- Share relevant error messages and logs

### Community
- GitHub Discussions for design questions
- Consider proposing major changes as RFCs
- Follow existing code review practices

---

**Next Steps**: After creating your plugin, consider contributing it back to the main repository or publishing it as a separate package for the community to use.