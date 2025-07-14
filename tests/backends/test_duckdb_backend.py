"""Tests for DuckDB backend implementation."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from core.backends.duckdb import DuckDBBackend, DuckDBStateManager, DuckDBDataReader
from core.backends.base import DuckDBConfig


class TestDuckDBConfig:
    """Test DuckDB configuration."""
    
    def test_default_config(self):
        """Test default DuckDB configuration values."""
        config = DuckDBConfig()
        
        assert config.backend_type == "duckdb"
        assert config.database_path == "./data/finops.duckdb"
    
    def test_custom_config(self):
        """Test custom DuckDB configuration."""
        config = DuckDBConfig(database_path="/custom/path/test.duckdb")
        
        assert config.database_path == "/custom/path/test.duckdb"


class TestDuckDBBackend:
    """Test DuckDB backend implementation."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        # Create a temporary file path but don't create the file
        # Let DuckDB create the database file itself
        tmp_dir = tempfile.mkdtemp()
        db_path = os.path.join(tmp_dir, 'test.duckdb')
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        if os.path.exists(tmp_dir):
            os.rmdir(tmp_dir)
    
    @pytest.fixture
    def config(self, temp_db_path):
        """Create test DuckDB config."""
        return DuckDBConfig(database_path=temp_db_path)
    
    def test_backend_initialization(self, config):
        """Test DuckDB backend initialization."""
        backend = DuckDBBackend(config)
        
        assert backend.config == config
        # Check that database directory was created
        assert Path(config.database_path).parent.exists()
    
    def test_backend_initialization_creates_directory(self):
        """Test that backend creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "subdir", "test.duckdb")
            config = DuckDBConfig(database_path=db_path)
            
            backend = DuckDBBackend(config)
            
            assert Path(db_path).parent.exists()
    
    @patch('core.backends.duckdb.dlt.destinations.duckdb')
    def test_get_dlt_destination(self, mock_dlt_duckdb, config):
        """Test DLT destination creation."""
        mock_destination = Mock()
        mock_dlt_duckdb.return_value = mock_destination
        
        backend = DuckDBBackend(config)
        destination = backend.get_dlt_destination()
        
        assert destination == mock_destination
        mock_dlt_duckdb.assert_called_once_with(config.database_path)
    
    def test_create_state_manager(self, config):
        """Test state manager creation."""
        backend = DuckDBBackend(config)
        state_manager = backend.create_state_manager()
        
        assert isinstance(state_manager, DuckDBStateManager)
        assert state_manager.db_path == config.database_path
    
    def test_create_data_reader(self, config):
        """Test data reader creation."""
        backend = DuckDBBackend(config)
        data_reader = backend.create_data_reader()
        
        assert isinstance(data_reader, DuckDBDataReader)
        assert data_reader.config == config
    
    def test_supports_native_s3(self, config):
        """Test S3 support flag."""
        backend = DuckDBBackend(config)
        
        assert backend.supports_native_s3() is True
    
    def test_get_database_path_or_connection(self, config):
        """Test database path retrieval."""
        backend = DuckDBBackend(config)
        path = backend.get_database_path_or_connection()
        
        assert path == config.database_path
    
    def test_get_table_reference(self, config):
        """Test table reference generation."""
        backend = DuckDBBackend(config)
        table_ref = backend.get_table_reference("aws_billing", "billing_2024_01")
        
        expected = "aws_billing.billing_2024_01"
        assert table_ref == expected
    
    def test_from_config(self, temp_db_path):
        """Test backend creation from config dictionary."""
        config_dict = {
            "database": {
                "duckdb": {
                    "database_path": temp_db_path
                }
            }
        }
        
        backend = DuckDBBackend.from_config(config_dict)
        
        assert backend.config.database_path == temp_db_path
    
    def test_from_config_defaults(self):
        """Test backend creation with default values."""
        config_dict = {"database": {"duckdb": {}}}
        
        backend = DuckDBBackend.from_config(config_dict)
        
        assert backend.config.database_path == "./data/finops.duckdb"


class TestDuckDBStateManager:
    """Test DuckDB state manager implementation."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        # Create a temporary file path but don't create the file
        # Let DuckDB create the database file itself
        tmp_dir = tempfile.mkdtemp()
        db_path = os.path.join(tmp_dir, 'test.duckdb')
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        if os.path.exists(tmp_dir):
            os.rmdir(tmp_dir)
    
    @pytest.fixture
    def state_manager(self, temp_db_path):
        """Create DuckDB state manager."""
        return DuckDBStateManager(temp_db_path)
    
    def test_initialization(self, temp_db_path):
        """Test state manager initialization."""
        state_manager = DuckDBStateManager(temp_db_path)
        
        assert state_manager.db_path == temp_db_path
        
        # Verify state table was created by connecting and checking
        import duckdb
        conn = duckdb.connect(temp_db_path)
        try:
            # Use DuckDB's information schema to check for tables
            tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_name = 'load_state'").fetchall()
            table_names = [table[0] for table in tables]
            assert 'load_state' in table_names
        finally:
            conn.close()
    
    def test_is_version_loaded_false(self, state_manager):
        """Test version check when version is not loaded."""
        result = state_manager.is_version_loaded("aws", "test-export", "2024-01", "v123")
        assert result is False
    
    def test_start_and_complete_load_cycle(self, state_manager):
        """Test complete load lifecycle."""
        # Start load
        state_manager.start_load("aws", "test-export", "2024-01", "v123", "v2", 5)
        
        # Check that it's not completed yet
        assert not state_manager.is_version_loaded("aws", "test-export", "2024-01", "v123")
        
        # Complete load
        state_manager.complete_load("aws", "test-export", "2024-01", "v123", 1000)
        
        # Now it should be loaded
        assert state_manager.is_version_loaded("aws", "test-export", "2024-01", "v123")
    
    def test_start_load_duplicate(self, state_manager):
        """Test starting load multiple times (should handle ON CONFLICT)."""
        # Start load twice
        state_manager.start_load("aws", "test-export", "2024-01", "v123", "v2", 5)
        state_manager.start_load("aws", "test-export", "2024-01", "v123", "v2", 6)  # Different file count
        
        # Should not raise error due to ON CONFLICT handling
        assert True  # If we get here, no exception was raised
    
    def test_fail_load(self, state_manager):
        """Test marking a load as failed."""
        # Start load
        state_manager.start_load("aws", "test-export", "2024-01", "v123", "v2", 5)
        
        # Fail load
        state_manager.fail_load("aws", "test-export", "2024-01", "v123", "Connection timeout")
        
        # Should still not be loaded
        assert not state_manager.is_version_loaded("aws", "test-export", "2024-01", "v123")
    
    def test_get_current_versions(self, state_manager):
        """Test getting current versions."""
        # Add some test data
        state_manager.start_load("aws", "test-export", "2024-01", "v123", "v2", 5)
        state_manager.complete_load("aws", "test-export", "2024-01", "v123", 1000)
        
        state_manager.start_load("aws", "test-export", "2024-02", "v124", "v2", 6)
        state_manager.complete_load("aws", "test-export", "2024-02", "v124", 1500)
        
        versions = state_manager.get_current_versions("aws", "test-export")
        
        assert len(versions) == 2
        # Should be ordered by billing_period DESC
        assert versions[0]['billing_period'] == "2024-02"
        assert versions[0]['version_id'] == "v124"
        assert versions[0]['row_count'] == 1500
        assert versions[1]['billing_period'] == "2024-01"
        assert versions[1]['version_id'] == "v123"
        assert versions[1]['row_count'] == 1000
    
    def test_get_version_history(self, state_manager):
        """Test getting version history."""
        # Create version history for same billing period
        state_manager.start_load("aws", "test-export", "2024-01", "v123", "v2", 5)
        state_manager.complete_load("aws", "test-export", "2024-01", "v123", 1000)
        
        state_manager.start_load("aws", "test-export", "2024-01", "v124", "v2", 6)
        state_manager.complete_load("aws", "test-export", "2024-01", "v124", 1200)
        
        history = state_manager.get_version_history("aws", "test-export", "2024-01")
        
        assert len(history) == 2
        # Should be ordered by load_timestamp DESC (most recent first)
        assert history[0]['version_id'] == "v124"
        assert history[0]['current_version'] is True  # Most recent should be current
        assert history[0]['load_completed'] is True
        assert history[1]['version_id'] == "v123"
        assert history[1]['current_version'] is False  # Previous should not be current
    
    def test_current_version_tracking(self, state_manager):
        """Test that only one version is marked as current per billing period."""
        # Load first version
        state_manager.start_load("aws", "test-export", "2024-01", "v123", "v2", 5)
        state_manager.complete_load("aws", "test-export", "2024-01", "v123", 1000)
        
        # Load second version (should become current, first should become non-current)
        state_manager.start_load("aws", "test-export", "2024-01", "v124", "v2", 6)
        state_manager.complete_load("aws", "test-export", "2024-01", "v124", 1200)
        
        history = state_manager.get_version_history("aws", "test-export", "2024-01")
        
        # Only one should be current
        current_versions = [h for h in history if h['current_version']]
        assert len(current_versions) == 1
        assert current_versions[0]['version_id'] == "v124"


class TestDuckDBDataReader:
    """Test DuckDB data reader implementation."""
    
    @pytest.fixture
    def config(self):
        """Create test config."""
        return DuckDBConfig(database_path="/tmp/test.duckdb")
    
    @pytest.fixture
    def data_reader(self, config):
        """Create DuckDB data reader."""
        return DuckDBDataReader(config)
    
    @pytest.fixture
    def mock_aws_creds(self):
        """Create mock AWS credentials."""
        return {
            'aws_access_key_id': 'test_key',
            'aws_secret_access_key': 'test_secret',
            'region_name': 'us-east-1'
        }
    
    @patch('core.backends.duckdb.duckdb.connect')
    @patch('core.backends.duckdb.S3Utils.setup_duckdb_s3_credentials')
    @patch('core.backends.duckdb.S3Utils.build_s3_path')
    @patch('core.backends.duckdb.S3Utils.clean_column_names')
    def test_read_csv_file(self, mock_clean_columns, mock_build_path, mock_setup_creds, 
                          mock_connect, data_reader, mock_aws_creds):
        """Test reading CSV file from S3."""
        # Setup mocks
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        mock_build_path.return_value = "s3://bucket/path/file.csv"
        mock_clean_columns.side_effect = lambda x: x  # Return as-is
        
        # Mock query result
        mock_conn.execute.return_value.fetchall.return_value = [
            ("2024-01-01", "service1", "100.50"),
            ("2024-01-02", "service2", "200.75")
        ]
        mock_conn.description = [("date", None), ("service", None), ("cost", None)]
        
        # Execute
        records = list(data_reader.read_csv_file("test-bucket", "path/file.csv", mock_aws_creds))
        
        # Verify
        assert len(records) == 2
        assert records[0] == {"date": "2024-01-01", "service": "service1", "cost": "100.50"}
        assert records[1] == {"date": "2024-01-02", "service": "service2", "cost": "200.75"}
        
        # Verify S3 setup was called
        mock_setup_creds.assert_called_once_with(mock_conn, mock_aws_creds)
        mock_build_path.assert_called_once_with("test-bucket", "path/file.csv")
        mock_conn.close.assert_called_once()
    
    @patch('core.backends.duckdb.duckdb.connect')
    @patch('core.backends.duckdb.S3Utils.setup_duckdb_s3_credentials')
    @patch('core.backends.duckdb.S3Utils.build_s3_path')
    def test_read_csv_file_gzipped(self, mock_build_path, mock_setup_creds, 
                                  mock_connect, data_reader, mock_aws_creds):
        """Test reading gzipped CSV file."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        mock_build_path.return_value = "s3://bucket/path/file.csv.gz"
        
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_conn.description = []
        
        # Execute
        list(data_reader.read_csv_file("test-bucket", "path/file.csv.gz", mock_aws_creds))
        
        # Verify gzip compression parameter was used
        execute_call = mock_conn.execute.call_args[0][0]
        assert "compression='gzip'" in execute_call
    
    @patch('core.backends.duckdb.duckdb.connect')
    @patch('core.backends.duckdb.S3Utils.setup_duckdb_s3_credentials')
    @patch('core.backends.duckdb.S3Utils.build_s3_path')
    @patch('core.backends.duckdb.S3Utils.clean_column_names')
    def test_read_parquet_file(self, mock_clean_columns, mock_build_path, mock_setup_creds,
                              mock_connect, data_reader, mock_aws_creds):
        """Test reading Parquet file from S3."""
        # Setup mocks
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        mock_build_path.return_value = "s3://bucket/path/file.parquet"
        mock_clean_columns.side_effect = lambda x: x
        
        # Mock query result
        mock_conn.execute.return_value.fetchall.return_value = [
            ("2024-01-01", "service1", 100.50),
            ("2024-01-02", "service2", 200.75)
        ]
        mock_conn.description = [("date", None), ("service", None), ("cost", None)]
        
        # Execute
        records = list(data_reader.read_parquet_file("test-bucket", "path/file.parquet", mock_aws_creds))
        
        # Verify
        assert len(records) == 2
        assert records[0] == {"date": "2024-01-01", "service": "service1", "cost": 100.50}
        
        # Verify parquet query was used
        execute_call = mock_conn.execute.call_args[0][0]
        assert "read_parquet" in execute_call
        mock_conn.close.assert_called_once()
    
    @patch('core.backends.duckdb.S3Utils.setup_duckdb_s3_credentials')
    @patch('core.backends.duckdb.S3Utils.build_s3_path')
    @patch('core.backends.duckdb.duckdb.connect')
    def test_connection_cleanup_on_error(self, mock_connect, mock_build_path, mock_setup_creds, data_reader, mock_aws_creds):
        """Test that connection is properly closed even when error occurs."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        mock_build_path.return_value = 's3://bucket/key'
        mock_conn.execute.side_effect = Exception("Query failed")
        
        with pytest.raises(Exception):
            list(data_reader.read_csv_file("bucket", "key", mock_aws_creds))
        
        # Connection should still be closed
        mock_conn.close.assert_called_once()


class TestDuckDBBackendRegistry:
    """Test DuckDB backend registration."""
    
    def test_backend_registered(self, clean_backend_registry):
        """Test that DuckDB backend is registered."""
        from core.backends.duckdb import DuckDBBackend
        from core.backends.factory import register_backend
        
        # Register the backend (simulating import-time registration)
        register_backend("duckdb", DuckDBBackend)
        
        # Verify registration
        assert "duckdb" in clean_backend_registry
        assert clean_backend_registry["duckdb"] == DuckDBBackend