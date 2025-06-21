"""DuckLake backend implementation."""

import dlt
import duckdb
from typing import Dict, Any, Iterator
from datetime import datetime
from pathlib import Path

from .base import DatabaseBackend, StateManager, DataReader, DuckLakeConfig, BACKEND_REGISTRY
from .factory import register_backend


class DuckLakeStateManager(StateManager):
    """State management using DuckLake tables with transactional support."""
    
    def __init__(self, config: DuckLakeConfig, shared_connection=None):
        """Initialize the state tracker with DuckLake configuration.
        
        Args:
            config: DuckLake configuration object
            shared_connection: Optional shared DuckDB connection with DuckLake already attached
        """
        self.config = config
        if shared_connection:
            self.conn = shared_connection
            self._ducklake_available = True
        else:
            self.conn = None
            self._ducklake_available = False
            self._setup_connection()
        self._ensure_state_table()
    
    def _setup_connection(self):
        """Setup DuckDB connection with DuckLake extension."""
        # Create DuckDB connection
        self.conn = duckdb.connect(self.config.duckdb_path)
        
        # Install and load DuckLake extension
        try:
            self.conn.execute("INSTALL ducklake")
            self.conn.execute("LOAD ducklake")
            
            # Attach DuckLake database as ducklake schema
            self.conn.execute(f"ATTACH 'ducklake:{self.config.database_path}' AS ducklake")
            
            # Create aws_billing schema in DuckDB for DLT compatibility
            self.conn.execute("CREATE SCHEMA IF NOT EXISTS aws_billing")
            
            self._ducklake_available = True
            print("✓ DuckLake extension setup successful")
            
        except Exception as e:
            print(f"Warning: Could not setup DuckLake extension: {e}")
            print("Falling back to regular DuckDB connection")
            self._ducklake_available = False
    
    def _ensure_state_table(self):
        """Create the load_state table if it doesn't exist."""
        if self._ducklake_available:
            try:
                # Create schema for state management in DuckLake
                self.conn.execute("CREATE SCHEMA IF NOT EXISTS ducklake.billing_state")
                
                # Create the state tracking table
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS ducklake.billing_state.load_state (
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
                    
                    -- Constraints
                    PRIMARY KEY (vendor, export_name, billing_period, version_id)
                )
                """)
                
                print("✓ DuckLake state table created successfully")
                
            except Exception as e:
                print(f"Warning: Could not create state table in DuckLake: {e}")
                self._ducklake_available = False
                self._ensure_fallback_state_table()
        else:
            # Use regular DuckDB schema
            self._ensure_fallback_state_table()
    
    def _ensure_fallback_state_table(self):
        """Create state table in regular DuckDB if DuckLake fails."""
        self.conn.execute("CREATE SCHEMA IF NOT EXISTS billing_state")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS billing_state.load_state (
                vendor VARCHAR NOT NULL,
                export_name VARCHAR NOT NULL,
                billing_period VARCHAR NOT NULL,
                version_id VARCHAR NOT NULL,
                data_format_version VARCHAR NOT NULL,
                current_version BOOLEAN DEFAULT FALSE,
                load_timestamp TIMESTAMP NOT NULL,
                load_completed BOOLEAN NOT NULL DEFAULT FALSE,
                row_count INTEGER,
                file_count INTEGER,
                PRIMARY KEY (vendor, export_name, billing_period, version_id)
            )
        """)
    
    def is_version_loaded(self, vendor: str, export_name: str, billing_period: str, version_id: str) -> bool:
        """Check if a specific version has already been loaded."""
        if self._ducklake_available:
            try:
                result = self.conn.execute("""
                    SELECT load_completed FROM ducklake.billing_state.load_state
                    WHERE vendor = ? AND export_name = ? AND billing_period = ? AND version_id = ?
                """, [vendor, export_name, billing_period, version_id]).fetchone()
            except:
                # Fallback to regular DuckDB table
                result = self.conn.execute("""
                    SELECT load_completed FROM billing_state.load_state
                    WHERE vendor = ? AND export_name = ? AND billing_period = ? AND version_id = ?
                """, [vendor, export_name, billing_period, version_id]).fetchone()
        else:
            result = self.conn.execute("""
                SELECT load_completed FROM billing_state.load_state
                WHERE vendor = ? AND export_name = ? AND billing_period = ? AND version_id = ?
            """, [vendor, export_name, billing_period, version_id]).fetchone()
        
        return result is not None and result[0]
    
    def _get_state_table(self) -> str:
        """Get the appropriate state table name based on DuckLake availability."""
        if self._ducklake_available:
            return "ducklake.billing_state.load_state"
        else:
            return "billing_state.load_state"
    
    def start_load(self, vendor: str, export_name: str, billing_period: str, version_id: str, 
                   data_format_version: str, file_count: int) -> None:
        """Mark the start of a data load."""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO ducklake.billing_state.load_state
                (vendor, export_name, billing_period, version_id, data_format_version, 
                 load_timestamp, load_completed, file_count)
                VALUES (?, ?, ?, ?, ?, ?, FALSE, ?)
            """, [vendor, export_name, billing_period, version_id, data_format_version, 
                  datetime.now(), file_count])
        except:
            # Fallback to regular DuckDB table
            self.conn.execute("""
                INSERT OR REPLACE INTO billing_state.load_state
                (vendor, export_name, billing_period, version_id, data_format_version, 
                 load_timestamp, load_completed, file_count)
                VALUES (?, ?, ?, ?, ?, ?, FALSE, ?)
            """, [vendor, export_name, billing_period, version_id, data_format_version, 
                  datetime.now(), file_count])
    
    def complete_load(self, vendor: str, export_name: str, billing_period: str, version_id: str, 
                      row_count: int) -> None:
        """Mark the completion of a data load."""
        try:
            self.conn.execute("""
                UPDATE ducklake.billing_state.load_state
                SET load_completed = TRUE, row_count = ?
                WHERE vendor = ? AND export_name = ? AND billing_period = ? AND version_id = ?
            """, [row_count, vendor, export_name, billing_period, version_id])
        except:
            # Fallback to regular DuckDB table
            self.conn.execute("""
                UPDATE billing_state.load_state
                SET load_completed = TRUE, row_count = ?
                WHERE vendor = ? AND export_name = ? AND billing_period = ? AND version_id = ?
            """, [row_count, vendor, export_name, billing_period, version_id])
    
    def fail_load(self, vendor: str, export_name: str, billing_period: str, version_id: str, 
                  error: str) -> None:
        """Mark a data load as failed."""
        # For now, just delete the incomplete load record
        try:
            self.conn.execute("""
                DELETE FROM ducklake.billing_state.load_state
                WHERE vendor = ? AND export_name = ? AND billing_period = ? AND version_id = ?
            """, [vendor, export_name, billing_period, version_id])
        except:
            # Fallback to regular DuckDB table
            self.conn.execute("""
                DELETE FROM billing_state.load_state
                WHERE vendor = ? AND export_name = ? AND billing_period = ? AND version_id = ?
            """, [vendor, export_name, billing_period, version_id])
    
    def get_current_versions(self, vendor: str, export_name: str) -> Dict[str, str]:
        """Get the current version IDs for each billing period."""
        try:
            results = self.conn.execute("""
                SELECT billing_period, version_id FROM ducklake.billing_state.load_state
                WHERE vendor = ? AND export_name = ? AND load_completed = TRUE
                ORDER BY billing_period
            """, [vendor, export_name]).fetchall()
        except:
            # Fallback to regular DuckDB table
            results = self.conn.execute("""
                SELECT billing_period, version_id FROM billing_state.load_state
                WHERE vendor = ? AND export_name = ? AND load_completed = TRUE
                ORDER BY billing_period
            """, [vendor, export_name]).fetchall()
        
        return {period: version for period, version in results}
    
    def get_version_history(self, vendor: str, export_name: str, billing_period: str) -> list:
        """Get the version history for a specific billing period."""
        try:
            results = self.conn.execute("""
                SELECT version_id, load_timestamp, row_count, file_count, data_format_version
                FROM ducklake.billing_state.load_state
                WHERE vendor = ? AND export_name = ? AND billing_period = ? AND load_completed = TRUE
                ORDER BY load_timestamp DESC
            """, [vendor, export_name, billing_period]).fetchall()
        except:
            # Fallback to regular DuckDB table
            results = self.conn.execute("""
                SELECT version_id, load_timestamp, row_count, file_count, data_format_version
                FROM billing_state.load_state
                WHERE vendor = ? AND export_name = ? AND billing_period = ? AND load_completed = TRUE
                ORDER BY load_timestamp DESC
            """, [vendor, export_name, billing_period]).fetchall()
        
        return [
            {
                'version_id': row[0],
                'load_timestamp': row[1],
                'row_count': row[2],
                'file_count': row[3],
                'data_format_version': row[4]
            }
            for row in results
        ]


class DuckLakeDataReader(DataReader):
    """Data reader using DuckLake capabilities."""
    
    def __init__(self, config: DuckLakeConfig, shared_connection=None):
        """Initialize data reader with DuckLake configuration."""
        self.config = config
        if shared_connection:
            self.conn = shared_connection
        else:
            self.conn = duckdb.connect(self.config.duckdb_path)
            self._setup_connection()
    
    def _setup_connection(self):
        """Setup DuckDB connection with DuckLake extension."""
        try:
            self.conn.execute("INSTALL ducklake")
            self.conn.execute("LOAD ducklake")
            self.conn.execute("INSTALL httpfs")
            self.conn.execute("LOAD httpfs")
            
            # Attach DuckLake database as ducklake schema
            self.conn.execute(f"ATTACH 'ducklake:{self.config.database_path}' AS ducklake")
            
            # Create aws_billing schema in DuckDB for DLT compatibility
            self.conn.execute("CREATE SCHEMA IF NOT EXISTS aws_billing")
            
        except Exception as e:
            print(f"Warning: DataReader could not setup DuckLake extension: {e}")
            print("Falling back to regular DuckDB with httpfs")
            self.conn.execute("INSTALL httpfs")
            self.conn.execute("LOAD httpfs")
    
    def read_csv_file(self, bucket: str, key: str, aws_creds: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """Read CSV file from S3 using DuckDB's httpfs extension."""
        s3_uri = f"s3://{bucket}/{key}"
        
        # Configure AWS credentials for DuckDB
        if aws_creds.get('access_key_id'):
            self.conn.execute(f"SET s3_access_key_id='{aws_creds['access_key_id']}'")
        if aws_creds.get('secret_access_key'):
            self.conn.execute(f"SET s3_secret_access_key='{aws_creds['secret_access_key']}'")
        if aws_creds.get('region'):
            self.conn.execute(f"SET s3_region='{aws_creds['region']}'")
        
        # Use DuckDB's native S3 reading capabilities
        query = f"""
            SELECT * FROM read_csv_auto('{s3_uri}', 
                compression='gzip',
                header=true,
                sample_size=-1
            )
        """
        
        try:
            result = self.conn.execute(query)
            columns = [desc[0] for desc in result.description]
            
            for row in result.fetchall():
                yield dict(zip(columns, row))
                
        except Exception as e:
            print(f"Error reading CSV from {s3_uri}: {e}")
            raise
    
    def read_parquet_file(self, bucket: str, key: str, aws_creds: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """Read Parquet file from S3 using DuckDB's httpfs extension."""
        s3_uri = f"s3://{bucket}/{key}"
        
        # Configure AWS credentials for DuckDB
        if aws_creds.get('access_key_id'):
            self.conn.execute(f"SET s3_access_key_id='{aws_creds['access_key_id']}'")
        if aws_creds.get('secret_access_key'):
            self.conn.execute(f"SET s3_secret_access_key='{aws_creds['secret_access_key']}'")
        if aws_creds.get('region'):
            self.conn.execute(f"SET s3_region='{aws_creds['region']}'")
        
        query = f"SELECT * FROM read_parquet('{s3_uri}')"
        
        try:
            result = self.conn.execute(query)
            columns = [desc[0] for desc in result.description]
            
            for row in result.fetchall():
                yield dict(zip(columns, row))
                
        except Exception as e:
            print(f"Error reading Parquet from {s3_uri}: {e}")
            raise


class DuckLakeBackend(DatabaseBackend):
    """DuckLake backend implementation with lakehouse capabilities."""
    
    def __init__(self, config: DuckLakeConfig):
        """Initialize DuckLake backend with configuration."""
        self.config = config
        self._ensure_directories()
        self._shared_connection = None
        self._ducklake_available = False
        self._setup_shared_connection()
    
    def _ensure_directories(self):
        """Ensure necessary directories exist."""
        # Create data directory if it doesn't exist
        data_dir = Path(self.config.database_path).parent
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create DuckDB file directory if different
        duckdb_dir = Path(self.config.duckdb_path).parent
        duckdb_dir.mkdir(parents=True, exist_ok=True)
    
    def _setup_shared_connection(self):
        """Setup a shared DuckDB connection with DuckLake extension."""
        # Create a single shared connection
        self._shared_connection = duckdb.connect(self.config.duckdb_path)
        
        try:
            # Remove existing database and files to start completely fresh
            import os
            import shutil
            
            if os.path.exists(self.config.database_path):
                os.remove(self.config.database_path)
                print(f"Removed existing DuckLake metadata: {self.config.database_path}")
                
            files_dir = f"{self.config.database_path}.files"
            if os.path.exists(files_dir):
                shutil.rmtree(files_dir)
                print(f"Removed existing DuckLake files directory: {files_dir}")
                
            wal_file = f"{self.config.database_path}.wal"
            if os.path.exists(wal_file):
                os.remove(wal_file)
                print(f"Removed existing DuckLake WAL: {wal_file}")
            
            # Install and load extensions
            self._shared_connection.execute("INSTALL ducklake")
            self._shared_connection.execute("LOAD ducklake")
            self._shared_connection.execute("INSTALL httpfs")
            self._shared_connection.execute("LOAD httpfs")
            
            # Check if ducklake alias already exists and detach if needed
            try:
                databases = self._shared_connection.execute("SHOW DATABASES").fetchall()
                db_names = [db[0] for db in databases]
                if 'ducklake' in db_names:
                    self._shared_connection.execute("DETACH ducklake")
                    print("Detached existing ducklake database")
            except:
                pass  # No existing attachment
            
            # Attach DuckLake database as ducklake schema
            self._shared_connection.execute(f"ATTACH 'ducklake:{self.config.database_path}' AS ducklake")
            
            # Create aws_billing schema in DuckDB for DLT compatibility
            self._shared_connection.execute("CREATE SCHEMA IF NOT EXISTS aws_billing")
            
            print("✓ DuckLake backend setup successful")
            self._ducklake_available = True
            
        except Exception as e:
            print(f"Warning: Could not setup DuckLake backend: {e}")
            print("Falling back to regular DuckDB")
            self._ducklake_available = False
            # Ensure httpfs is available for S3 access
            try:
                self._shared_connection.execute("INSTALL httpfs")
                self._shared_connection.execute("LOAD httpfs")
            except:
                pass
    
    def get_dlt_destination(self) -> Any:
        """Get DLT destination for DuckLake backend."""
        # Use DuckDB destination with DuckLake attached
        return dlt.destinations.duckdb(
            credentials=str(self.config.duckdb_path)
        )
    
    def create_state_manager(self) -> StateManager:
        """Create a state manager for this backend."""
        return DuckLakeStateManager(self.config, self._shared_connection)
    
    def create_data_reader(self) -> DataReader:
        """Create a data reader for this backend."""
        return DuckLakeDataReader(self.config, self._shared_connection)
    
    def supports_native_s3(self) -> bool:
        """Check if this backend supports native S3 reading."""
        return True
    
    def get_database_path_or_connection(self) -> str:
        """Get the database path or connection string."""
        return str(self.config.duckdb_path)
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'DuckLakeBackend':
        """Create DuckLake backend from configuration dictionary."""
        database_config = config.get("database", {})
        ducklake_config = database_config.get("ducklake", {})
        
        dl_config = DuckLakeConfig(
            database_path=ducklake_config.get("database_path", "./data/finops.ducklake"),
            duckdb_path=ducklake_config.get("duckdb_path", "./data/finops-ducklake.duckdb"),
            compression=ducklake_config.get("compression", "zstd"),
            enable_encryption=ducklake_config.get("enable_encryption", False),
            partition_strategy=ducklake_config.get("partition_strategy", "monthly")
        )
        
        return cls(dl_config)


# Register the DuckLake backend
register_backend("ducklake", DuckLakeBackend)