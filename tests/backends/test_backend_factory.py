"""Tests for backend factory and registry system."""

import pytest
from unittest.mock import patch, Mock

from core.backends.factory import create_backend, list_available_backends, register_backend
from core.backends.base import BACKEND_REGISTRY, DatabaseBackend


class MockBackend(DatabaseBackend):
    """Mock backend for testing."""
    
    def __init__(self, config):
        self.config = config
    
    def get_dlt_destination(self):
        return Mock()
    
    def create_state_manager(self):
        return Mock()
    
    def create_data_reader(self):
        return Mock()
    
    def supports_native_s3(self) -> bool:
        return True
    
    def get_database_path_or_connection(self) -> str:
        return "mock://connection"
    
    def get_table_reference(self, dataset_name: str, table_name: str) -> str:
        return f"mock.{dataset_name}.{table_name}"
    
    @classmethod
    def from_config(cls, config):
        return cls(config)


class TestBackendRegistry:
    """Test backend registration system."""
    
    def test_register_backend(self):
        """Test registering a new backend."""
        # Clean up any existing test backend
        if "test_backend" in BACKEND_REGISTRY:
            del BACKEND_REGISTRY["test_backend"]
        
        register_backend("test_backend", MockBackend)
        
        assert "test_backend" in BACKEND_REGISTRY
        assert BACKEND_REGISTRY["test_backend"] == MockBackend
        
        # Cleanup
        del BACKEND_REGISTRY["test_backend"]
    
    def test_backend_registry_persistence(self):
        """Test that registry maintains state across calls."""
        initial_backends = list(BACKEND_REGISTRY.keys())
        
        register_backend("persistent_test", MockBackend)
        
        assert "persistent_test" in BACKEND_REGISTRY
        assert len(BACKEND_REGISTRY) == len(initial_backends) + 1
        
        # Cleanup
        del BACKEND_REGISTRY["persistent_test"]


class TestCreateBackend:
    """Test backend factory function."""
    
    def setup_method(self):
        """Setup test backend for each test."""
        register_backend("mock_backend", MockBackend)
    
    def teardown_method(self):
        """Cleanup test backend after each test."""
        if "mock_backend" in BACKEND_REGISTRY:
            del BACKEND_REGISTRY["mock_backend"]
    
    def test_create_backend_success(self):
        """Test successful backend creation."""
        config = {
            "database": {
                "backend": "mock_backend"
            }
        }
        
        backend = create_backend(config)
        
        assert isinstance(backend, MockBackend)
        assert backend.config == config
    
    def test_create_backend_default_duckdb(self):
        """Test that duckdb is used as default backend."""
        config = {"database": {}}
        
        with patch('importlib.import_module') as mock_import:
            # Mock successful import of duckdb module
            mock_import.return_value = Mock()
            
            # Temporarily register duckdb for this test
            register_backend("duckdb", MockBackend)
            
            try:
                backend = create_backend(config)
                assert isinstance(backend, MockBackend)
                mock_import.assert_called_with('core.backends.duckdb')
            finally:
                if "duckdb" in BACKEND_REGISTRY:
                    del BACKEND_REGISTRY["duckdb"]
    
    def test_create_backend_unknown_type(self):
        """Test error when unknown backend type is requested."""
        config = {
            "database": {
                "backend": "nonexistent_backend"
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            create_backend(config)
        
        assert "Backend 'nonexistent_backend' not available" in str(exc_info.value)
        assert "Available backends:" in str(exc_info.value)
    
    @patch('importlib.import_module')
    def test_create_backend_auto_import(self, mock_import):
        """Test automatic import of backend module."""
        config = {
            "database": {
                "backend": "auto_import_backend"
            }
        }
        
        # Mock the import to trigger registration
        def mock_import_side_effect(module_name):
            if module_name == 'core.backends.auto_import_backend':
                register_backend("auto_import_backend", MockBackend)
            return Mock()
        
        mock_import.side_effect = mock_import_side_effect
        
        backend = create_backend(config)
        
        assert isinstance(backend, MockBackend)
        mock_import.assert_called_with('core.backends.auto_import_backend')
        
        # Cleanup
        if "auto_import_backend" in BACKEND_REGISTRY:
            del BACKEND_REGISTRY["auto_import_backend"]
    
    @patch('importlib.import_module')
    def test_create_backend_import_failure_ignored(self, mock_import):
        """Test that import failures are handled gracefully."""
        config = {
            "database": {
                "backend": "mock_backend"
            }
        }
        
        # Make import fail
        mock_import.side_effect = ImportError("Module not found")
        
        # Should still work if backend is already registered
        backend = create_backend(config)
        
        assert isinstance(backend, MockBackend)
        mock_import.assert_called_with('core.backends.mock_backend')
    
    def test_create_backend_empty_config(self):
        """Test backend creation with empty config."""
        config = {}
        
        with patch('importlib.import_module') as mock_import:
            register_backend("duckdb", MockBackend)
            
            try:
                backend = create_backend(config)
                assert isinstance(backend, MockBackend)
                mock_import.assert_called_with('core.backends.duckdb')
            finally:
                if "duckdb" in BACKEND_REGISTRY:
                    del BACKEND_REGISTRY["duckdb"]


class TestListAvailableBackends:
    """Test listing available backends."""
    
    def test_list_available_backends_empty_registry(self):
        """Test listing when registry is empty."""
        # Save current registry
        original_registry = BACKEND_REGISTRY.copy()
        BACKEND_REGISTRY.clear()
        
        with patch('importlib.import_module') as mock_import:
            # Make all imports fail
            mock_import.side_effect = ImportError("No modules available")
            
            backends = list_available_backends()
            assert backends == []
        
        # Restore registry
        BACKEND_REGISTRY.update(original_registry)
    
    def test_list_available_backends_with_registered(self):
        """Test listing when backends are already registered."""
        register_backend("test_backend_1", MockBackend)
        register_backend("test_backend_2", MockBackend)
        
        backends = list_available_backends()
        
        assert "test_backend_1" in backends
        assert "test_backend_2" in backends
        
        # Cleanup
        del BACKEND_REGISTRY["test_backend_1"]
        del BACKEND_REGISTRY["test_backend_2"]
    
    @patch('importlib.import_module')
    def test_list_available_backends_auto_discovery(self, mock_import):
        """Test automatic discovery of backends."""
        # Save and clear the registry for this test
        original_registry = BACKEND_REGISTRY.copy()
        BACKEND_REGISTRY.clear()
        
        try:
            def mock_import_side_effect(module_name):
                if module_name == 'core.backends.duckdb':
                    register_backend("duckdb", MockBackend)
                elif module_name == 'core.backends.clickhouse':
                    register_backend("clickhouse", MockBackend)
                elif module_name in ['core.backends.ducklake', 'core.backends.snowflake']:
                    raise ImportError("Module not available")
                return Mock()
            
            mock_import.side_effect = mock_import_side_effect
            
            backends = list_available_backends()
            
            assert "duckdb" in backends
            assert "clickhouse" in backends
            assert "ducklake" not in backends  # Import failed
            assert "snowflake" not in backends  # Import failed
        finally:
            # Restore original registry
            BACKEND_REGISTRY.clear()
            BACKEND_REGISTRY.update(original_registry)
        
        # Verify all known backends were attempted
        expected_calls = [
            'core.backends.duckdb',
            'core.backends.ducklake', 
            'core.backends.snowflake',
            'core.backends.clickhouse'
        ]
        
        actual_calls = [call[0][0] for call in mock_import.call_args_list]
        for expected_call in expected_calls:
            assert expected_call in actual_calls
        
        # Cleanup
        for backend in ["duckdb", "clickhouse"]:
            if backend in BACKEND_REGISTRY:
                del BACKEND_REGISTRY[backend]
    
    def test_list_available_backends_partial_import_failure(self):
        """Test listing when some imports fail."""
        # Register one backend manually
        register_backend("manual_backend", MockBackend)
        
        with patch('importlib.import_module') as mock_import:
            def mock_import_side_effect(module_name):
                if module_name == 'core.backends.duckdb':
                    register_backend("duckdb", MockBackend)
                else:
                    raise ImportError(f"Cannot import {module_name}")
                return Mock()
            
            mock_import.side_effect = mock_import_side_effect
            
            backends = list_available_backends()
            
            assert "manual_backend" in backends
            assert "duckdb" in backends
            # Others should not be present due to import failures
        
        # Cleanup
        for backend in ["manual_backend", "duckdb"]:
            if backend in BACKEND_REGISTRY:
                del BACKEND_REGISTRY[backend]


class TestBackendIntegration:
    """Integration tests for backend system."""
    
    def test_end_to_end_backend_creation(self):
        """Test complete flow from registration to creation."""
        # Register backend
        register_backend("integration_test", MockBackend)
        
        try:
            # Create backend via factory
            config = {
                "database": {
                    "backend": "integration_test",
                    "some_setting": "test_value"
                }
            }
            
            backend = create_backend(config)
            
            # Verify backend was created correctly
            assert isinstance(backend, MockBackend)
            assert backend.config == config
            
            # Test backend interface
            assert backend.supports_native_s3() is True
            assert backend.get_database_path_or_connection() == "mock://connection"
            assert backend.get_table_reference("dataset", "table") == "mock.dataset.table"
            
        finally:
            # Cleanup
            del BACKEND_REGISTRY["integration_test"]
    
    def test_backend_registry_isolation(self):
        """Test that registry operations don't interfere with each other."""
        initial_count = len(BACKEND_REGISTRY)
        
        # Register multiple backends
        register_backend("test_a", MockBackend)
        register_backend("test_b", MockBackend)
        
        assert len(BACKEND_REGISTRY) == initial_count + 2
        
        # Remove one
        del BACKEND_REGISTRY["test_a"]
        
        assert len(BACKEND_REGISTRY) == initial_count + 1
        assert "test_b" in BACKEND_REGISTRY
        assert "test_a" not in BACKEND_REGISTRY
        
        # Cleanup
        del BACKEND_REGISTRY["test_b"]
        
        assert len(BACKEND_REGISTRY) == initial_count