"""AWS CUR data pipeline using DLT."""

import csv
import gzip
import io
import tempfile
import os
from datetime import datetime
from typing import Iterator, Dict, Any, Optional
import boto3
import dlt
from dlt.sources import DltResource
import duckdb

from .manifest import ManifestLocator, ManifestFile
from ...core.config import AWSConfig


@dlt.source(name="aws_cur")
def aws_cur_source(config: AWSConfig):
    """DLT source for AWS Cost and Usage Reports.
    
    This source creates separate tables for each billing period,
    completely replacing the data each time it runs.
    """
    
    # Get AWS credentials
    aws_creds = {
        'access_key_id': config.access_key_id,
        'secret_access_key': config.secret_access_key,
        'region': config.region
    }
    
    # Initialize manifest locator
    locator = ManifestLocator(
        bucket=config.bucket,
        prefix=config.prefix,
        export_name=config.export_name,
        cur_version=config.cur_version
    )
    
    # List all manifests within date range
    manifests = locator.list_manifests(
        start_date=config.start_date,
        end_date=config.end_date,
        **aws_creds
    )
    
    if not manifests:
        raise ValueError(f"No manifests found in {config.bucket}/{config.prefix}")
    
    print(f"Found {len(manifests)} billing periods to process")
    
    # Strategy 1: Separate tables per billing period (recommended)
    # Each month gets its own table that's completely replaced
    for manifest in manifests:
        table_name = f"billing_{manifest.billing_period.replace('-', '_')}"
        yield dlt.resource(
            billing_period_resource(manifest, config, aws_creds),
            name=table_name,
            write_disposition="replace"  # Always replace the entire table
        )


@dlt.source(name="aws_cur_single_table")
def aws_cur_single_table_source(config: AWSConfig):
    """Alternative source that uses a single table with partitioning.
    
    This approach uses a single table but processes each month separately,
    deleting the old data for that month before inserting new data.
    """
    
    # Get AWS credentials
    aws_creds = {
        'access_key_id': config.access_key_id,
        'secret_access_key': config.secret_access_key,
        'region': config.region
    }
    
    # Initialize manifest locator
    locator = ManifestLocator(
        bucket=config.bucket,
        prefix=config.prefix,
        export_name=config.export_name,
        cur_version=config.cur_version
    )
    
    # List all manifests within date range
    manifests = locator.list_manifests(
        start_date=config.start_date,
        end_date=config.end_date,
        **aws_creds
    )
    
    if not manifests:
        raise ValueError(f"No manifests found in {config.bucket}/{config.prefix}")
    
    print(f"Found {len(manifests)} billing periods to process")
    
    # Strategy 2: Single table with custom partition handling
    # We'll add a billing_period column and handle deletion manually
    for manifest in manifests:
        # Create a resource with the billing period embedded
        yield dlt.resource(
            billing_period_with_partition(manifest, config, aws_creds),
            name="billing_data",
            write_disposition="append",  # We'll handle deletion manually
            columns={
                "billing_period": {"data_type": "text", "nullable": False},
                "usage_start_date": {"data_type": "timestamp", "nullable": False}
            }
        )


def billing_period_resource(
    manifest: ManifestFile,
    config: AWSConfig,
    aws_creds: Dict[str, Any]
) -> Iterator[Dict[str, Any]]:
    """DLT resource for a single billing period."""
    
    # Fetch manifest data
    locator = ManifestLocator(
        bucket=config.bucket,
        prefix=config.prefix,
        export_name=config.export_name,
        cur_version=config.cur_version
    )
    
    manifest = locator.fetch_manifest(manifest, **aws_creds)
    
    print(f"Processing billing period: {manifest.billing_period}")
    print(f"  Assembly ID: {manifest.assembly_id}")
    print(f"  Report files: {len(manifest.report_keys)}")
    
    # Process each report file
    for report_key in manifest.report_keys:
        print(f"  Processing: {report_key}")
        
        # Extract key from S3 URI if needed (CUR v2 uses full S3 URIs)
        if report_key.startswith('s3://'):
            # Parse s3://bucket/key format to extract just the key
            parts = report_key.replace('s3://', '').split('/', 1)
            if len(parts) == 2:
                s3_bucket, s3_key = parts
            else:
                raise ValueError(f"Invalid S3 URI format: {report_key}")
        else:
            # CUR v1 format - key only
            s3_bucket = config.bucket
            s3_key = report_key
        
        # Determine format from file extension or config
        if config.export_format:
            file_format = config.export_format
        elif s3_key.endswith('.parquet'):
            file_format = 'parquet'
        elif s3_key.endswith('.csv.gz') or s3_key.endswith('.csv'):
            file_format = 'csv'
        else:
            raise ValueError(f"Cannot determine file format for {s3_key}")
        
        # Yield records from the file
        yield from read_report_file(
            bucket=s3_bucket,
            key=s3_key,
            file_format=file_format,
            aws_creds=aws_creds
        )


def billing_period_with_partition(
    manifest: ManifestFile,
    config: AWSConfig,
    aws_creds: Dict[str, Any]
) -> Iterator[Dict[str, Any]]:
    """DLT resource that adds billing period to each record."""
    
    # First, delete existing data for this billing period
    # This would be done before yielding any records
    # Note: DLT doesn't have built-in partition deletion, so this would need
    # to be handled at the pipeline level
    
    for record in billing_period_resource(manifest, config, aws_creds):
        # Add the billing period to each record
        record['billing_period'] = manifest.billing_period
        yield record


def read_report_file(
    bucket: str,
    key: str,
    file_format: str,
    aws_creds: Dict[str, Any]
) -> Iterator[Dict[str, Any]]:
    """Read records from a CUR report file using DuckDB."""
    
    if file_format == 'parquet':
        yield from read_parquet_file(None, bucket, key, aws_creds)
    else:
        yield from read_csv_file(None, bucket, key, aws_creds)


def read_csv_file(s3_client, bucket: str, key: str) -> Iterator[Dict[str, Any]]:
    """Read CSV file from S3 and yield records."""
    response = s3_client.get_object(Bucket=bucket, Key=key)
    
    # Handle gzipped files
    if key.endswith('.gz'):
        file_content = gzip.decompress(response['Body'].read())
        csv_reader = csv.DictReader(io.StringIO(file_content.decode('utf-8')))
    else:
        csv_reader = csv.DictReader(io.StringIO(response['Body'].read().decode('utf-8')))
    
    for row in csv_reader:
        # Clean up column names (remove any prefixes)
        cleaned_row = {}
        for col, val in row.items():
            # Handle different column naming conventions
            if '/' in col:
                # Remove prefix (e.g., "lineItem/UsageAmount" -> "UsageAmount")
                clean_col = col.split('/')[-1]
            else:
                clean_col = col
            
            # Convert empty strings to None
            cleaned_row[clean_col] = val if val != '' else None
        
        yield cleaned_row


def read_parquet_file(s3_client, bucket: str, key: str, aws_creds: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Read Parquet file from S3 using DuckDB and yield records."""
    
    # Create a temporary DuckDB connection
    conn = duckdb.connect()
    
    # Install and load the httpfs extension for S3 access
    conn.execute("INSTALL httpfs")
    conn.execute("LOAD httpfs")
    
    # Configure AWS credentials for DuckDB
    conn.execute(f"SET s3_access_key_id='{aws_creds['access_key_id']}'")
    conn.execute(f"SET s3_secret_access_key='{aws_creds['secret_access_key']}'")
    conn.execute(f"SET s3_region='{aws_creds.get('region', 'us-east-1')}'")
    
    # Read directly from S3 using DuckDB
    s3_path = f"s3://{bucket}/{key}"
    
    try:
        # Query the parquet file directly
        result = conn.execute(f"SELECT * FROM read_parquet('{s3_path}')").fetchall()
        columns = [desc[0] for desc in conn.description]
        
        print(f"    Loaded {len(result)} rows from parquet file")
        print(f"    Columns: {len(columns)}")
        
        # Yield records as dictionaries
        for row in result:
            record = dict(zip(columns, row))
            yield record
            
    finally:
        conn.close()


def run_aws_pipeline(config: AWSConfig, 
                    destination: str = "duckdb",
                    table_strategy: str = "separate",
                    project_config = None) -> None:
    """Run the AWS CUR pipeline.
    
    Args:
        config: AWS configuration
        destination: DLT destination (default: duckdb)
        table_strategy: How to organize tables
            - "separate": Each billing period gets its own table (recommended)
            - "single": All data in one table with billing_period column
        project_config: Project configuration for data directory
    """
    
    # Validate configuration
    from ...core.config import Config
    temp_config = Config()
    temp_config.aws = config
    temp_config.validate_aws_config()
    
    # Set up data directory
    if project_config and project_config.data_dir:
        from pathlib import Path
        data_dir = Path(project_config.data_dir)
        data_dir.mkdir(exist_ok=True)
        db_path = data_dir / "finops.duckdb"
    else:
        db_path = "./data/finops.duckdb"
    
    # Create pipeline with centralized database
    if destination == "duckdb":
        pipeline = dlt.pipeline(
            pipeline_name="finops_pipeline",
            destination=dlt.destinations.duckdb(db_path),
            dataset_name="aws_billing"
        )
    else:
        pipeline = dlt.pipeline(
            pipeline_name="finops_pipeline",
            destination=destination,
            dataset_name="aws_billing"
        )
    
    # For single table strategy with proper partition replacement
    if table_strategy == "single":
        # We need to manually delete old data for each billing period
        # before loading new data
        print("Using single table strategy with partition replacement")
        
        # Get the manifest list first
        aws_creds = {
            'access_key_id': config.access_key_id,
            'secret_access_key': config.secret_access_key,
            'region': config.region
        }
        
        locator = ManifestLocator(
            bucket=config.bucket,
            prefix=config.prefix,
            export_name=config.export_name,
            cur_version=config.cur_version
        )
        
        manifests = locator.list_manifests(
            start_date=config.start_date,
            end_date=config.end_date,
            **aws_creds
        )
        
        # Process each billing period separately
        for manifest in manifests:
            print(f"\nProcessing {manifest.billing_period}...")
            
            # Delete existing data for this billing period
            if destination == "duckdb":
                with pipeline.sql_client() as client:
                    # Check if table exists
                    tables = client.execute_sql(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'aws_billing' AND table_name = 'billing_data'"
                    )
                    
                    if tables:
                        # Delete data for this billing period
                        delete_sql = f"""
                        DELETE FROM aws_billing.billing_data 
                        WHERE billing_period = '{manifest.billing_period}'
                        """
                        client.execute_sql(delete_sql)
                        print(f"  Deleted existing data for {manifest.billing_period}")
            
            # Load new data for this billing period
            load_info = pipeline.run(
                [dlt.resource(
                    billing_period_with_partition(manifest, config, aws_creds),
                    name="billing_data",
                    write_disposition="append"
                )]
            )
            
            # Count rows loaded for this billing period
            try:
                with pipeline.sql_client() as client:
                    result = client.execute_sql(f"SELECT COUNT(*) FROM billing_data WHERE billing_period = '{manifest.billing_period}'")
                    rows = result[0][0] if result else 0
                    print(f"  Loaded {rows:,} rows")
            except Exception as e:
                print(f"  Loaded data (row count unavailable: {e})")
    
    else:
        # Use separate tables strategy (default and recommended)
        print("Using separate tables strategy")
        print(f"Database location: {db_path}")
        
        # Run pipeline with separate tables
        load_info = pipeline.run(
            aws_cur_source(config),
            write_disposition="replace" if config.reset else "replace"
        )
        
        print(f"\nPipeline completed!")
        print(f"Load info: {load_info}")
        
        # Show some statistics by querying the database directly
        total_rows = 0
        try:
            with pipeline.sql_client() as client:
                # Get list of billing tables
                tables_result = client.execute_sql(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'aws_billing' AND table_name LIKE 'billing_%'"
                )
                
                print(f"\nTable summary:")
                for table_row in tables_result:
                    table_name = table_row[0]
                    count_result = client.execute_sql(f"SELECT COUNT(*) FROM aws_billing.{table_name}")
                    rows = count_result[0][0] if count_result else 0
                    total_rows += rows
                    print(f"  {table_name}: {rows:,} rows")
                    
        except Exception as e:
            print(f"Could not get row counts: {e}")
        
        print(f"\nTotal rows in database: {total_rows:,}")
