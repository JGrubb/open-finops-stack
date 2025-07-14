"""Unit tests for configuration module."""

import os
import pytest
from pathlib import Path

from core.config import Config, AWSConfig, ProjectConfig


class TestConfig:
    """Test configuration loading and merging."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        
        assert config.project.name == "open-finops-stack"
        assert config.project.data_dir == "./data"
        assert config.aws.cur_version == "v1"
        assert config.aws.reset is False
    
    def test_load_from_toml(self, sample_config_toml):
        """Test loading configuration from TOML file."""
        config = Config.load(sample_config_toml)
        
        assert config.project.name == "test-project"
        assert config.project.data_dir == "./test-data"
        assert config.aws.bucket == "test-bucket"
        assert config.aws.prefix == "test-prefix"
        assert config.aws.export_name == "test-export"
        assert config.aws.cur_version == "v1"
        assert config.aws.export_format == "csv"
    
    def test_env_overrides(self, monkeypatch, temp_dir):
        """Test environment variable overrides."""
        # Create a minimal config file for testing
        config_file = temp_dir / "test_config.toml"
        config_file.write_text("""
[project]
name = "test-project"

[aws]
bucket = "original-bucket"
""")
        
        monkeypatch.setenv("OPEN_FINOPS_AWS_BUCKET", "env-bucket")
        monkeypatch.setenv("OPEN_FINOPS_AWS_PREFIX", "env-prefix")
        monkeypatch.setenv("OPEN_FINOPS_AWS_EXPORT_NAME", "env-export")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
        
        config = Config.load(config_file)
        
        assert config.aws.bucket == "env-bucket"
        assert config.aws.prefix == "env-prefix"
        assert config.aws.export_name == "env-export"
        assert config.aws.access_key_id == "test-key"
        assert config.aws.secret_access_key == "test-secret"
    
    def test_cli_args_merge(self):
        """Test merging CLI arguments."""
        config = Config()
        
        cli_args = {
            "bucket": "cli-bucket",
            "prefix": "cli-prefix",
            "export_name": "cli-export",
            "cur_version": "v2",
            "start_date": "2024-01",
            "end_date": "2024-03",
            "reset": True
        }
        
        config.merge_cli_args(cli_args)
        
        assert config.aws.bucket == "cli-bucket"
        assert config.aws.prefix == "cli-prefix"
        assert config.aws.export_name == "cli-export"
        assert config.aws.cur_version == "v2"
        assert config.aws.start_date == "2024-01"
        assert config.aws.end_date == "2024-03"
        assert config.aws.reset is True
    
    def test_precedence_order(self, sample_config_toml, monkeypatch):
        """Test configuration precedence: CLI > ENV > TOML > defaults."""
        # TOML sets bucket to "test-bucket"
        # ENV will set it to "env-bucket"
        # CLI will set it to "cli-bucket"
        
        monkeypatch.setenv("OPEN_FINOPS_AWS_BUCKET", "env-bucket")
        
        config = Config.load(sample_config_toml)
        assert config.aws.bucket == "env-bucket"  # ENV overrides TOML
        
        config.merge_cli_args({"bucket": "cli-bucket"})
        assert config.aws.bucket == "cli-bucket"  # CLI overrides ENV
    
    def test_validate_aws_config_missing_required(self):
        """Test validation fails when required fields are missing."""
        config = Config()
        
        with pytest.raises(ValueError, match="Missing required AWS configuration"):
            config.validate_aws_config()
    
    def test_validate_aws_config_success(self):
        """Test validation passes with all required fields."""
        config = Config()
        config.aws.bucket = "test-bucket"
        config.aws.prefix = "test-prefix"
        config.aws.export_name = "test-export"
        
        # Should not raise
        config.validate_aws_config()
    
    def test_partial_cli_args(self):
        """Test merging partial CLI arguments."""
        config = Config()
        config.aws.bucket = "original-bucket"
        config.aws.prefix = "original-prefix"
        
        # Only override bucket
        config.merge_cli_args({"bucket": "new-bucket"})
        
        assert config.aws.bucket == "new-bucket"
        assert config.aws.prefix == "original-prefix"  # Unchanged
    
    def test_none_values_ignored(self):
        """Test that None values in CLI args are ignored."""
        config = Config()
        config.aws.bucket = "original-bucket"
        
        config.merge_cli_args({"bucket": None, "prefix": None})
        
        assert config.aws.bucket == "original-bucket"  # Unchanged