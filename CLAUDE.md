# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Mission

**Kill paid finops visibility tooling as a market segment** by building a complete, open source alternative. This is a FOCUS-first FinOps platform that ingests cloud billing data from AWS, Azure, and GCP, transforms it into standardized formats, and provides visualization through pre-built dashboards.

## Current State

This is a complete reboot of the Open FinOps Stack with FOCUS-first architecture. The project is being built in public through a blog series on The FinOperator blog. Each blog post corresponds to new functionality added to the codebase.

## Architecture Overview

The stack will be built on these core technologies:
- **DLT (Data Load Tool)** - Data ingestion with automatic schema evolution
- **DuckDB** - Local development and data processing (will scale to ClickHouse/etc for production)
- **dbt** - Transforms vendor billing formats to FOCUS specification
- **Metabase** - Pre-built dashboards and self-service analytics
- **Docker** - One-command deployment of the entire stack

## FOCUS Specification

All data models should be designed around FOCUS (FinOps Open Cost and Usage Specification) columns:
- `BillingPeriod` - When the cost was incurred
- `ServiceName` - What service generated the cost
- `ResourceId` - Specific resource identifier
- `UsageQuantity` - How much was consumed
- `EffectiveCost` - Actual cost after discounts
- `BilledCost` - What appears on your invoice

## Development Roadmap

Following the blog series roadmap:
1. Foundation (current) - Project structure and vision
2. Data pipeline architecture and CLI design with DLT
3. AWS billing pipeline implementation
4. Azure billing integration and multi-cloud refactoring
5. dbt transformations - building the FOCUS conversion library
6. Metabase dashboards and visualization layer
7. Docker packaging and deployment automation
8. Production scaling, cost allocation, and advanced analytics

## Directory Structure

```
/
├── src/                      # Core application code
│   ├── pipelines/            # DLT data pipelines
│   ├── cli/                  # Command-line interface
│   └── api/                  # API layer (future)
├── transformations/          # dbt FOCUS conversions
│   ├── aws/                  # AWS CUR → FOCUS
│   ├── azure/                # Azure → FOCUS
│   └── gcp/                  # GCP → FOCUS
├── dashboards/               # Metabase dashboards
├── examples/                 # Sample configurations
├── docs/                     # Documentation and blog posts
└── tests/                    # Test suites
```

## Development Commands

Currently, the only available command is:
```bash
# Start Metabase and Postgres
docker-compose up -d
```

As we build out the codebase, this section will be updated with:
- Python package installation commands
- CLI usage for data ingestion
- Test running commands
- dbt transformation commands

## Important Notes

- The `data/` directory contains preserved data from the previous version and should not be tracked in git
- Blog posts documenting the build process are in `docs/blog-posts/`
- Each major feature addition should correspond to a blog post in the series