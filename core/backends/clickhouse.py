"""ClickHouse database backend implementation."""

import dlt
import clickhouse_connect
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Iterator

from core.backends.base import (
    DatabaseBackend,
    StateManager,
    DataReader,
    ClickHouseConfig,
    BACKEND_REGISTRY,
)




class ClickHouseBackend(DatabaseBackend):
    """ClickHouse database backend."""

    def __init__(self, config: ClickHouseConfig):
        self.config = config
        self.client = clickhouse_connect.get_client(
            host=config.host,
            port=config.http_port,  # Use HTTP port for clickhouse_connect
            user=config.user,
            password=config.password,
            database=config.database,
            secure=False,  # Disable SSL for HTTP connection
        )

    def get_dlt_destination(self) -> Any:
        """Get DLT destination for this backend."""
        creds = self.config.__dict__.copy()
        creds['secure'] = False  # Disable SSL for DLT destination too
        return dlt.destinations.clickhouse(
            credentials=creds,
            database_name=self.config.database,
        )

    def create_state_manager(self) -> "StateManager":
        """Create state management instance."""
        return ClickHouseStateManager(self.client, self.config.database)

    def create_data_reader(self) -> Optional["DataReader"]:
        """Create data reader for S3 files."""
        # ClickHouse uses S3 table functions for direct loading,
        # not Python-based reading. Return None to trigger fallback.
        return None

    def supports_native_s3(self) -> bool:
        """Whether backend can read directly from S3."""
        return True  # ClickHouse has excellent S3 integration

    def get_database_path_or_connection(self) -> str:
        """Get database path or connection string."""
        return f"clickhouse://{self.config.user}@{self.config.host}:{self.config.port}/{self.config.database}"

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'ClickHouseBackend':
        """Create backend instance from configuration dictionary."""
        database_config = config.get("database", {})
        clickhouse_config = database_config.get("clickhouse", {})
        
        ch_config = ClickHouseConfig(
            host=clickhouse_config.get("host", "localhost"),
            port=clickhouse_config.get("port", 9000),
            http_port=clickhouse_config.get("http_port", 8123),
            database=clickhouse_config.get("database", "finops"),
            user=clickhouse_config.get("user", "default"),
            password=clickhouse_config.get("password", ""),
            secure=clickhouse_config.get("secure", False)
        )
        
        return cls(ch_config)


class ClickHouseStateManager(StateManager):
    """State manager for ClickHouse."""

    def __init__(self, client: clickhouse_connect.driver.Client, database: str):
        self.client = client
        self.database = database
        self.table_name = "load_state"
        self._create_state_table_if_not_exists()

    def _create_state_table_if_not_exists(self):
        """Create the state table if it doesn't exist."""
        query = f"""
        CREATE TABLE IF NOT EXISTS {self.database}.{self.table_name} (
            vendor String,
            export_name String,
            billing_period String,
            version_id String,
            data_format_version String,
            file_count UInt32,
            row_count UInt64,
            status String,
            error_message String,
            started_at DateTime,
            completed_at DateTime,
            is_current UInt8
        ) ENGINE = MergeTree()
        ORDER BY (vendor, export_name, billing_period, started_at)
        """
        self.client.command(query)

    def is_version_loaded(
        self, vendor: str, export_name: str, billing_period: str, version_id: str
    ) -> bool:
        """Check if a specific version has been successfully loaded."""
        query = f"""
        SELECT count() FROM {self.database}.{self.table_name}
        WHERE vendor = %(vendor)s
          AND export_name = %(export_name)s
          AND billing_period = %(billing_period)s
          AND version_id = %(version_id)s
          AND status = 'completed'
        """
        params = {
            "vendor": vendor,
            "export_name": export_name,
            "billing_period": billing_period,
            "version_id": version_id,
        }
        result = self.client.query(query, parameters=params)
        return result.result_rows[0][0] > 0

    def start_load(
        self,
        vendor: str,
        export_name: str,
        billing_period: str,
        version_id: str,
        data_format_version: str,
        file_count: int,
    ) -> None:
        """Record the start of a new data load."""
        query = f"""
        INSERT INTO {self.database}.{self.table_name} (
            vendor, export_name, billing_period, version_id, data_format_version,
            file_count, status, started_at, is_current
        ) VALUES (
            %(vendor)s, %(export_name)s, %(billing_period)s, %(version_id)s,
            %(data_format_version)s, %(file_count)s, 'started', now(), 0
        )
        """
        params = {
            "vendor": vendor,
            "export_name": export_name,
            "billing_period": billing_period,
            "version_id": version_id,
            "data_format_version": data_format_version,
            "file_count": file_count,
        }
        self.client.command(query, parameters=params)

    def complete_load(
        self, vendor: str, export_name: str, billing_period: str, version_id: str, row_count: int
    ) -> None:
        """Mark a load as successfully completed and set it as the current version."""
        try:
            # Step 1: Update previous versions to not current
            update_query = f"""
            ALTER TABLE {self.database}.{self.table_name}
            UPDATE is_current = 0
            WHERE vendor = %(vendor)s
              AND export_name = %(export_name)s
              AND billing_period = %(billing_period)s
              AND is_current = 1
            """
            params = {
                "vendor": vendor,
                "export_name": export_name,
                "billing_period": billing_period,
            }
            self.client.command(update_query, parameters=params)

            # Step 2: Mark current load as completed and current
            complete_query = f"""
            ALTER TABLE {self.database}.{self.table_name}
            UPDATE status = 'completed', completed_at = now(), row_count = %(row_count)s, is_current = 1
            WHERE vendor = %(vendor)s
              AND export_name = %(export_name)s
              AND billing_period = %(billing_period)s
              AND version_id = %(version_id)s
            """
            params["row_count"] = row_count
            params["version_id"] = version_id
            self.client.command(complete_query, parameters=params)
            
        except Exception as e:
            # Log error and re-raise with context
            error_msg = f"Failed to complete load for {vendor}/{export_name}/{billing_period}: {e}"
            print(f"ERROR: {error_msg}")
            raise RuntimeError(error_msg) from e

    def fail_load(
        self,
        vendor: str,
        export_name: str,
        billing_period: str,
        version_id: str,
        error_message: str,
    ) -> None:
        """Mark a load as failed with an error message."""
        query = f"""
        ALTER TABLE {self.database}.{self.table_name}
        UPDATE status = 'failed', error_message = %(error_message)s
        WHERE vendor = %(vendor)s
          AND export_name = %(export_name)s
          AND billing_period = %(billing_period)s
          AND version_id = %(version_id)s
        """
        params = {
            "vendor": vendor,
            "export_name": export_name,
            "billing_period": billing_period,
            "version_id": version_id,
            "error_message": error_message,
        }
        self.client.command(query, parameters=params)

    def get_current_versions(
        self, vendor: str, export_name: str
    ) -> List[Dict[str, Any]]:
        """Get all current versions for a vendor and export."""
        query = f"""
        SELECT billing_period, version_id, data_format_version, started_at, row_count, file_count
        FROM {self.database}.{self.table_name}
        WHERE vendor = %(vendor)s
          AND export_name = %(export_name)s
          AND is_current = 1
        ORDER BY billing_period DESC
        """
        params = {"vendor": vendor, "export_name": export_name}
        result = self.client.query(query, parameters=params)
        
        return [
            {
                'billing_period': row[0],
                'version_id': row[1],
                'data_format_version': row[2],
                'load_timestamp': row[3],
                'row_count': row[4],
                'file_count': row[5]
            }
            for row in result.result_rows
        ]

    def get_version_history(
        self, vendor: str, export_name: str, billing_period: str
    ) -> List[Dict[str, Any]]:
        """Get the version history for a specific billing period."""
        query = f"""
        SELECT version_id, data_format_version, is_current, started_at, 
               completed_at, row_count, file_count, error_message, status
        FROM {self.database}.{self.table_name}
        WHERE vendor = %(vendor)s
          AND export_name = %(export_name)s
          AND billing_period = %(billing_period)s
        ORDER BY started_at DESC
        """
        params = {
            "vendor": vendor,
            "export_name": export_name,
            "billing_period": billing_period,
        }
        result = self.client.query(query, parameters=params)
        
        return [
            {
                'version_id': row[0],
                'data_format_version': row[1],
                'current_version': bool(row[2]),
                'load_timestamp': row[3],
                'load_completed': row[4] is not None,
                'row_count': row[5] or 0,
                'file_count': row[6] or 0,
                'error_message': row[7] or ''
            }
            for row in result.result_rows
        ]




# Register the backend
BACKEND_REGISTRY["clickhouse"] = ClickHouseBackend
