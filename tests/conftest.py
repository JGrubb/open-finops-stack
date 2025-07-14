"""Pytest configuration and fixtures."""

import os
import tempfile
from pathlib import Path
import pytest
import shutil

from core.config import Config, AWSConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_config_toml(temp_dir):
    """Create a sample config.toml file."""
    config_path = temp_dir / "config.toml"
    config_content = """
[project]
name = "test-project"
data_dir = "./test-data"

[aws]
bucket = "test-bucket"
prefix = "test-prefix"
export_name = "test-export"
cur_version = "v1"
export_format = "csv"
"""
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def aws_config():
    """Create a test AWS configuration."""
    return AWSConfig(
        bucket="test-bucket",
        prefix="test-prefix",
        export_name="test-export",
        cur_version="v1",
        export_format="csv",
        region="us-east-1"
    )


@pytest.fixture
def mock_aws_credentials(monkeypatch):
    """Mock AWS credentials for testing."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key-id")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")