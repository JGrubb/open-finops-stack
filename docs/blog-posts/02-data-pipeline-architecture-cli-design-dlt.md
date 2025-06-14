# Data Pipeline Architecture and CLI Design with DLT

In the [first post](./01-building-finops-infrastructure-with-focus.md), we established the mission: kill the finops vendor tax by building a complete, open source alternative. Today we're laying the technical foundation with modern data pipeline architecture and a configuration system that scales from development to production.

The question isn't whether you *can* build finops infrastructure yourself—it's whether you can build it *right*. That means choosing patterns and tools that handle the real complexities: multiple data formats, evolving schemas, reliable incremental updates, and deployment flexibility. 

## The Traditional ETL Trap

Most finops implementations start with scripts. A Python script to download AWS billing files. Another to parse them. A third to load them into whatever database seemed reasonable at the time. Six months later, you're debugging CSV parsing edge cases while your schema migration breaks production dashboards.

The problem isn't the scripts—it's that billing data has characteristics that make ETL challenging (in the ways that most real world data makes ETL challenging):

- **Schema evolution**: Cloud vendors add columns monthly
- **Late-arriving data**: Billing files get updated after initial delivery
- **Volume variability**: November costs might be 10x larger than February
- **Multi-format sources**: Even AWS has multiple billing formats (CUR v1, CUR v2, Cost Intelligence Dashboard exports)

Building reliable infrastructure means choosing tools designed for these realities rather than fighting them with custom code.

## Why DLT: Modern Data Pipelines Without the Infrastructure Tax

[DLT (Data Load Tool)](https://dlthub.com/) is a Python library that handles the operational complexity of data pipelines while staying out of your way. Unlike heavyweight orchestration platforms that require dedicated infrastructure teams, DLT focuses on making individual pipelines robust and deployable anywhere.

Here's what DLT handles automatically that we'd otherwise build manually:

- **Schema inference and evolution**: Automatically detects new columns and handles type changes
- **Incremental loading**: Built-in merge/append strategies with state management  
- **Error handling and retries**: Graceful failure recovery without data loss
- **Multi-destination support**: Same pipeline can target DuckDB, PostgreSQL, Snowflake, or BigQuery
- **Data lineage tracking**: Full observability without custom instrumentation

Most importantly, DLT pipelines are just Python functions. No proprietary configuration languages, no vendor lock-in, no separate deployment infrastructure.

## Configuration Architecture: TOML + CLI + Environment Variables

Configuration systems reveal architectural philosophy. Complex YAML files with nested hierarchies suggest infrastructure that's hard to understand and harder to debug. Our approach prioritizes clarity and operational flexibility:

```toml
# config.toml.example
[project]
name = "open-finops-stack"
data_dir = "./data"

[aws]
# Required settings (no defaults)
# bucket = "your-cur-bucket-name"
# prefix = "your-cur-prefix"  
# export_name = "your-cur-export-name"

# Optional settings with defaults
cur_version = "v1"  # Options: "v1" or "v2"
export_format = "csv"  # Options: "csv" or "parquet"

# Date range filters (optional)
# start_date = "2024-01"  # Format: YYYY-MM
# end_date = "2024-12"    # Format: YYYY-MM
```

The configuration system follows a clear precedence hierarchy:
1. **CLI flags** (highest priority) - for one-off runs and CI/CD
2. **Environment variables** - for container deployments and secrets
3. **TOML files** - for persistent configuration
4. **Defaults** (lowest priority) - for sane starting points

This means the same pipeline code works across all deployment patterns:

```bash
# Development with config file
./finops aws import-cur

# CI/CD with environment variables
AWS_BUCKET=ci-bucket ./finops aws import-cur

# Production override with CLI flags
./finops aws import-cur --bucket prod-bucket --start-date 2024-01
```

## CLI Design: Discoverability Over Memorization

Command-line interfaces reveal complexity. Good CLIs make complex operations discoverable rather than requiring memorization of dozens of flags. Our design follows Unix patterns while optimizing for the most common finops workflows:

```bash
# Top-level commands by cloud provider
./finops aws import-cur        # AWS Cost and Usage Reports
./finops azure import-billing  # Azure billing (coming soon)
./finops gcp import-billing    # GCP billing (coming soon)

# Discovery operations
./finops aws list-manifests    # See what data is available
./finops aws list-manifests --start-date 2024-01 --end-date 2024-03

# Pipeline execution with full control
./finops aws import-cur \
  --bucket my-cur-bucket \
  --prefix cur-reports \
  --export-name monthly-cur \
  --start-date 2024-01 \
  --end-date 2024-03 \
  --table-strategy separate
```

The CLI is built with Python's standard library `argparse` rather than external dependencies. This keeps the core lightweight while providing full functionality including help text, subcommands, and argument validation.

## Testing Strategy: Infrastructure for Infrastructure

Building data infrastructure without comprehensive testing is technical debt with interest compounded by production failures. We're taking a different approach: test infrastructure that's as sophisticated as the pipeline infrastructure itself.

Our testing strategy has three layers:

### 1. Sample Data Generation
Rather than depending on external data sources or brittle mocks, we generate realistic test data that matches real-world billing characteristics:

```python
# FOCUS-compliant sample data
records = generate_focus_record(
    billing_period="2024-01",
    service_name="EC2",
    region="us-east-1",
    usage_date=datetime(2024, 1, 15, 14)
)

# AWS CUR format with authentic column structure
aws_records = generate_cur_record(
    billing_period="2024-01", 
    usage_date=datetime(2024, 1, 15, 14)
)
```

### 2. Unit Tests for Components
Every configuration loader, manifest parser, and data transformation gets isolated testing with controlled inputs and predictable outputs.

### 3. Integration Tests with Real File Structures
Integration tests use generated sample data to create complete S3-like directory structures, then run the full pipeline end-to-end. This catches issues that unit tests miss while staying fast enough for development workflows.

The test runner automatically generates fresh sample data for each run, ensuring tests never pass due to stale fixtures:

```bash
# Run all tests with fresh sample data
python run_tests.py

# Run with coverage reporting
python run_tests.py --coverage

# Run with code quality checks
python run_tests.py --quality
```

## Pipeline Architecture: Two Strategies for Data Replacement

Billing data has a unique characteristic: it gets updated. AWS publishes initial Cost and Usage Reports during the month, then updates them with final pricing and discounts after the billing period closes. This means our pipelines need reliable strategies for replacing entire months of data.

DLT supports this with two architectural patterns:

### Strategy 1: Separate Tables (Recommended)
Each billing period gets its own table (`billing_2024_01`, `billing_2024_02`). When new data arrives, we completely replace the table for that month:

```python
@dlt.source(name="aws_cur")
def aws_cur_source(config: AWSConfig):
    for manifest in manifests:
        table_name = f"billing_{manifest.billing_period.replace('-', '_')}"
        yield dlt.resource(
            billing_period_resource(manifest, config, aws_creds),
            name=table_name,
            write_disposition="replace"  # Always replace the entire table
        )
```

### Strategy 2: Single Table with Partition Management
All data goes into one table, but we manually delete old data for each billing period before loading new data:

```python
# Delete existing data for this billing period
with pipeline.sql_client() as client:
    client.execute_sql(f"""
        DELETE FROM aws_billing.billing_data 
        WHERE billing_period = '{manifest.billing_period}'
    """)

# Load new data
load_info = pipeline.run(billing_data_source)
```

The separate tables approach is cleaner because it eliminates partial delete risks and makes historical data management trivial. Need to drop old months? Just drop the table.

## What's Next: AWS Implementation

The foundation is solid: modern pipeline architecture, flexible configuration, comprehensive testing, and reliable data replacement strategies. In the next post, we'll implement the first cloud provider integration with full AWS Cost and Usage Report support.

You'll see how this architecture handles real-world complexity: CUR v1 vs v2 formats, manifest file parsing, incremental data processing, and authentic test data generation. Most importantly, you'll have working code that processes actual AWS billing data from S3 to DuckDB.

The goal remains the same: build multi-cloud, open source infrastructure so robust and accessible that paying vendor premiums becomes indefensible.

---

*This post is part of the Open FinOps Stack blog series. All code is available in the [GitHub repository](https://github.com/your-repo/open-finops-stack) and each post corresponds to working, tested functionality.*