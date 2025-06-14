"""Unit tests for AWS manifest module."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.pipelines.aws.manifest import ManifestFile, ManifestLocator


class TestManifestFile:
    """Test ManifestFile dataclass."""
    
    def test_manifest_file_creation(self):
        """Test creating a ManifestFile."""
        manifest = ManifestFile(
            bucket="test-bucket",
            key="test-key",
            billing_period="2024-01",
            version="v1"
        )
        
        assert manifest.bucket == "test-bucket"
        assert manifest.key == "test-key"
        assert manifest.billing_period == "2024-01"
        assert manifest.version == "v1"
        assert manifest.data is None
    
    def test_report_keys_empty(self):
        """Test report_keys property when data is None."""
        manifest = ManifestFile(
            bucket="test-bucket",
            key="test-key",
            billing_period="2024-01",
            version="v1"
        )
        
        assert manifest.report_keys == []
    
    def test_report_keys_with_data(self):
        """Test report_keys property with manifest data."""
        manifest = ManifestFile(
            bucket="test-bucket",
            key="test-key",
            billing_period="2024-01",
            version="v1",
            data={"reportKeys": ["file1.csv.gz", "file2.csv.gz"]}
        )
        
        assert manifest.report_keys == ["file1.csv.gz", "file2.csv.gz"]
    
    def test_assembly_id(self):
        """Test assembly_id property."""
        manifest = ManifestFile(
            bucket="test-bucket",
            key="test-key",
            billing_period="2024-01",
            version="v1",
            data={"assemblyId": "2024-01-12345"}
        )
        
        assert manifest.assembly_id == "2024-01-12345"


class TestManifestLocator:
    """Test ManifestLocator class."""
    
    def test_init(self):
        """Test ManifestLocator initialization."""
        locator = ManifestLocator(
            bucket="test-bucket",
            prefix="test-prefix",
            export_name="test-export",
            cur_version="v2"
        )
        
        assert locator.bucket == "test-bucket"
        assert locator.prefix == "test-prefix"
        assert locator.export_name == "test-export"
        assert locator.cur_version == "v2"
        assert locator.s3_client is None
    
    def test_v1_pattern(self):
        """Test v1 manifest path pattern."""
        locator = ManifestLocator(
            bucket="bucket",
            prefix="prefix",
            export_name="export",
            cur_version="v1"
        )
        
        pattern = locator._get_v1_pattern()
        expected = r"prefix/export/\d{8}-\d{8}/export-Manifest\.json"
        assert pattern == expected
    
    def test_v2_pattern(self):
        """Test v2 manifest path pattern."""
        locator = ManifestLocator(
            bucket="bucket",
            prefix="prefix",
            export_name="export",
            cur_version="v2"
        )
        
        pattern = locator._get_v2_pattern()
        expected = r"prefix/export/metadata/BILLING_PERIOD=\d{4}-\d{2}/export-Manifest\.json"
        assert pattern == expected
    
    def test_parse_manifest_key_v1(self):
        """Test parsing v1 manifest key."""
        locator = ManifestLocator(
            bucket="bucket",
            prefix="prefix",
            export_name="export",
            cur_version="v1"
        )
        
        key = "prefix/export/20240101-20240201/export-Manifest.json"
        manifest = locator._parse_manifest_key(key)
        
        assert manifest is not None
        assert manifest.billing_period == "2024-01"
        assert manifest.key == key
        assert manifest.version == "v1"
    
    def test_parse_manifest_key_v2(self):
        """Test parsing v2 manifest key."""
        locator = ManifestLocator(
            bucket="bucket",
            prefix="prefix",
            export_name="export",
            cur_version="v2"
        )
        
        key = "prefix/export/metadata/BILLING_PERIOD=2024-01/export-Manifest.json"
        manifest = locator._parse_manifest_key(key)
        
        assert manifest is not None
        assert manifest.billing_period == "2024-01"
        assert manifest.key == key
        assert manifest.version == "v2"
    
    def test_is_in_date_range(self):
        """Test date range filtering."""
        locator = ManifestLocator(
            bucket="bucket",
            prefix="prefix",
            export_name="export",
            cur_version="v1"
        )
        
        manifest = ManifestFile(
            bucket="bucket",
            key="key",
            billing_period="2024-02",
            version="v1"
        )
        
        # No date range - should include
        assert locator._is_in_date_range(manifest, None, None) is True
        
        # Within range
        assert locator._is_in_date_range(manifest, "2024-01", "2024-03") is True
        
        # Before start date
        assert locator._is_in_date_range(manifest, "2024-03", None) is False
        
        # After end date
        assert locator._is_in_date_range(manifest, None, "2024-01") is False
        
        # Exact match
        assert locator._is_in_date_range(manifest, "2024-02", "2024-02") is True
    
    @patch('boto3.client')
    def test_list_manifests(self, mock_boto_client):
        """Test listing manifests from S3."""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Mock paginator
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        
        # Mock S3 response
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {'Key': 'prefix/export/20240101-20240201/export-Manifest.json'},
                    {'Key': 'prefix/export/20240201-20240301/export-Manifest.json'},
                    {'Key': 'prefix/export/20240301-20240401/export-Manifest.json'},
                    {'Key': 'prefix/export/some-other-file.csv.gz'}  # Should be ignored
                ]
            }
        ]
        
        locator = ManifestLocator(
            bucket="bucket",
            prefix="prefix",
            export_name="export",
            cur_version="v1"
        )
        
        manifests = locator.list_manifests(start_date="2024-01", end_date="2024-02")
        
        assert len(manifests) == 2
        assert manifests[0].billing_period == "2024-01"
        assert manifests[1].billing_period == "2024-02"
    
    @patch('boto3.client')
    def test_fetch_manifest(self, mock_boto_client):
        """Test fetching manifest content from S3."""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Mock manifest data
        manifest_data = {
            "assemblyId": "2024-01-12345",
            "reportKeys": ["prefix/export/data/file1.csv.gz"]
        }
        
        # Mock S3 response
        mock_response = {
            'Body': MagicMock(read=lambda: json.dumps(manifest_data).encode())
        }
        mock_s3.get_object.return_value = mock_response
        
        locator = ManifestLocator(
            bucket="bucket",
            prefix="prefix",
            export_name="export",
            cur_version="v1"
        )
        
        manifest = ManifestFile(
            bucket="bucket",
            key="test-key",
            billing_period="2024-01",
            version="v1"
        )
        
        fetched = locator.fetch_manifest(manifest)
        
        assert fetched.data == manifest_data
        assert fetched.assembly_id == "2024-01-12345"
        assert fetched.report_keys == ["prefix/export/data/file1.csv.gz"]