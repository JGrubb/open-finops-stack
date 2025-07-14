
# The Open FinOps Stack

## Project Mission

**Kill paid finops visibility tooling as a market segment** by building a complete, open source alternative. This is a FOCUS-first FinOps platform that ingests cloud billing data from AWS, Azure, and GCP, transforms it into standardized formats, and provides visualization through pre-built dashboards.

## Current State: FOUNDATION COMPLETE

This is a complete reboot of the Open FinOps Stack with FOCUS-first architecture. **Foundation phases are complete** with a production-ready AWS CUR pipeline, centralized DuckDB database, comprehensive testing, and multi-export support.

The project is being built in public through a blog series on The FinOperator blog.

## Implementation Status

### Foundation Complete (Phase 1 + 1.5)
- **Core Features**: AWS CUR pipeline (v1/v2), DuckDB database, CLI interface, testing framework
- **Recent Enhancements**: DuckDB direct reading, multi-export support, state tracking, CUR v2 parquet support
- **Status**: Production-ready with real-world validation (1,700+ AWS CUR rows processed)

### CURRENT WORK: Phase 2 - Podman Deployment Infrastructure
- **Issue**: #34
- **Goal**: Container-based deployment using Podman as Docker Desktop alternative
- **Status**: Setting up Podman for local development and testing existing docker-compose.yml
- **Key Tasks**: 
  - Podman setup and docker-compose.yml testing
  - Containerized CLI wrapper implementation
  - One-command deployment without licensing requirements
  - Production deployment documentation

### NEXT UP: Phase 3 - Visualization & Analytics
- **Issue**: #19 (Metabase components)
- **Goal**: Complete Metabase setup with DuckDB integration and pre-built dashboards
- **Dependencies**: Phase 2 completion

### FUTURE WORK: Multi-Cloud & Advanced Features
- **AWS Commitment Pipelines**: Reserved Instance, Savings Plans, Spot Instance analysis (#38, #39, #40)
- **GCP BigQuery Billing**: Full GCP integration with service account auth (#49-#53)
- **Azure Integration**: Multi-cloud transformations (#20)
- **dbt Transformations**: FOCUS compliance and production hardening (#21)
- **Dashboard Templates**: Pre-built FinOps dashboards (#22-#25)

## Architecture Overview

The stack is built on these core technologies:
- **DLT (Data Load Tool)** - Data ingestion with automatic schema evolution (COMPLETE)
- **DuckDB** - Centralized analytical database (`./data/finops.duckdb`) (COMPLETE)
- **Podman** - Container runtime for deployment (Phase 2 focus)
- **Metabase** - Pre-built dashboards and self-service analytics (Phase 3)
- **dbt** - Transforms vendor billing formats to FOCUS specification (Future)

## FOCUS Specification

All data models are designed around FOCUS (FinOps Open Cost and Usage Specification) columns:
- `BillingPeriod` - When the cost was incurred
- `ServiceName` - What service generated the cost  
- `ResourceId` - Specific resource identifier
- `UsageQuantity` - How much was consumed
- `EffectiveCost` - Actual cost after discounts
- `BilledCost` - What appears on your invoice

## Key Directories

```
├── core/                     # Core application code (COMPLETE)
│   ├── cli/main.py          # Command-line interface (COMPLETE)
│   ├── config.py            # Configuration management (COMPLETE)
│   └── backends/            # Database backend abstraction (COMPLETE)
├── vendors/                  # Cloud vendor pipelines (COMPLETE)
│   └── aws/                 # AWS CUR pipeline implementation (COMPLETE)
├── tests/                    # Comprehensive test suites (COMPLETE)
├── docker/                   # Container configurations (IN PROGRESS)
│   └── metabase/            # Custom Metabase with DuckDB (IN PROGRESS)
├── data/                     # Production data directory (COMPLETE)
│   └── finops.duckdb        # Centralized database (COMPLETE)
├── docs/                     # Documentation and blog posts (COMPLETE)
├── config.toml.example       # Configuration template (COMPLETE)
└── finops                    # CLI entry point (COMPLETE)
```

## Development Commands

### Core Pipeline (Use .venv virtualenv and ./finops wrapper)
```bash
# Import AWS CUR data
./finops aws import-cur

# List available manifests  
./finops aws list-manifests

# Run comprehensive test suite
python run_tests.py
```

### Container Deployment (Phase 2 Focus)
```bash
# Current Docker setup (migrating to Podman)
docker-compose up -d

# Future Podman setup
podman-compose up -d

# Access Metabase dashboards
open http://localhost:3000
```

## Data Architecture

**Centralized Database**: All data flows into `./data/finops.duckdb`
- **AWS Billing Tables**: `aws_billing.billing_YYYY_MM` (monthly tables)
- **Schema**: Native cloud formats, ready for FOCUS transformations
- **Multi-Export Support**: Table namespacing for multiple AWS accounts
- **Access**: Both CLI and Metabase connect to the same database

## Configuration

**TOML-based configuration** with environment variable overrides:
```toml
[project]
name = "open-finops-stack"
data_dir = "./data"

[aws]
bucket = "your-cur-bucket"
prefix = "your-prefix"
export_name = "your-export-name"
cur_version = "v1"  # or "v2"

[gcp]
project_id = "your-project-id"
dataset = "your-billing-dataset"  
table = "your-billing-table"
service_account_path = "path/to/service-account.json"
```

**Environment Variables**: `OPEN_FINOPS_AWS_BUCKET`, `AWS_ACCESS_KEY_ID`, etc.

## Current Session Focus

**Phase 2: Podman Deployment Infrastructure (#34)**

Implementing container-based deployment using Podman as an open-source Docker alternative.

**Key Tasks**: 
- Test existing docker-compose.yml with podman-compose
- Adapt finops-docker.sh for Podman
- Create deployment documentation
- Implement containerized CLI wrapper

**Current State**: 
- Foundation complete with multi-export support
- All tests passing with comprehensive coverage
- Ready to implement Podman deployment

**Key Files**: 
- `docker-compose.yml` - Existing stack definition
- `docker/metabase/Dockerfile` - Custom Metabase with DuckDB
- `finops-docker.sh` - Docker wrapper (adapt for Podman)

**Important**: 
- Always use `./finops` wrapper command and `.venv` virtualenv
- Never mention Claude Code in PRs, issues, or commit messages