# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Mission

**Kill paid finops visibility tooling as a market segment** by building a complete, open source alternative. This is a FOCUS-first FinOps platform that ingests cloud billing data from AWS, Azure, and GCP, transforms it into standardized formats, and provides visualization through pre-built dashboards.

## Current State: PHASE 1 COMPLETE! 🎉

This is a complete reboot of the Open FinOps Stack with FOCUS-first architecture. **Phase 1 (Foundation) is fully implemented** with a working AWS CUR pipeline, centralized database architecture, comprehensive testing, and development documentation.

The project is being built in public through a blog series on The FinOperator blog. Each blog post corresponds to new functionality added to the codebase.

## Implementation Status

### ✅ Phase 1: Foundation (COMPLETED)
- **Issue**: #18 
- **Status**: All core infrastructure implemented and tested
- **PRs**: #12, #13, #14, #15 (all merged)
- **Capabilities**: 
  - Complete AWS CUR pipeline with v1/v2 support
  - Centralized DuckDB database (`./data/finops.duckdb`)
  - CLI interface with `aws import-cur` and `aws list-manifests`
  - Comprehensive testing framework (25 unit + 13 integration tests)
  - Real-world validation with actual AWS billing data

### ✅ Phase 1.5: Core Infrastructure Enhancements (COMPLETED)  
- **Issues**: #27, #28, #29, #30, #32
- **Status**: Major pipeline improvements implemented
- **PRs**: #27 (DuckDB direct reading), #28 (DLT fixes), #29 (column naming), #30 (state tracking), #33 (multi-export)
- **Capabilities**: 
  - **DuckDB Direct Reading**: Replaced Pandas/PyArrow with native DuckDB for better performance
  - **Enhanced CUR v2 Support**: Full parquet file support with S3 URI parsing
  - **Improved Column Naming**: Preserves AWS CUR category prefixes (lineItem_*, reservation_*, etc.)
  - **DLT Stability**: Fixed nested table deletion conflicts while preserving multi-database support
  - **Multi-Export Support**: Import multiple AWS accounts/exports simultaneously with table namespacing
  - **State Tracking**: Intelligent deduplication and incremental imports
  - **Comprehensive Testing**: Added CUR v2 specific tests, now 25 unit + 13 integration tests

### 🔄 Phase 2: Container Runtime & Deployment Infrastructure (IN PROGRESS)
- **Issue**: #34
- **Status**: Setting up Podman-based deployment
- **Focus**: 
  - Podman as Docker Desktop alternative
  - Container-based deployment for local and production
  - One-command setup without licensing requirements
  - Simple single VM production hosting

### ⏳ Phase 3: Visualization & Analytics (PLANNED)
- **Issue**: #19 (Metabase components)
- **Status**: Infrastructure ready, awaiting Phase 2 completion
- **Components**: 
  - Complete Metabase setup with DuckDB integration
  - Pre-built FinOps dashboard templates
  - Custom dashboard creation guides
  - Advanced analytics features

### ⏳ Phase 3 Extensions: Dashboard Templates (PLANNED)
- **Issues**: #22, #23, #24, #25 (split from #19)
- **Status**: Ready for implementation after core visualization
- **Focus**: 
  - Pre-built FinOps dashboard templates (#22)
  - Advanced analytics features (#23) 
  - Custom dashboard creation guides (#24)
  - Multi-cloud dashboard templates (#25)

### ⏳ Phase 4: Multi-Cloud Support (PLANNED)
- **Issue**: #20 
- **Focus**: Azure and GCP integration

### ⏳ Phase 5: Production Features & Transformations (PLANNED)
- **Issue**: #21
- **Focus**: dbt transformations, FOCUS compliance, production hardening

## Architecture Overview

The stack is built on these core technologies:
- **DLT (Data Load Tool)** - Data ingestion with automatic schema evolution ✅
- **DuckDB** - Centralized analytical database (`./data/finops.duckdb`) ✅
- **dbt** - Transforms vendor billing formats to FOCUS specification ⏳
- **Metabase** - Pre-built dashboards and self-service analytics ✅
- **Docker** - One-command deployment of the entire stack ✅

## FOCUS Specification

All data models are designed around FOCUS (FinOps Open Cost and Usage Specification) columns:
- `BillingPeriod` - When the cost was incurred
- `ServiceName` - What service generated the cost  
- `ResourceId` - Specific resource identifier
- `UsageQuantity` - How much was consumed
- `EffectiveCost` - Actual cost after discounts
- `BilledCost` - What appears on your invoice

## Directory Structure

```
/
├── src/                      # Core application code ✅
│   ├── pipelines/aws/        # AWS CUR pipeline implementation ✅
│   ├── cli/main.py          # Command-line interface ✅
│   └── core/config.py       # Configuration management ✅
├── transformations/          # dbt FOCUS conversions ⏳
│   ├── aws/                  # AWS CUR → FOCUS ⏳
│   ├── azure/                # Azure → FOCUS ⏳
│   └── gcp/                  # GCP → FOCUS ⏳
├── tests/                    # Comprehensive test suites ✅
│   ├── unit/                 # Unit tests (23 tests) ✅
│   ├── integration/          # Integration tests (13 tests) ✅
│   ├── data/                 # Test data generators ✅
│   └── compare_data.py       # Real vs test data analysis ✅
├── docs/                     # Documentation and blog posts ✅
│   ├── blog-posts/           # Published blog series ✅
│   ├── VISUALIZATION.md      # Metabase setup guide 🔄
│   └── DOCKER.md            # Docker deployment guide 🔄
├── docker/                   # Docker configurations 🔄
│   └── metabase/            # Custom Metabase with DuckDB 🔄
├── data/                     # Production data directory ✅
│   └── finops.duckdb        # Centralized database ✅
├── tmp/                      # Temporary test data ✅
├── examples/                 # Sample configurations ✅
├── dashboards/               # Metabase dashboards ⏳
├── config.toml.example       # Configuration template ✅
└── finops                    # CLI entry point ✅
```

## Development Commands

### Core Pipeline Commands ✅
```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Import AWS CUR data
python -m src.cli.main aws import-cur

# List available manifests  
python -m src.cli.main aws list-manifests

# Run comprehensive test suite
python run_tests.py
```

### Docker Commands ✅ (Ready)
```bash
# Build and run pipeline (no Python setup needed)
./finops-docker.sh aws import-cur

# Start complete stack (pipeline + Metabase)
docker-compose up -d

# Access Metabase dashboards
open http://localhost:3000
```

### Testing & Development ✅
```bash
# Run all tests
python -m pytest

# Run specific test types
python -m pytest tests/unit/          # Unit tests
python -m pytest tests/integration/   # Integration tests

# Compare real vs test data
cd tests && python compare_data.py
```

## Data Architecture ✅

**Centralized Database**: All data flows into a single `./data/finops.duckdb` database
- **AWS Billing Tables**: `aws_billing.billing_YYYY_MM` (separate tables per month)
- **Schema**: Native AWS CUR format, ready for FOCUS transformations
- **Access**: Both CLI and Metabase connect to the same database
- **Performance**: Optimized for analytical queries with DuckDB

## Configuration ✅

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
```

**Environment Variables**:
- `OPEN_FINOPS_AWS_BUCKET`, `OPEN_FINOPS_AWS_PREFIX`, etc.
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

## Testing Framework ✅

**Comprehensive test coverage** with realistic sample data:
- **Unit Tests**: Configuration, manifest processing, core functionality
- **Integration Tests**: AWS CUR format validation, pipeline end-to-end
- **Data Generators**: Create realistic AWS CUR data for testing
- **Comparison Tools**: Validate test data against real AWS billing data

## Important Notes

- **Phase 1 Complete**: Core AWS pipeline is production-ready
- **Real Data Tested**: Successfully processed 1,700+ AWS CUR rows
- **Issue Tracking**: Main progress tracked in issue #11 with sub-issues #18-21
- **Blog Series**: Each phase documented in `docs/blog-posts/`
- **Git Structure**: Clean feature branch workflow with PRs for each phase
- **Data Directory**: `./data/` contains production database, `./tmp/` for test artifacts

## 🎯 Next Session Work Plan

**Current Focus: Podman Deployment Infrastructure (Phase 2)**

With the core pipeline infrastructure complete and enhanced, we're now implementing container-based deployment using Podman as an open-source Docker alternative.

**Active Work**: 
- 🔄 Setting up Podman for local development
- 🔄 Testing existing docker-compose.yml with podman-compose
- 🔄 Creating deployment documentation
- 🔄 Implementing containerized CLI wrapper

**Current State**: 
- ✅ Pipeline fully functional with multi-export support
- ✅ Both CUR v1 (CSV) and v2 (parquet) formats supported  
- ✅ All tests passing with comprehensive coverage
- ✅ Five major PRs merged: #27, #28, #29, #30, #33
- 🔄 Issue #34 created for Phase 2 Podman work

**Key Files for Phase 2**:
- `docker-compose.yml` - Existing stack definition
- `docker/metabase/Dockerfile` - Custom Metabase with DuckDB
- `finops-docker.sh` - Existing Docker wrapper (adapt for Podman)
- `docs/PODMAN.md` - Deployment guide (to be created)

PS - never add anything about Claude Code to any PRs, issues, or commit messages.
There is a wrapper command at ./finops and a virtualenv at .venv that you should always use.