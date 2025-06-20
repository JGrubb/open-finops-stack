# Database Backend Abstraction Architecture

## Overview

This document outlines the architecture for supporting multiple database backends in the Open FinOps Stack, extending beyond DuckDB to support enterprise data warehouses like Snowflake, BigQuery, PostgreSQL, and others.

## Current State Analysis

### Well-Abstracted Components ✅
- **DLT Pipeline**: Already uses `dlt.destinations.*` for backend switching
- **Data Loading**: DLT handles schema creation, type mapping, and write dispositions
- **Configuration Management**: TOML-based config is easily extensible

### Tightly Coupled Components ❌
- **State Management**: Direct DuckDB connections in `core/state.py`
- **S3 Direct Reading**: Uses DuckDB's native `httpfs` extension
- **SQL Operations**: Some DuckDB-specific queries and functions

## Proposed Architecture

### 1. Backend Interface Design

```python
# core/backends/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class BackendConfig:
    """Base configuration for database backends."""
    backend_type: str
    dataset_name: str = "aws_billing"

@dataclass 
class DuckDBConfig(BackendConfig):
    backend_type: str = "duckdb"
    database_path: str = "./data/finops.duckdb"

@dataclass
class SnowflakeConfig(BackendConfig):
    backend_type: str = "snowflake"
    account: str
    warehouse: str
    database: str
    schema: str
    user: str
    password: Optional[str] = None
    private_key_path: Optional[str] = None
    role: Optional[str] = None

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

class StateManager(ABC):
    """Abstract interface for state tracking."""
    
    @abstractmethod
    def is_version_loaded(self, vendor: str, export_name: str, 
                         billing_period: str, version_id: str) -> bool:
        pass
    
    @abstractmethod
    def start_load(self, vendor: str, export_name: str, 
                  billing_period: str, version_id: str, **kwargs) -> None:
        pass
    
    @abstractmethod
    def complete_load(self, vendor: str, export_name: str,
                     billing_period: str, version_id: str, **kwargs) -> None:
        pass

class DataReader(ABC):
    """Abstract interface for reading data files."""
    
    @abstractmethod
    def read_csv_file(self, bucket: str, key: str, aws_creds: Dict) -> Iterator[Dict]:
        pass
    
    @abstractmethod
    def read_parquet_file(self, bucket: str, key: str, aws_creds: Dict) -> Iterator[Dict]:
        pass
```

### 2. Backend Implementations

#### DuckDB Backend (Default)
```python
# core/backends/duckdb.py
class DuckDBBackend(DatabaseBackend):
    def __init__(self, config: DuckDBConfig):
        self.config = config
    
    def get_dlt_destination(self):
        return dlt.destinations.duckdb(self.config.database_path)
    
    def supports_native_s3(self) -> bool:
        return True  # DuckDB has excellent S3 support
    
    def create_data_reader(self) -> 'DuckDBDataReader':
        return DuckDBDataReader(self.config)

class DuckDBStateManager(StateManager):
    """Current state management implementation."""
    # Move existing code from core/state.py here

class DuckDBDataReader(DataReader):
    """DuckDB's native S3 reading capabilities."""
    # Move existing S3 reading code here
```

#### Snowflake Backend
```python
# core/backends/snowflake.py
class SnowflakeBackend(DatabaseBackend):
    def __init__(self, config: SnowflakeConfig):
        self.config = config
    
    def get_dlt_destination(self):
        return dlt.destinations.snowflake(
            credentials={
                "account": self.config.account,
                "user": self.config.user,
                "password": self.config.password,
                "warehouse": self.config.warehouse,
                "database": self.config.database,
                "schema": self.config.schema,
                "role": self.config.role
            }
        )
    
    def supports_native_s3(self) -> bool:
        return True  # Snowflake has External Stages
    
    def create_data_reader(self) -> 'SnowflakeDataReader':
        return SnowflakeDataReader(self.config)

class SnowflakeStateManager(StateManager):
    """State management using Snowflake tables."""
    # Implement using Snowflake SQL

class SnowflakeDataReader(DataReader):
    """Use Snowflake External Stages or boto3 fallback."""
    # Implement Snowflake-specific S3 reading
```

### 3. Configuration Schema

```toml
# config.toml
[project]
name = "open-finops-stack"

# Database backend configuration
[database]
backend = "duckdb"  # or "snowflake", "bigquery", "postgresql"

# DuckDB-specific config
[database.duckdb]
database_path = "./data/finops.duckdb"

# Snowflake-specific config
[database.snowflake]
account = "your-account.snowflakecomputing.com"
warehouse = "FINOPS_WH"
database = "FINOPS_DB"
schema = "AWS_BILLING"
user = "finops_user"
# password via environment variable: SNOWFLAKE_PASSWORD
role = "FINOPS_ROLE"

# AWS configuration (unchanged)
[aws]
bucket = "your-cur-bucket"
prefix = "your-prefix"
export_name = "your-export-name"
```

### 4. Backend Factory

```python
# core/backends/factory.py
def create_backend(config: Dict[str, Any]) -> DatabaseBackend:
    """Factory function to create appropriate backend."""
    backend_type = config.get("database", {}).get("backend", "duckdb")
    
    if backend_type == "duckdb":
        db_config = DuckDBConfig(**config.get("database", {}).get("duckdb", {}))
        return DuckDBBackend(db_config)
    
    elif backend_type == "snowflake":
        sf_config = SnowflakeConfig(**config.get("database", {}).get("snowflake", {}))
        # Override with environment variables for sensitive data
        sf_config.password = os.getenv("SNOWFLAKE_PASSWORD", sf_config.password)
        return SnowflakeBackend(sf_config)
    
    else:
        raise ValueError(f"Unsupported backend: {backend_type}")
```

## Implementation Strategy

### Phase 1: Foundation (High Priority)
1. **Create Backend Interfaces** - Define abstract base classes
2. **Refactor State Management** - Extract from direct DuckDB usage
3. **Update Configuration** - Extend config schema for multiple backends
4. **Backend Factory** - Central point for backend creation

### Phase 2: Backend Implementations (Medium Priority)  
1. **DuckDB Backend** - Migrate existing functionality
2. **Snowflake Backend** - Full Snowflake support
3. **Data Reader Abstraction** - Handle S3 reading strategies
4. **Pipeline Integration** - Update AWS pipeline to use new abstraction

### Phase 3: Advanced Features (Low Priority)
1. **Additional Backends** - BigQuery, PostgreSQL support
2. **Performance Optimization** - Backend-specific optimizations
3. **Advanced SQL Features** - Views, indexes, clustering

## S3 Reading Strategy

### Native Capabilities
- **DuckDB**: Direct S3 reading via `httpfs` extension (fastest)
- **Snowflake**: External Stages with S3 integration
- **BigQuery**: External Tables with Cloud Storage

### Fallback Strategy
For backends without native S3 support:
```python
class Boto3DataReader(DataReader):
    """Fallback using boto3 + pandas/pyarrow."""
    
    def read_parquet_file(self, bucket: str, key: str, aws_creds: Dict):
        # Download via boto3, read with pyarrow, yield records
        s3_client = boto3.client('s3', **aws_creds)
        response = s3_client.get_object(Bucket=bucket, Key=key)
        df = pd.read_parquet(io.BytesIO(response['Body'].read()))
        for _, row in df.iterrows():
            yield row.to_dict()
```

## Migration Path

### Backward Compatibility
- Default to DuckDB backend for existing configurations
- Existing `./data/finops.duckdb` files continue to work
- No breaking changes to CLI interface

### New Features
- `--backend` CLI flag to override config
- `finops aws import-cur --backend snowflake`
- Environment variable support: `OPEN_FINOPS_DATABASE_BACKEND=snowflake`

## Benefits

### For Users
- **Enterprise Integration**: Use existing data warehouse infrastructure
- **Scale**: Handle larger datasets with warehouse compute
- **Governance**: Leverage existing security and access controls
- **Cost Optimization**: Use warehouse-specific features (clustering, partitioning)

### For Development
- **Clean Architecture**: Well-defined interfaces and separation of concerns
- **Extensibility**: Easy to add new backends
- **Testability**: Each backend can be tested independently
- **Maintainability**: Backend-specific code is isolated

## Example Usage

```bash
# Use DuckDB (default)
./finops aws import-cur

# Use Snowflake
./finops aws import-cur --backend snowflake

# Use different config file
./finops aws import-cur --config snowflake-config.toml
```

## Next Steps

1. Start with Phase 1 foundation work
2. Implement DuckDB backend first (migrate existing code)
3. Add Snowflake backend as proof of concept
4. Extend to other backends based on user demand

This architecture provides a clean foundation for multi-backend support while maintaining the current DuckDB functionality and user experience.