"""Shared fixtures for backend tests."""

import pytest
import tempfile
import os
from unittest.mock import Mock
from typing import Dict, Any

from core.backends.base import (
    DuckDBConfig, 
    ClickHouseConfig, 
    SnowflakeConfig,
    BigQueryConfig,
    PostgreSQLConfig
)


@pytest.fixture
def temp_database_path():
    """Provide a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False) as tmp:
        db_path = tmp.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def duckdb_config(temp_database_path):
    """Provide a DuckDB configuration for testing."""
    return DuckDBConfig(database_path=temp_database_path)


@pytest.fixture
def clickhouse_config():
    """Provide a ClickHouse configuration for testing."""
    return ClickHouseConfig(
        host="localhost",
        port=9000,
        http_port=8123,
        database="test_finops",
        user="test_user",
        password="test_pass",
        secure=False
    )


@pytest.fixture
def snowflake_config():
    """Provide a Snowflake configuration for testing."""
    return SnowflakeConfig(
        account="test-account",
        warehouse="test-warehouse",
        database="test-database",
        schema="test-schema",
        user="test-user",
        password="test-password"
    )


@pytest.fixture
def bigquery_config():
    """Provide a BigQuery configuration for testing."""
    return BigQueryConfig(
        project_id="test-project",
        dataset="test_dataset",
        location="US",
        credentials_path="/path/to/credentials.json"
    )


@pytest.fixture
def postgresql_config():
    """Provide a PostgreSQL configuration for testing."""
    return PostgreSQLConfig(
        host="localhost",
        port=5432,
        database="test_finops",
        schema="test_billing",
        user="test_user",
        password="test_pass"
    )


@pytest.fixture
def sample_config_dict():
    """Provide a sample configuration dictionary."""
    return {
        "project": {
            "name": "test-finops",
            "data_dir": "./test_data"
        },
        "database": {
            "backend": "duckdb",
            "duckdb": {
                "database_path": "./test_data/test.duckdb"
            },
            "clickhouse": {
                "host": "localhost",
                "port": 9000,
                "http_port": 8123,
                "database": "test_finops",
                "user": "test_user",
                "password": "test_pass"
            }
        },
        "aws": {
            "bucket": "test-bucket",
            "prefix": "test-prefix",
            "export_name": "test-export",
            "dataset_name": "aws_billing",
            "table_strategy": "separate"
        }
    }


@pytest.fixture
def mock_aws_credentials():
    """Provide mock AWS credentials for testing."""
    return {
        'aws_access_key_id': 'AKIA1234567890ABCDEF',
        'aws_secret_access_key': 'abcdefghijk1234567890ABCDEFGHIJKmnopqrst',
        'region_name': 'us-east-1'
    }


@pytest.fixture
def mock_clickhouse_client():
    """Provide a mock ClickHouse client."""
    client = Mock()
    client.command = Mock()
    client.query = Mock()
    
    # Default query result for count queries
    mock_result = Mock()
    mock_result.result_rows = [[0]]
    client.query.return_value = mock_result
    
    return client


@pytest.fixture
def sample_billing_data():
    """Provide sample billing data for testing."""
    return [
        {
            "billing_period": "2024-01",
            "service_name": "Amazon S3",
            "resource_id": "arn:aws:s3:::my-bucket",
            "usage_quantity": "100.0",
            "effective_cost": "10.50",
            "billed_cost": "10.50"
        },
        {
            "billing_period": "2024-01", 
            "service_name": "Amazon EC2",
            "resource_id": "i-1234567890abcdef0",
            "usage_quantity": "744.0",
            "effective_cost": "150.25",
            "billed_cost": "150.25"
        },
        {
            "billing_period": "2024-02",
            "service_name": "Amazon S3",
            "resource_id": "arn:aws:s3:::my-bucket",
            "usage_quantity": "120.0", 
            "effective_cost": "12.60",
            "billed_cost": "12.60"
        }
    ]


@pytest.fixture
def sample_manifest_data():
    """Provide sample CUR manifest data for testing."""
    return {
        "manifestVersion": "1.0",
        "billingPeriod": {
            "start": "20240101T000000.000Z",
            "end": "20240201T000000.000Z"
        },
        "account": "123456789012",
        "columns": [
            {"category": "lineItem", "name": "lineItemId", "type": "OptionalString"},
            {"category": "lineItem", "name": "usageStartDate", "type": "OptionalString"},
            {"category": "lineItem", "name": "productCode", "type": "OptionalString"},
            {"category": "lineItem", "name": "unblendedCost", "type": "OptionalBigDecimal"}
        ],
        "charset": "UTF-8",
        "compression": "GZIP",
        "contentType": "text/csv",
        "reportKeys": [
            "test-prefix/test-export/20240101-20240201/test-export-00001.csv.gz"
        ],
        "reportId": "test-report-id",
        "reportName": "test-export"
    }


@pytest.fixture  
def mock_dlt_destination():
    """Provide a mock DLT destination."""
    destination = Mock()
    destination.configuration = Mock()
    return destination


@pytest.fixture
def state_test_data():
    """Provide test data for state management testing."""
    return {
        "vendor": "aws",
        "export_name": "test-export",
        "billing_period": "2024-01",
        "version_id": "v123456",
        "data_format_version": "v2",
        "file_count": 5,
        "row_count": 1000
    }


class MockS3Utils:
    """Mock S3 utilities for testing."""
    
    @staticmethod
    def setup_duckdb_s3_credentials(conn, creds):
        """Mock S3 credential setup."""
        pass
    
    @staticmethod
    def build_s3_path(bucket, key):
        """Mock S3 path building."""
        return f"s3://{bucket}/{key}"
    
    @staticmethod
    def clean_column_names(record):
        """Mock column name cleaning."""
        return record


@pytest.fixture
def mock_s3_utils():
    """Provide mock S3 utilities."""
    return MockS3Utils


@pytest.fixture
def clean_backend_registry():
    """Provide a clean backend registry for testing."""
    from core.backends.base import BACKEND_REGISTRY
    
    # Save original registry
    original_registry = BACKEND_REGISTRY.copy()
    
    # Clear for test
    BACKEND_REGISTRY.clear()
    
    yield BACKEND_REGISTRY
    
    # Restore original registry
    BACKEND_REGISTRY.clear()
    BACKEND_REGISTRY.update(original_registry)