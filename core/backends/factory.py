"""Factory for creating database backend instances using registry pattern."""

import importlib
from typing import Dict, Any

from .base import DatabaseBackend, BACKEND_REGISTRY


def register_backend(name: str, backend_class):
    """Register a backend implementation.
    
    Args:
        name: Backend type name (e.g., 'duckdb', 'snowflake')
        backend_class: Backend class that implements DatabaseBackend
    """
    BACKEND_REGISTRY[name] = backend_class


def _try_import_backend(backend_type: str) -> None:
    """Try to import a backend module to trigger registration."""
    try:
        importlib.import_module(f'core.backends.{backend_type}')
    except ImportError:
        # Backend module doesn't exist or has missing dependencies
        pass


def get_backend_class(backend_type: str):
    """Get a backend class from the registry.
    
    Args:
        backend_type: Backend type name (e.g., 'duckdb', 'clickhouse')
        
    Returns:
        Backend class that implements DatabaseBackend
        
    Raises:
        ValueError: If backend type is not registered
    """
    _try_import_backend(backend_type)
    
    if backend_type not in BACKEND_REGISTRY:
        available_backends = list(BACKEND_REGISTRY.keys())
        raise ValueError(f"Backend '{backend_type}' not available. Available backends: {available_backends}")
    
    return BACKEND_REGISTRY[backend_type]


def create_backend(config: Dict[str, Any]) -> DatabaseBackend:
    """Factory function to create appropriate backend using registry pattern.
    
    Args:
        config: Configuration dictionary with database settings
        
    Returns:
        DatabaseBackend instance for the specified backend type
        
    Raises:
        ValueError: If backend type is not supported or available
    """
    database_config = config.get("database", {})
    backend_type = database_config.get("backend", "duckdb")
    
    # Get the backend class (imports if needed)
    backend_class = get_backend_class(backend_type)
    return backend_class.from_config(config)


def list_available_backends() -> list:
    """List all available backend types.
    
    This function attempts to import all known backend modules to populate
    the registry, then returns the list of available backends.
    """
    # Try to import known backends
    known_backends = ["duckdb", "ducklake", "snowflake", "clickhouse"]
    
    for backend_type in known_backends:
        _try_import_backend(backend_type)
    
    return list(BACKEND_REGISTRY.keys())
