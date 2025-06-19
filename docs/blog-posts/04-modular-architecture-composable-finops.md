# Building Composable FinOps: A Modular Architecture for Every Organization

*How we transformed the Open FinOps Stack from a monolithic platform into individual, installable components that organizations can mix and match based on their specific needs.*

## The Problem with One-Size-Fits-All FinOps

When we started building the Open FinOps Stack, we had a vision: replace expensive FinOps vendors with open source infrastructure. But as we talked to more organizations, we realized something important - not everyone needs the same thing.

**The reality of FinOps needs:**
- A startup using only AWS doesn't need Azure billing pipelines
- A data team might only want the raw data pipelines, not the visualization layer
- An organization with existing Grafana dashboards doesn't need another Metabase instance
- A consultancy wants to build custom solutions on top of solid data foundations

Yet most FinOps tools force you to take everything or nothing. You get locked into their entire ecosystem, even if you only need 20% of the functionality.

## Enter Modular Architecture

We decided to break the Open FinOps Stack into composable pieces. Each component serves a specific purpose and can be used independently or combined with others.

### The Core Philosophy

**"Use what you need, when you need it"**

Every organization should be able to:
- Install only the cloud providers they use
- Choose their own visualization tools
- Build custom analytics on top of solid data foundations
- Add new vendors without touching existing infrastructure

## What We Built

### Individual Installable Components

#### `open-finops-core` - The Foundation
```bash
pip install open-finops-core
```

The core framework provides:
- Configuration management across all vendors
- State tracking and incremental loading
- Common utilities and table naming conventions
- CLI framework with plugin discovery

**Who needs this**: Everyone. This is the foundation that other components build on.

#### `open-finops-aws` - AWS Data Pipelines
```bash
pip install open-finops-aws
```

Complete AWS Cost and Usage Report processing:
- Automatic CUR manifest discovery
- Support for both CUR v1 (CSV) and v2 (Parquet) formats
- Incremental loading with deduplication
- Multi-account and multi-export support

**Who needs this**: Any organization using AWS that wants clean, queryable billing data.

#### `open-finops-docker` - Containerized Deployment
```bash
pip install open-finops-docker
```

One-command deployment configurations:
- Pre-configured Metabase with DuckDB integration
- Docker Compose definitions for the full stack
- Container-based CLI for teams without Python expertise

**Who needs this**: Teams that want turnkey deployment without managing Python environments.

### The Meta-Package Experience

For organizations that want everything:
```bash
pip install open-finops          # Gets all components
pip install open-finops[aws]     # Core + AWS only
pip install open-finops[docker]  # Core + deployment tools
```

## Real-World Use Cases

### Case 1: The Data Team
**Situation**: A data engineering team wants AWS billing data in their existing data warehouse.

**Solution**:
```bash
pip install open-finops-aws
finops aws import-cur --export-name production-billing
```

They get:
- Clean, normalized AWS billing data
- Automatic incremental updates
- No need for visualization tools they don't want
- Data flows into their existing analytics pipeline

### Case 2: The Multi-Cloud Startup
**Situation**: A growing company uses AWS and will add GCP soon.

**Solution**:
```bash
pip install open-finops[aws]     # Start with AWS
# Later: pip install open-finops-gcp  (when available)
```

They get:
- Immediate AWS cost visibility
- Ready for GCP expansion without architectural changes
- Consistent data formats across all cloud providers

### Case 3: The Consulting Firm
**Situation**: A consultancy builds custom FinOps solutions for clients.

**Solution**:
```bash
pip install open-finops-core
# Build custom vendor integrations
# Create client-specific analytics
```

They get:
- Solid foundation for custom solutions
- Plugin architecture for client-specific needs
- No vendor lock-in for their own tooling

### Case 4: The Enterprise Migration
**Situation**: Large enterprise wants to migrate from expensive FinOps vendor.

**Solution**:
```bash
pip install open-finops  # Full platform
docker-compose up -d     # Instant deployment
```

They get:
- Drop-in replacement for existing vendor
- Full control over their data and infrastructure
- Immediate cost savings (no percentage-of-spend pricing)

## The Technical Foundation

### Plugin Architecture
Each vendor is a separate Python package that registers itself with the core framework:

```python
# vendors/aws/setup.py
entry_points={
    'open_finops.vendors': [
        'aws = vendors.aws.cli:AWSCommands',
    ]
}
```

The core CLI automatically discovers and loads available vendors:
```
$ finops --help
✓ Loaded vendor plugin: aws

Available commands:
  aws    AWS Cost and Usage Report pipelines
```

### Development Experience
While users get modular installation, developers still work in a monorepo:

```bash
# Contributors work with everything
git clone open-finops-stack
pip install -e ./core/ ./vendors/aws/ ./docker/

# But users install selectively
pip install open-finops-aws
```

This gives us the best of both worlds - easy development and flexible deployment.

## What's Coming Next

### More Vendor Modules
```bash
pip install open-finops-azure    # Coming soon
pip install open-finops-gcp      # Coming soon
```

Each cloud provider will be a separate package with its own release cycle.

### DBT Transformations
```bash
pip install open-finops-dbt-aws     # FOCUS transformations
pip install open-finops-dbt-azure   # Cloud-specific models
```

The same modular approach will apply to data transformations. Organizations can install only the dbt models they need.

### Community Plugins
The plugin architecture enables third-party extensions:
```bash
pip install finops-kubernetes-costs    # Community plugin
pip install finops-snowflake-billing   # Custom integrations
```

## Why This Matters

### For Organizations
- **Lower barriers to entry**: Start small, grow as needed
- **No vendor lock-in**: Use existing tools where they work
- **Cost efficiency**: Pay for infrastructure, not percentages
- **Flexibility**: Build exactly what you need

### For the FinOps Community
- **Faster innovation**: Teams can contribute specific components
- **Better collaboration**: Clear interfaces between components
- **Ecosystem growth**: Third-party plugins and integrations
- **Knowledge sharing**: Reusable patterns across vendors

## Getting Started

### Just Need AWS Data?
```bash
pip install open-finops-aws
finops aws import-cur
```

### Want the Full Platform?
```bash
git clone https://github.com/JGrubb/open-finops-stack.git
cd open-finops-stack
pip install -e ./core/ ./vendors/aws/ ./docker/
docker-compose up -d
```

### Building Something Custom?
Check out our [Plugin Development Guide](../PLUGIN_DEVELOPMENT.md) to create your own vendor integrations.

## The Bigger Picture

This modular architecture represents a fundamental shift in how we think about FinOps tooling. Instead of monolithic platforms that force you into their entire ecosystem, we're building composable infrastructure that adapts to your organization.

**The result**: Every organization can build exactly the FinOps stack they need, using open source components that don't charge percentage-of-spend pricing.

Whether you're a startup needing basic AWS visibility or an enterprise building sophisticated multi-cloud analytics, you can now use exactly the pieces you need from the Open FinOps Stack.

---

*Want to contribute to the modular architecture? Check out our [GitHub repository](https://github.com/JGrubb/open-finops-stack) and see how you can help build the future of FinOps tooling.*

## Technical Details

For those interested in the implementation details:

### Package Structure
```
open-finops-core/        # Foundation framework
├── config.py           # Cross-vendor configuration
├── state.py            # Incremental loading state
├── utils.py            # Common utilities
└── cli/                # Plugin discovery system

open-finops-aws/         # AWS vendor plugin
├── pipeline.py         # CUR data processing
├── manifest.py         # S3 manifest handling
└── cli.py              # AWS-specific commands

open-finops-docker/      # Deployment configurations
├── docker-compose.yml  # Full stack definition
└── metabase/           # Custom Metabase with DuckDB
```

### Plugin Discovery
The core framework uses Python entry points to automatically discover installed vendors:

```python
for entry_point in pkg_resources.iter_entry_points('open_finops.vendors'):
    vendor_class = entry_point.load()
    self.vendors[entry_point.name] = vendor_class
```

This enables seamless integration of new vendors without modifying core code.

### Data Pipeline Integration
All vendors follow the same patterns:
- DLT for data loading with automatic schema evolution
- DuckDB for analytical processing
- Standardized table naming conventions
- Common state management for incremental updates

This ensures consistent behavior across all cloud providers while allowing vendor-specific optimizations.