"""Database backend abstraction for Open FinOps Stack.

This module provides database-agnostic interfaces for the Open FinOps Stack,
allowing users to deploy with DuckDB (default), Snowflake, BigQuery, PostgreSQL,
and other analytical databases supported by DLT.
"""

from .base import (
    BackendConfig,
    DatabaseBackend,
    StateManager,
    DataReader,
    DuckDBConfig,
    SnowflakeConfig,
    BigQueryConfig,
    PostgreSQLConfig
)
from .factory import create_backend

__all__ = [
    'BackendConfig',
    'DatabaseBackend', 
    'StateManager',
    'DataReader',
    'DuckDBConfig',
    'SnowflakeConfig',
    'BigQueryConfig',
    'PostgreSQLConfig',
    'create_backend'
]