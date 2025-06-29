"""Unit tests for core utility functions."""

import pytest
from core.table_utils import sanitize_table_name, create_table_name


class TestTableNaming:
    """Test table naming utilities."""
    
    def test_sanitize_table_name_basic(self):
        """Test basic table name sanitization."""
        assert sanitize_table_name("production-account") == "production_account"
        assert sanitize_table_name("PRODUCTION-ACCOUNT") == "production_account"
        assert sanitize_table_name("prod account") == "prod_account"
        assert sanitize_table_name("prod/account") == "prod_account"
        assert sanitize_table_name("prod\\account") == "prod_account"
    
    def test_sanitize_table_name_special_chars(self):
        """Test removing special characters."""
        assert sanitize_table_name("prod@account!") == "prodaccount"
        assert sanitize_table_name("prod#$%account") == "prodaccount"
        assert sanitize_table_name("prod.account") == "prodaccount"
    
    def test_sanitize_table_name_underscores(self):
        """Test handling of underscores."""
        assert sanitize_table_name("prod___account") == "prod_account"
        assert sanitize_table_name("_prod_") == "export_prod"  # Starts with underscore, needs prefix
        assert sanitize_table_name("__prod__account__") == "export_prod_account"  # Starts with underscore
    
    def test_sanitize_table_name_numeric_start(self):
        """Test handling names that start with numbers."""
        assert sanitize_table_name("123account") == "export_123account"
        assert sanitize_table_name("1-prod") == "export_1_prod"
        assert sanitize_table_name("999") == "export_999"
    
    def test_sanitize_table_name_empty(self):
        """Test handling empty or invalid names."""
        assert sanitize_table_name("") == "export"  # Empty string gets prefix only
        assert sanitize_table_name("---") == "export"  # All invalid chars
        assert sanitize_table_name("@#$%") == "export"  # All invalid chars
    
    def test_sanitize_table_name_long(self):
        """Test truncation of long names."""
        long_name = "a" * 100
        result = sanitize_table_name(long_name)
        assert len(result) == 50
        assert result == "a" * 50
    
    def test_create_table_name(self):
        """Test complete table name creation."""
        assert create_table_name("production", "2024-01") == "production_2024_01"
        assert create_table_name("dev-account", "2024-12") == "dev_account_2024_12"
        assert create_table_name("TEST EXPORT", "2023-06") == "test_export_2023_06"
        assert create_table_name("123-export", "2024-01") == "export_123_export_2024_01"