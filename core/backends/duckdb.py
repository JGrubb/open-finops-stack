"""DuckDB backend implementation."""

import dlt
import duckdb
from typing import Dict, Any, Iterator
from datetime import datetime
from pathlib import Path

from .base import DatabaseBackend, StateManager, DataReader, DuckDBConfig, BACKEND_REGISTRY
from .factory import register_backend
from .s3_utils import S3Utils


class DuckDBStateManager(StateManager):
    """State management using DuckDB tables."""
    
    def __init__(self, db_path: str):
        """Initialize the state tracker with a database path.
        
        Args:
            db_path: Path to the DuckDB database file
        """
        self.db_path = db_path
        self._ensure_state_table()
    
    def _ensure_state_table(self):
        """Create the load_state table if it doesn't exist."""
        conn = duckdb.connect(self.db_path)
        try:
            # Create schema if it doesn't exist
            conn.execute("CREATE SCHEMA IF NOT EXISTS billing_state")
            
            # Create the state tracking table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS billing_state.load_state (
                    -- Primary identification
                    vendor VARCHAR NOT NULL,              -- 'aws', 'azure', 'gcp'
                    export_name VARCHAR NOT NULL,         -- User's export/dataset name
                    billing_period VARCHAR NOT NULL,      -- '2024-01'
                    version_id VARCHAR NOT NULL,          -- Vendor-specific version ID
                    
                    -- Version and configuration
                    data_format_version VARCHAR NOT NULL, -- 'v1', 'v2', etc.
                    current_version BOOLEAN DEFAULT FALSE,
                    
                    -- Load metadata
                    load_timestamp TIMESTAMP NOT NULL,
                    load_completed BOOLEAN NOT NULL DEFAULT FALSE,
                    row_count INTEGER,
                    file_count INTEGER,
                    
                    -- Error tracking
                    error_message VARCHAR,
                    
                    PRIMARY KEY (vendor, export_name, billing_period, version_id)
                )
            """)
            
            # Create indexes for common queries
            # Temporarily disabled due to DuckDB constraint issues
            # conn.execute("""
            #     CREATE INDEX IF NOT EXISTS idx_current_versions 
            #     ON billing_state.load_state(vendor, export_name, current_version)
            # """)
            # 
            # conn.execute("""
            #     CREATE INDEX IF NOT EXISTS idx_billing_period 
            #     ON billing_state.load_state(vendor, export_name, billing_period)
            # """)
            
        finally:
            conn.close()
    
    def is_version_loaded(self, vendor: str, export_name: str, 
                         billing_period: str, version_id: str) -> bool:
        """Check if a specific version has been successfully loaded."""
        conn = duckdb.connect(self.db_path)
        try:
            result = conn.execute("""
                SELECT load_completed 
                FROM billing_state.load_state 
                WHERE vendor = ? 
                AND export_name = ? 
                AND billing_period = ? 
                AND version_id = ?
                AND load_completed = TRUE
            """, [vendor, export_name, billing_period, version_id]).fetchone()
            
            return result is not None
            
        finally:
            conn.close()
    
    def start_load(self, vendor: str, export_name: str, billing_period: str,
                   version_id: str, data_format_version: str, file_count: int) -> None:
        """Record the start of a new data load."""
        conn = duckdb.connect(self.db_path)
        try:
            # Check if record exists first
            existing = conn.execute("""
                SELECT COUNT(*) FROM billing_state.load_state 
                WHERE vendor = ? AND export_name = ? AND billing_period = ? AND version_id = ?
            """, [vendor, export_name, billing_period, version_id]).fetchone()[0]
            
            if existing > 0:
                # Update existing record
                conn.execute("""
                    UPDATE billing_state.load_state 
                    SET load_timestamp = ?, 
                        load_completed = FALSE,
                        file_count = ?,
                        error_message = NULL
                    WHERE vendor = ? AND export_name = ? AND billing_period = ? AND version_id = ?
                """, [datetime.now(), file_count, vendor, export_name, billing_period, version_id])
            else:
                # Insert new record
                conn.execute("""
                    INSERT INTO billing_state.load_state 
                    (vendor, export_name, billing_period, version_id, data_format_version,
                     load_timestamp, load_completed, file_count)
                    VALUES (?, ?, ?, ?, ?, ?, FALSE, ?)
                """, [vendor, export_name, billing_period, version_id, 
                      data_format_version, datetime.now(), file_count])
            
        finally:
            conn.close()
    
    def complete_load(self, vendor: str, export_name: str, billing_period: str,
                     version_id: str, row_count: int) -> None:
        """Mark a load as successfully completed and set it as the current version."""
        conn = duckdb.connect(self.db_path)
        try:
            # First, mark all other versions for this billing period as not current
            conn.execute("""
                UPDATE billing_state.load_state 
                SET current_version = FALSE
                WHERE vendor = ? 
                AND export_name = ? 
                AND billing_period = ?
                AND version_id <> ?
            """, [vendor, export_name, billing_period, version_id])
            
            # Update load_completed and row_count separately to avoid constraint issues
            conn.execute("""
                UPDATE billing_state.load_state 
                SET load_completed = TRUE
                WHERE vendor = ? 
                AND export_name = ? 
                AND billing_period = ? 
                AND version_id = ?
            """, [vendor, export_name, billing_period, version_id])
            
            conn.execute("""
                UPDATE billing_state.load_state 
                SET current_version = TRUE
                WHERE vendor = ? 
                AND export_name = ? 
                AND billing_period = ? 
                AND version_id = ?
            """, [vendor, export_name, billing_period, version_id])
            
            conn.execute("""
                UPDATE billing_state.load_state 
                SET row_count = ?
                WHERE vendor = ? 
                AND export_name = ? 
                AND billing_period = ? 
                AND version_id = ?
            """, [row_count, vendor, export_name, billing_period, version_id])
            
        finally:
            conn.close()
    
    def fail_load(self, vendor: str, export_name: str, billing_period: str,
                  version_id: str, error_message: str) -> None:
        """Mark a load as failed with an error message."""
        conn = duckdb.connect(self.db_path)
        try:
            conn.execute("""
                UPDATE billing_state.load_state 
                SET load_completed = FALSE,
                    error_message = ?
                WHERE vendor = ? 
                AND export_name = ? 
                AND billing_period = ? 
                AND version_id = ?
            """, [error_message, vendor, export_name, billing_period, version_id])
            
        finally:
            conn.close()
    
    def get_current_versions(self, vendor: str, export_name: str) -> list:
        """Get all current versions for a vendor and export."""
        conn = duckdb.connect(self.db_path)
        try:
            result = conn.execute("""
                SELECT 
                    billing_period,
                    version_id,
                    data_format_version,
                    load_timestamp,
                    row_count,
                    file_count
                FROM billing_state.load_state 
                WHERE vendor = ? 
                AND export_name = ? 
                AND current_version = TRUE
                ORDER BY billing_period DESC
            """, [vendor, export_name]).fetchall()
            
            return [
                {
                    'billing_period': row[0],
                    'version_id': row[1],
                    'data_format_version': row[2],
                    'load_timestamp': row[3],
                    'row_count': row[4],
                    'file_count': row[5]
                }
                for row in result
            ]
            
        finally:
            conn.close()
    
    def get_version_history(self, vendor: str, export_name: str, 
                           billing_period: str) -> list:
        """Get the version history for a specific billing period."""
        conn = duckdb.connect(self.db_path)
        try:
            result = conn.execute("""
                SELECT 
                    version_id,
                    data_format_version,
                    current_version,
                    load_timestamp,
                    load_completed,
                    row_count,
                    file_count,
                    error_message
                FROM billing_state.load_state 
                WHERE vendor = ? 
                AND export_name = ? 
                AND billing_period = ?
                ORDER BY load_timestamp DESC
            """, [vendor, export_name, billing_period]).fetchall()
            
            return [
                {
                    'version_id': row[0],
                    'data_format_version': row[1],
                    'current_version': row[2],
                    'load_timestamp': row[3],
                    'load_completed': row[4],
                    'row_count': row[5],
                    'file_count': row[6],
                    'error_message': row[7]
                }
                for row in result
            ]
            
        finally:
            conn.close()


class DuckDBDataReader(DataReader):
    """DuckDB's native S3 reading capabilities."""
    
    def __init__(self, config: DuckDBConfig):
        self.config = config
    
    def read_csv_file(self, bucket: str, key: str, aws_creds: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """Read CSV file from S3 using DuckDB and yield records."""
        
        # Create a temporary DuckDB connection
        conn = duckdb.connect()
        
        # Setup S3 credentials using common utility
        S3Utils.setup_duckdb_s3_credentials(conn, aws_creds)
        
        # Build S3 path using common utility
        s3_path = S3Utils.build_s3_path(bucket, key)
        
        try:
            # Handle gzipped files - DuckDB can read them directly
            if key.endswith('.gz'):
                result = conn.execute(f"SELECT * FROM read_csv_auto('{s3_path}', compression='gzip')").fetchall()
            else:
                result = conn.execute(f"SELECT * FROM read_csv_auto('{s3_path}')").fetchall()
                
            columns = [desc[0] for desc in conn.description]
            
            print(f"    Loaded {len(result)} rows from CSV file")
            print(f"    Columns: {len(columns)}")
            
            # Yield records as dictionaries
            for row in result:
                record = dict(zip(columns, row))
                # Clean up column names using common utility
                cleaned_record = S3Utils.clean_column_names(record)
                yield cleaned_record
                
        finally:
            conn.close()
    
    def read_parquet_file(self, bucket: str, key: str, aws_creds: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """Read Parquet file from S3 using DuckDB and yield records."""
        
        # Create a temporary DuckDB connection
        conn = duckdb.connect()
        
        # Setup S3 credentials using common utility
        S3Utils.setup_duckdb_s3_credentials(conn, aws_creds)
        
        # Build S3 path using common utility
        s3_path = S3Utils.build_s3_path(bucket, key)
        
        try:
            # Query the parquet file directly
            result = conn.execute(f"SELECT * FROM read_parquet('{s3_path}')").fetchall()
            columns = [desc[0] for desc in conn.description]
            
            print(f"    Loaded {len(result)} rows from parquet file")
            print(f"    Columns: {len(columns)}")
            
            # Yield records as dictionaries
            for row in result:
                record = dict(zip(columns, row))
                # Clean up column names using common utility
                cleaned_record = S3Utils.clean_column_names(record)
                yield cleaned_record
                
        finally:
            conn.close()


class DuckDBBackend(DatabaseBackend):
    """DuckDB backend implementation."""
    
    def __init__(self, config: DuckDBConfig):
        self.config = config
        
        # Ensure database directory exists
        db_path = Path(config.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def get_dlt_destination(self):
        """Get DLT destination for DuckDB."""
        return dlt.destinations.duckdb(self.config.database_path)
    
    def create_state_manager(self) -> StateManager:
        """Create DuckDB state management instance."""
        return DuckDBStateManager(self.config.database_path)
    
    def create_data_reader(self) -> DataReader:
        """Create DuckDB data reader instance."""
        return DuckDBDataReader(self.config)
    
    def supports_native_s3(self) -> bool:
        """DuckDB has excellent native S3 support."""
        return True
    
    def get_database_path_or_connection(self) -> str:
        """Get database path for DuckDB."""
        return self.config.database_path
    
    def get_table_reference(self, dataset_name: str, table_name: str) -> str:
        """Get the correct table reference for DuckDB.
        
        DuckDB uses schema.table notation
        """
        return f"{dataset_name}.{table_name}"
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'DuckDBBackend':
        """Create DuckDB backend from configuration dictionary."""
        database_config = config.get("database", {})
        duckdb_config = database_config.get("duckdb", {})
        
        db_config = DuckDBConfig(
            database_path=duckdb_config.get("database_path", "./data/finops.duckdb")
        )
        
        return cls(db_config)


# Register the DuckDB backend
register_backend("duckdb", DuckDBBackend)