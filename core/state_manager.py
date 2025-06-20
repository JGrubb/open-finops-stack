"""Backend-aware state management for cloud billing data loads."""

from typing import Dict, Any, List
from .backends.factory import create_backend
from .backends.base import StateManager


class LoadStateManager:
    """Backend-aware state tracker for billing data loads.
    
    This class provides a high-level interface for state tracking that delegates
    to the appropriate backend implementation based on configuration.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize state manager with backend configuration.
        
        Args:
            config: Configuration dictionary containing database settings
        """
        self.backend = create_backend(config)
        self.state_manager = self.backend.create_state_manager()
    
    def is_version_loaded(self, vendor: str, export_name: str, 
                         billing_period: str, version_id: str) -> bool:
        """Check if a specific version has been successfully loaded."""
        return self.state_manager.is_version_loaded(vendor, export_name, billing_period, version_id)
    
    def start_load(self, vendor: str, export_name: str, billing_period: str,
                   version_id: str, data_format_version: str, file_count: int) -> None:
        """Record the start of a new data load."""
        self.state_manager.start_load(vendor, export_name, billing_period, version_id, 
                                     data_format_version, file_count)
    
    def complete_load(self, vendor: str, export_name: str, billing_period: str,
                     version_id: str, row_count: int) -> None:
        """Mark a load as successfully completed and set it as the current version."""
        self.state_manager.complete_load(vendor, export_name, billing_period, version_id, row_count)
    
    def fail_load(self, vendor: str, export_name: str, billing_period: str,
                  version_id: str, error_message: str) -> None:
        """Mark a load as failed with an error message."""
        self.state_manager.fail_load(vendor, export_name, billing_period, version_id, error_message)
    
    def get_current_versions(self, vendor: str, export_name: str) -> List[Dict[str, Any]]:
        """Get all current versions for a vendor and export."""
        return self.state_manager.get_current_versions(vendor, export_name)
    
    def get_version_history(self, vendor: str, export_name: str, 
                           billing_period: str) -> List[Dict[str, Any]]:
        """Get the version history for a specific billing period."""
        return self.state_manager.get_version_history(vendor, export_name, billing_period)


# For backward compatibility, provide a function that creates the old interface
def LoadStateTracker(db_path: str):
    """Backward compatibility function for existing code.
    
    Creates a LoadStateManager configured for DuckDB with the specified path.
    
    Args:
        db_path: Path to DuckDB database
        
    Returns:
        LoadStateManager configured for DuckDB
    """
    config = {
        "database": {
            "backend": "duckdb",
            "duckdb": {
                "database_path": db_path
            }
        }
    }
    return LoadStateManager(config)