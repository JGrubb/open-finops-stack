---
layout: page
title: CLI Commands
permalink: /reference/cli/
parent: Reference
---

# CLI Commands

The Open FinOps Stack provides a command-line interface for importing and managing cloud billing data.

## Installation

### Standard Installation

```bash
# Clone the repository
git clone https://github.com/openfinops/open-finops-stack.git
cd open-finops-stack

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Make the CLI executable
chmod +x finops
```

### Docker Installation

No Python setup required - use the provided Docker wrapper:

```bash
chmod +x finops-docker.sh
./finops-docker.sh --help
```

## Command Structure

```
./finops [global-options] <provider> <command> [options]
```

## Global Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--config` | `-c` | Path to configuration file | `./config.toml` |

## AWS Commands

### aws import-cur

Import AWS Cost and Usage Reports from S3 into the local DuckDB database.

```bash
./finops aws import-cur [options]
```

#### Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--bucket` | `-b` | S3 bucket containing CUR files | - |
| `--prefix` | `-p` | S3 prefix/path to CUR files | - |
| `--export-name` | `-e` | Name of the CUR export | - |
| `--cur-version` | `-v` | CUR version (`v1` or `v2`) | `v1` |
| `--export-format` | - | Export format (`csv` or `parquet`) | `csv |
| `--start-date` | - | Start date (YYYY-MM) | - |
| `--end-date` | - | End date (YYYY-MM) | - |
| `--reset` | - | Drop existing tables before import | `False` |
| `--table-strategy` | - | Table organization (`separate` or `single`) | `separate` |

#### Examples

```bash
# Import using config file
./finops aws import-cur

# Import specific date range
./finops aws import-cur --start-date 2024-01 --end-date 2024-03

# Import CUR v2 with reset
./finops aws import-cur --cur-version v2 --reset

# Docker usage
./finops-docker.sh aws import-cur --start-date 2024-01
```

### aws list-manifests

List available billing periods in the configured S3 bucket.

```bash
./finops aws list-manifests [options]
```

#### Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--bucket` | `-b` | S3 bucket containing CUR files | - |
| `--prefix` | `-p` | S3 prefix/path to CUR files | - |
| `--export-name` | `-e` | Name of the CUR export | - |
| `--cur-version` | `-v` | CUR version (`v1` or `v2`) | `v1` |
| `--start-date` | - | Start date (YYYY-MM) | - |
| `--end-date` | - | End date (YYYY-MM) | - |

#### Examples

```bash
# List all available manifests
./finops aws list-manifests

# List manifests for specific period
./finops aws list-manifests --start-date 2024-01 --end-date 2024-06

# Docker usage
./finops-docker.sh aws list-manifests
```

## Configuration

Configuration can be provided through multiple sources (in priority order):

1. **Command-line arguments** (highest priority)
2. **Environment variables**
3. **Configuration file** (config.toml)
4. **Default values** (lowest priority)

### Configuration File

Create a `config.toml` file:

```toml
[project]
name = "open-finops-stack"
data_dir = "./data"

[aws]
bucket = "your-cur-bucket"
prefix = "cur-reports/hourly"
export_name = "my-cur-export"
cur_version = "v2"
export_format = "parquet"
region = "us-east-1"

[dlt]
destination = "duckdb"
dataset_name = "aws_billing"
```

### Environment Variables

Configuration via environment variables:

```bash
# AWS configuration
export OPEN_FINOPS_AWS_BUCKET=my-cur-bucket
export OPEN_FINOPS_AWS_PREFIX=reports/cur
export OPEN_FINOPS_AWS_EXPORT_NAME=monthly
export OPEN_FINOPS_AWS_CUR_VERSION=v2

# AWS credentials
export AWS_ACCESS_KEY_ID=your-key-id
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=us-east-1
```

## Output

The CLI provides detailed output including:

- Configuration being used
- Progress indicators
- Success/failure status
- Table creation details
- Row counts for imported data

Example output:

```
Running AWS CUR import pipeline...
Configuration:
  Source: s3://my-bucket/reports/cur/monthly-export
  Version: v2
  Period: 2024-01 to 2024-03
  
✅ Import completed successfully
Tables created:
  - aws_billing.billing_2024_01 (5,234 rows)
  - aws_billing.billing_2024_02 (4,891 rows)
  - aws_billing.billing_2024_03 (5,102 rows)
```

## Troubleshooting

### Missing Configuration

If required configuration is missing:

1. Check your `config.toml` file exists
2. Verify environment variables are set
3. Ensure AWS credentials are available

### Authentication Errors

For AWS authentication issues:

1. Verify AWS credentials are set correctly
2. Check IAM permissions include:
   - `s3:GetObject`
   - `s3:ListBucket`
3. Ensure bucket and prefix are correct

### Import Failures

If imports fail:

1. Use `list-manifests` to verify data exists
2. Check CUR version matches your export
3. Verify date formats (YYYY-MM)
4. Check available disk space