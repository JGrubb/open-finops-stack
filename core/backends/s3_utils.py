"""Common S3 utilities for database backends."""

from typing import Dict, Any


class S3Utils:
    """Utilities for S3 operations across different backends."""
    
    @staticmethod
    def setup_duckdb_s3_credentials(conn, aws_creds: Dict[str, Any]) -> None:
        """Setup S3 credentials for DuckDB connections."""
        # Install and load the httpfs extension for S3 access
        conn.execute("INSTALL httpfs")
        conn.execute("LOAD httpfs")
        
        # Configure AWS credentials for DuckDB
        conn.execute(f"SET s3_access_key_id='{aws_creds['access_key_id']}'")
        conn.execute(f"SET s3_secret_access_key='{aws_creds['secret_access_key']}'")
        conn.execute(f"SET s3_region='{aws_creds.get('region', 'us-east-1')}'")
    
    @staticmethod
    def clean_column_names(record: Dict[str, Any]) -> Dict[str, Any]:
        """Clean column names consistently across backends.
        
        Replaces '/' with '_' in column names to handle different naming conventions.
        Example: "lineItem/UnblendedCost" -> "lineItem_UnblendedCost"
        """
        cleaned_record = {}
        for col, val in record.items():
            if '/' in col:
                clean_col = col.replace('/', '_')
            else:
                clean_col = col
            cleaned_record[clean_col] = val
        return cleaned_record
    
    @staticmethod
    def build_s3_path(bucket: str, key: str) -> str:
        """Build S3 path from bucket and key."""
        return f"s3://{bucket}/{key}"
    
    @staticmethod
    def extract_aws_credentials(aws_creds: Dict[str, Any]) -> Dict[str, str]:
        """Extract and validate AWS credentials."""
        required_keys = ['access_key_id', 'secret_access_key']
        for key in required_keys:
            if key not in aws_creds:
                raise ValueError(f"Missing required AWS credential: {key}")
        
        return {
            'access_key_id': aws_creds['access_key_id'],
            'secret_access_key': aws_creds['secret_access_key'],
            'region': aws_creds.get('region', 'us-east-1'),
            'session_token': aws_creds.get('session_token')
        }