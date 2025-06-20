"""Abstract base classes for database backend abstraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Iterator


# Global registry for backend implementations
BACKEND_REGISTRY = {}


@dataclass
class BackendConfig:
    """Base configuration for database backends."""
    backend_type: str


@dataclass
class DuckDBConfig(BackendConfig):
    """Configuration for DuckDB backend."""
    backend_type: str = "duckdb"
    database_path: str = "./data/finops.duckdb"


@dataclass
class SnowflakeConfig(BackendConfig):
    """Configuration for Snowflake backend."""
    backend_type: str = "snowflake"
    account: str = ""
    warehouse: str = ""
    database: str = ""
    schema: str = ""
    user: str = ""
    password: Optional[str] = None
    private_key_path: Optional[str] = None
    role: Optional[str] = None


@dataclass
class BigQueryConfig(BackendConfig):
    """Configuration for BigQuery backend."""
    backend_type: str = "bigquery"
    project_id: str = ""
    dataset: str = "finops_data"
    location: str = "US"
    credentials_path: Optional[str] = None


@dataclass
class PostgreSQLConfig(BackendConfig):
    """Configuration for PostgreSQL backend."""
    backend_type: str = "postgresql"
    host: str = "localhost"
    port: int = 5432
    database: str = "finops"
    schema: str = "aws_billing"
    user: str = ""
    password: Optional[str] = None


class DatabaseBackend(ABC):
    """Abstract interface for database operations."""
    
    @abstractmethod
    def get_dlt_destination(self) -> Any:
        """Get DLT destination for this backend."""
        pass
    
    @abstractmethod
    def create_state_manager(self) -> 'StateManager':
        """Create state management instance."""
        pass
    
    @abstractmethod
    def create_data_reader(self) -> 'DataReader':
        """Create data reader for S3 files."""
        pass
    
    @abstractmethod
    def supports_native_s3(self) -> bool:
        """Whether backend can read directly from S3."""
        pass
    
    @abstractmethod
    def get_database_path_or_connection(self) -> str:
        """Get database path (for file-based) or connection string."""
        pass
    
    @classmethod
    @abstractmethod
    def from_config(cls, config: Dict[str, Any]) -> 'DatabaseBackend':
        """Create backend instance from configuration dictionary."""
        pass


class StateManager(ABC):
    """Abstract interface for state tracking."""
    
    @abstractmethod
    def is_version_loaded(self, vendor: str, export_name: str, 
                         billing_period: str, version_id: str) -> bool:
        """Check if a specific version has been successfully loaded."""
        pass
    
    @abstractmethod
    def start_load(self, vendor: str, export_name: str, 
                  billing_period: str, version_id: str, 
                  data_format_version: str, file_count: int) -> None:
        """Record the start of a new data load."""
        pass
    
    @abstractmethod
    def complete_load(self, vendor: str, export_name: str,
                     billing_period: str, version_id: str, row_count: int) -> None:
        """Mark a load as successfully completed and set it as the current version."""
        pass
    
    @abstractmethod
    def fail_load(self, vendor: str, export_name: str, billing_period: str,
                  version_id: str, error_message: str) -> None:
        """Mark a load as failed with an error message."""
        pass
    
    @abstractmethod
    def get_current_versions(self, vendor: str, export_name: str) -> List[Dict[str, Any]]:
        """Get all current versions for a vendor and export."""
        pass
    
    @abstractmethod
    def get_version_history(self, vendor: str, export_name: str, 
                           billing_period: str) -> List[Dict[str, Any]]:
        """Get the version history for a specific billing period."""
        pass


class DataReader(ABC):
    """Abstract interface for reading data files."""
    
    @abstractmethod
    def read_csv_file(self, bucket: str, key: str, aws_creds: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """Read CSV file from S3 and yield records."""
        pass
    
    @abstractmethod
    def read_parquet_file(self, bucket: str, key: str, aws_creds: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """Read Parquet file from S3 and yield records."""
        pass