"""Tests for ClickHouse backend implementation."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any

from core.backends.clickhouse import ClickHouseBackend, ClickHouseStateManager
from core.backends.base import ClickHouseConfig


class TestClickHouseConfig:
    """Test ClickHouse configuration."""
    
    def test_default_config(self):
        """Test default ClickHouse configuration values."""
        config = ClickHouseConfig()
        
        assert config.backend_type == "clickhouse"
        assert config.host == "localhost"
        assert config.port == 9000
        assert config.http_port == 8123
        assert config.database == "finops"
        assert config.user == "default"
        assert config.password == ""
        assert config.secure is False
    
    def test_custom_config(self):
        """Test custom ClickHouse configuration."""
        config = ClickHouseConfig(
            host="clickhouse.example.com",
            port=9001,
            http_port=8124,
            database="test_db",
            user="test_user",
            password="test_pass",
            secure=True
        )
        
        assert config.host == "clickhouse.example.com"
        assert config.port == 9001
        assert config.http_port == 8124
        assert config.database == "test_db"
        assert config.user == "test_user"
        assert config.password == "test_pass"
        assert config.secure is True


class TestClickHouseBackend:
    """Test ClickHouse backend implementation."""
    
    @pytest.fixture
    def config(self):
        """Create test ClickHouse config."""
        return ClickHouseConfig(
            host="localhost",
            port=9000,
            http_port=8123,
            database="test_finops",
            user="test_user",
            password="test_pass"
        )
    
    @pytest.fixture
    def mock_client(self):
        """Create mock ClickHouse client."""
        return Mock()
    
    @patch('core.backends.clickhouse.clickhouse_connect.get_client')
    def test_backend_initialization(self, mock_get_client, config, mock_client):
        """Test ClickHouse backend initialization."""
        mock_get_client.return_value = mock_client
        
        backend = ClickHouseBackend(config)
        
        assert backend.config == config
        mock_get_client.assert_called_once_with(
            host="localhost",
            port=8123,  # Should use HTTP port
            user="test_user",
            password="test_pass",
            database="test_finops",
            secure=False
        )
    
    @patch('core.backends.clickhouse.clickhouse_connect.get_client')
    @patch('core.backends.clickhouse.dlt.destinations.clickhouse')
    def test_get_dlt_destination(self, mock_dlt_ch, mock_get_client, config):
        """Test DLT destination creation."""
        mock_destination = Mock()
        mock_dlt_ch.return_value = mock_destination
        
        backend = ClickHouseBackend(config)
        destination = backend.get_dlt_destination()
        
        assert destination == mock_destination
        mock_dlt_ch.assert_called_once()
        
        # Check that credentials were passed correctly
        call_args = mock_dlt_ch.call_args
        assert call_args[1]['database_name'] == "test_finops"
        assert call_args[1]['credentials']['secure'] is False
    
    @patch('core.backends.clickhouse.clickhouse_connect.get_client')
    def test_create_state_manager(self, mock_get_client, config, mock_client):
        """Test state manager creation."""
        mock_get_client.return_value = mock_client
        
        backend = ClickHouseBackend(config)
        state_manager = backend.create_state_manager()
        
        assert isinstance(state_manager, ClickHouseStateManager)
        assert state_manager.client == mock_client
        assert state_manager.database == "test_finops"
    
    @patch('core.backends.clickhouse.clickhouse_connect.get_client')
    def test_create_data_reader(self, mock_get_client, config):
        """Test data reader creation (should return None)."""
        backend = ClickHouseBackend(config)
        data_reader = backend.create_data_reader()
        
        assert data_reader is None
    
    @patch('core.backends.clickhouse.clickhouse_connect.get_client')
    def test_supports_native_s3(self, mock_get_client, config):
        """Test S3 support flag."""
        backend = ClickHouseBackend(config)
        
        assert backend.supports_native_s3() is True
    
    @patch('core.backends.clickhouse.clickhouse_connect.get_client')
    def test_get_database_path_or_connection(self, mock_get_client, config):
        """Test connection string generation."""
        backend = ClickHouseBackend(config)
        connection = backend.get_database_path_or_connection()
        
        expected = "clickhouse://test_user@localhost:9000/test_finops"
        assert connection == expected
    
    @patch('core.backends.clickhouse.clickhouse_connect.get_client')
    def test_get_table_reference(self, mock_get_client, config):
        """Test table reference generation."""
        backend = ClickHouseBackend(config)
        table_ref = backend.get_table_reference("aws_billing", "billing_2024_01")
        
        expected = "test_finops.aws_billing___billing_2024_01"
        assert table_ref == expected
    
    @patch('core.backends.clickhouse.clickhouse_connect.get_client')
    def test_from_config(self, mock_get_client):
        """Test backend creation from config dictionary."""
        config_dict = {
            "database": {
                "clickhouse": {
                    "host": "remote-ch.example.com",
                    "port": 9001,
                    "http_port": 8124,
                    "database": "custom_db",
                    "user": "custom_user",
                    "password": "custom_pass",
                    "secure": True
                }
            }
        }
        
        backend = ClickHouseBackend.from_config(config_dict)
        
        assert backend.config.host == "remote-ch.example.com"
        assert backend.config.port == 9001
        assert backend.config.http_port == 8124
        assert backend.config.database == "custom_db"
        assert backend.config.user == "custom_user"
        assert backend.config.password == "custom_pass"
        assert backend.config.secure is True
    
    @patch('core.backends.clickhouse.clickhouse_connect.get_client')
    def test_from_config_defaults(self, mock_get_client):
        """Test backend creation with default values."""
        config_dict = {"database": {"clickhouse": {}}}
        
        backend = ClickHouseBackend.from_config(config_dict)
        
        assert backend.config.host == "localhost"
        assert backend.config.port == 9000
        assert backend.config.http_port == 8123
        assert backend.config.database == "finops"
        assert backend.config.user == "default"
        assert backend.config.password == ""
        assert backend.config.secure is False


class TestClickHouseStateManager:
    """Test ClickHouse state manager implementation."""
    
    @pytest.fixture
    def mock_client(self):
        """Create mock ClickHouse client."""
        client = Mock()
        client.command = Mock()
        client.query = Mock()
        return client
    
    @pytest.fixture
    def state_manager(self, mock_client):
        """Create ClickHouse state manager with mock client."""
        return ClickHouseStateManager(mock_client, "test_db")
    
    def test_initialization(self, mock_client):
        """Test state manager initialization."""
        state_manager = ClickHouseStateManager(mock_client, "test_db")
        
        assert state_manager.client == mock_client
        assert state_manager.database == "test_db"
        assert state_manager.table_name == "load_state"
        
        # Verify state table creation was called
        mock_client.command.assert_called_once()
        create_table_call = mock_client.command.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS test_db.load_state" in create_table_call
        assert "ENGINE = MergeTree()" in create_table_call
    
    def test_is_version_loaded_true(self, state_manager, mock_client):
        """Test version check when version is loaded."""
        mock_result = Mock()
        mock_result.result_rows = [[1]]
        mock_client.query.return_value = mock_result
        
        result = state_manager.is_version_loaded("aws", "test-export", "2024-01", "v123")
        
        assert result is True
        mock_client.query.assert_called_once()
        query_call = mock_client.query.call_args[0][0]
        assert "SELECT count() FROM test_db.load_state" in query_call
        assert "status = 'completed'" in query_call
    
    def test_is_version_loaded_false(self, state_manager, mock_client):
        """Test version check when version is not loaded."""
        mock_result = Mock()
        mock_result.result_rows = [[0]]
        mock_client.query.return_value = mock_result
        
        result = state_manager.is_version_loaded("aws", "test-export", "2024-01", "v123")
        
        assert result is False
    
    def test_start_load(self, state_manager, mock_client):
        """Test starting a data load."""
        state_manager.start_load("aws", "test-export", "2024-01", "v123", "v2", 5)
        
        mock_client.command.assert_called()
        # Skip the table creation call, get the start_load call
        insert_call = mock_client.command.call_args_list[-1][0][0]
        assert "INSERT INTO test_db.load_state" in insert_call
        assert "status" in insert_call
        
        # Check parameters
        params = mock_client.command.call_args_list[-1][1]['parameters']
        assert params['vendor'] == "aws"
        assert params['export_name'] == "test-export"
        assert params['billing_period'] == "2024-01"
        assert params['version_id'] == "v123"
        assert params['data_format_version'] == "v2"
        assert params['file_count'] == 5
    
    def test_complete_load(self, state_manager, mock_client):
        """Test completing a data load."""
        state_manager.complete_load("aws", "test-export", "2024-01", "v123", 1000)
        
        # Should have multiple command calls (update previous + update current)
        assert mock_client.command.call_count >= 2
        
        # Check that both UPDATE commands were called
        calls = [call[0][0] for call in mock_client.command.call_args_list[1:]]  # Skip table creation
        
        # First call should update previous versions
        assert any("UPDATE is_current = 0" in call for call in calls)
        # Second call should mark current as completed
        assert any("status = 'completed'" in call and "is_current = 1" in call for call in calls)
    
    def test_complete_load_with_error(self, state_manager, mock_client):
        """Test complete_load error handling."""
        mock_client.command.side_effect = [None, Exception("Database error")]  # Table creation succeeds, update fails
        
        with pytest.raises(RuntimeError) as exc_info:
            state_manager.complete_load("aws", "test-export", "2024-01", "v123", 1000)
        
        assert "Failed to complete load for aws/test-export/2024-01" in str(exc_info.value)
    
    def test_fail_load(self, state_manager, mock_client):
        """Test marking a load as failed."""
        state_manager.fail_load("aws", "test-export", "2024-01", "v123", "Connection timeout")
        
        mock_client.command.assert_called()
        # Get the fail_load call (skip table creation)
        fail_call = mock_client.command.call_args_list[-1][0][0]
        assert "ALTER TABLE test_db.load_state" in fail_call
        assert "status = 'failed'" in fail_call
        
        # Check parameters
        params = mock_client.command.call_args_list[-1][1]['parameters']
        assert params['error_message'] == "Connection timeout"
    
    def test_get_current_versions(self, state_manager, mock_client):
        """Test getting current versions."""
        mock_result = Mock()
        mock_result.result_rows = [
            ("2024-01", "v123", "v2", datetime(2024, 1, 15), 1000, 5),
            ("2024-02", "v124", "v2", datetime(2024, 2, 15), 1500, 6)
        ]
        mock_client.query.return_value = mock_result
        
        versions = state_manager.get_current_versions("aws", "test-export")
        
        assert len(versions) == 2
        assert versions[0]['billing_period'] == "2024-01"
        assert versions[0]['version_id'] == "v123"
        assert versions[0]['row_count'] == 1000
        assert versions[1]['billing_period'] == "2024-02"
        
        # Verify query
        query_call = mock_client.query.call_args[0][0]
        assert "SELECT billing_period, version_id" in query_call
        assert "is_current = 1" in query_call
    
    def test_get_version_history(self, state_manager, mock_client):
        """Test getting version history."""
        mock_result = Mock()
        mock_result.result_rows = [
            ("v124", "v2", 1, datetime(2024, 2, 15), datetime(2024, 2, 15), 1500, 6, ""),
            ("v123", "v2", 0, datetime(2024, 1, 15), datetime(2024, 1, 15), 1000, 5, "")
        ]
        mock_client.query.return_value = mock_result
        
        history = state_manager.get_version_history("aws", "test-export", "2024-01")
        
        assert len(history) == 2
        assert history[0]['version_id'] == "v124"
        assert history[0]['current_version'] is True
        assert history[1]['version_id'] == "v123"
        assert history[1]['current_version'] is False
        
        # Verify query
        query_call = mock_client.query.call_args[0][0]
        assert "SELECT version_id, data_format_version" in query_call
        assert "billing_period = %(billing_period)s" in query_call


class TestClickHouseBackendRegistry:
    """Test ClickHouse backend registration."""
    
    def test_backend_registered(self, clean_backend_registry):
        """Test that ClickHouse backend is registered."""
        from core.backends.clickhouse import ClickHouseBackend
        from core.backends.factory import register_backend
        
        # Register the backend (simulating import-time registration)
        register_backend("clickhouse", ClickHouseBackend)
        
        # Verify registration
        assert "clickhouse" in clean_backend_registry
        assert clean_backend_registry["clickhouse"] == ClickHouseBackend