"""State tracking for cloud billing data loads."""

from datetime import datetime
from typing import Optional, List, Dict, Any
import duckdb
from pathlib import Path


class LoadStateTracker:
    """Tracks the state of billing data loads across all cloud vendors.
    
    This class manages a vendor-agnostic state table that tracks:
    - Which data versions have been loaded
    - Load completion status
    - Current active version for each billing period
    - Load metadata and error tracking
    """
    
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
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_current_versions 
                ON billing_state.load_state(vendor, export_name, current_version)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_billing_period 
                ON billing_state.load_state(vendor, export_name, billing_period)
            """)
            
        finally:
            conn.close()
    
    def is_version_loaded(self, vendor: str, export_name: str, 
                         billing_period: str, version_id: str) -> bool:
        """Check if a specific version has been successfully loaded.
        
        Args:
            vendor: Cloud vendor ('aws', 'azure', 'gcp')
            export_name: Name of the export/dataset
            billing_period: Billing period (e.g., '2024-01')
            version_id: Vendor-specific version identifier
            
        Returns:
            True if this version has been successfully loaded
        """
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
        """Record the start of a new data load.
        
        Args:
            vendor: Cloud vendor ('aws', 'azure', 'gcp')
            export_name: Name of the export/dataset
            billing_period: Billing period (e.g., '2024-01')
            version_id: Vendor-specific version identifier
            data_format_version: Format version (e.g., 'v1', 'v2')
            file_count: Number of files to be processed
        """
        conn = duckdb.connect(self.db_path)
        try:
            # Insert or update the load record
            conn.execute("""
                INSERT INTO billing_state.load_state 
                (vendor, export_name, billing_period, version_id, data_format_version,
                 load_timestamp, load_completed, file_count)
                VALUES (?, ?, ?, ?, ?, ?, FALSE, ?)
                ON CONFLICT (vendor, export_name, billing_period, version_id)
                DO UPDATE SET 
                    load_timestamp = EXCLUDED.load_timestamp,
                    load_completed = FALSE,
                    file_count = EXCLUDED.file_count,
                    error_message = NULL
            """, [vendor, export_name, billing_period, version_id, 
                  data_format_version, datetime.now(), file_count])
            
        finally:
            conn.close()
    
    def complete_load(self, vendor: str, export_name: str, billing_period: str,
                     version_id: str, row_count: int) -> None:
        """Mark a load as successfully completed and set it as the current version.
        
        Args:
            vendor: Cloud vendor ('aws', 'azure', 'gcp')
            export_name: Name of the export/dataset
            billing_period: Billing period (e.g., '2024-01')
            version_id: Vendor-specific version identifier
            row_count: Number of rows loaded
        """
        conn = duckdb.connect(self.db_path)
        try:
            # Start a transaction
            conn.begin()
            
            # Mark all other versions for this billing period as not current
            conn.execute("""
                UPDATE billing_state.load_state 
                SET current_version = FALSE
                WHERE vendor = ? 
                AND export_name = ? 
                AND billing_period = ?
            """, [vendor, export_name, billing_period])
            
            # Mark this load as completed and current
            conn.execute("""
                UPDATE billing_state.load_state 
                SET load_completed = TRUE,
                    current_version = TRUE,
                    row_count = ?,
                    error_message = NULL
                WHERE vendor = ? 
                AND export_name = ? 
                AND billing_period = ? 
                AND version_id = ?
            """, [row_count, vendor, export_name, billing_period, version_id])
            
            # Commit the transaction
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def fail_load(self, vendor: str, export_name: str, billing_period: str,
                  version_id: str, error_message: str) -> None:
        """Mark a load as failed with an error message.
        
        Args:
            vendor: Cloud vendor ('aws', 'azure', 'gcp')
            export_name: Name of the export/dataset
            billing_period: Billing period (e.g., '2024-01')
            version_id: Vendor-specific version identifier
            error_message: Description of the error
        """
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
    
    def get_current_versions(self, vendor: str, export_name: str) -> List[Dict[str, Any]]:
        """Get all current versions for a vendor and export.
        
        Args:
            vendor: Cloud vendor ('aws', 'azure', 'gcp')
            export_name: Name of the export/dataset
            
        Returns:
            List of current version records
        """
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
                           billing_period: str) -> List[Dict[str, Any]]:
        """Get the version history for a specific billing period.
        
        Args:
            vendor: Cloud vendor ('aws', 'azure', 'gcp')
            export_name: Name of the export/dataset
            billing_period: Billing period (e.g., '2024-01')
            
        Returns:
            List of all versions for this billing period
        """
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