"""Integration tests for AWS pipeline."""

import csv
import gzip
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.config import AWSConfig
from vendors.aws.manifest import ManifestLocator
from tests.data.generate_sample_data import create_test_s3_structure


class TestAWSPipelineIntegration:
    """Integration tests for AWS pipeline components."""
    
    @pytest.fixture
    def sample_s3_data(self, temp_dir):
        """Create sample S3 structure with test data."""
        manifest_paths = create_test_s3_structure(
            base_path=temp_dir,
            bucket_name="test-bucket",
            prefix="cur-reports",
            export_name="test-export",
            billing_periods=["2024-01", "2024-02"],
            cur_version="v1",
            num_records_per_period=50
        )
        return temp_dir, manifest_paths
    
    def test_manifest_locator_with_real_files(self, sample_s3_data):
        """Test ManifestLocator with actual file structure."""
        base_path, manifest_paths = sample_s3_data
        
        # Mock S3 to read from local filesystem
        with patch('vendors.aws.manifest.boto3.client') as mock_boto_client:
            mock_s3 = MagicMock()
            mock_boto_client.return_value = mock_s3
            
            # Mock list_objects_v2 to return our test files
            test_files = []
            period_mapping = {
                "2024-01": "20240101-20240201",
                "2024-02": "20240201-20240301"
            }
            for period in ["2024-01", "2024-02"]:
                date_range = period_mapping[period]
                manifest_key = f"cur-reports/test-export/{date_range}/test-export-Manifest.json"
                test_files.append({'Key': manifest_key})
            
            mock_paginator = MagicMock()
            mock_s3.get_paginator.return_value = mock_paginator
            mock_paginator.paginate.return_value = [{'Contents': test_files}]
            
            # Mock get_object to read actual files
            def mock_get_object(Bucket, Key):
                # Map S3 key to local file path
                local_path = base_path / "test-bucket" / Key
                if local_path.exists():
                    content = local_path.read_text()
                    return {'Body': MagicMock(read=lambda: content.encode())}
                raise Exception(f"File not found: {local_path}")
            
            mock_s3.get_object.side_effect = mock_get_object
            
            # Test the locator
            locator = ManifestLocator(
                bucket="test-bucket",
                prefix="cur-reports",
                export_name="test-export",
                cur_version="v1"
            )
            
            manifests = locator.list_manifests()
            assert len(manifests) == 2
            
            # Test fetching manifest content
            for manifest in manifests:
                fetched = locator.fetch_manifest(manifest)
                assert fetched.data is not None
                assert fetched.assembly_id is not None
                assert len(fetched.report_keys) > 0
    
    def test_csv_data_parsing(self, sample_s3_data):
        """Test that generated CSV data is valid and parseable."""
        base_path, manifest_paths = sample_s3_data
        
        # Find a generated CSV file
        csv_files = list(base_path.rglob("*.csv.gz"))
        assert len(csv_files) > 0
        
        csv_file = csv_files[0]
        
        # Parse the CSV
        with gzip.open(csv_file, 'rt') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 50  # Should match num_records_per_period
        
        # Check FOCUS columns are present
        required_columns = [
            "BillingPeriodStart",
            "BillingPeriodEnd",
            "ServiceName",
            "ResourceId",
            "UsageQuantity",
            "BilledCost",
            "EffectiveCost",
            "BillingCurrency",
            "Provider"
        ]
        
        first_row = rows[0]
        for col in required_columns:
            assert col in first_row, f"Missing required column: {col}"
            assert first_row[col] is not None and first_row[col] != ""
        
        # Check data types and formats
        assert first_row["Provider"] == "AWS"
        assert first_row["BillingCurrency"] == "USD"
        assert first_row["ServiceName"] in ["EC2", "S3", "RDS", "Lambda", "DynamoDB", "CloudFront"]
        
        # Check cost values are numeric
        assert float(first_row["BilledCost"]) >= 0
        assert float(first_row["EffectiveCost"]) >= 0
        assert float(first_row["UsageQuantity"]) >= 0
    
    def test_manifest_content_validation(self, sample_s3_data):
        """Test that generated manifests contain valid data."""
        base_path, manifest_paths = sample_s3_data
        
        for period, manifest_path in manifest_paths.items():
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
            
            # Check required fields
            assert "assemblyId" in manifest_data
            assert "bucket" in manifest_data
            assert "reportKeys" in manifest_data
            assert "billingPeriod" in manifest_data
            assert "columns" in manifest_data
            
            # Check billing period format
            billing_period = manifest_data["billingPeriod"]
            assert "start" in billing_period
            assert "end" in billing_period
            assert period in billing_period["start"]
            
            # Check report keys point to existing files
            assert len(manifest_data["reportKeys"]) > 0
            for report_key in manifest_data["reportKeys"]:
                report_file = base_path / "test-bucket" / report_key
                assert report_file.exists(), f"Report file not found: {report_file}"
    
    def test_date_range_filtering(self, sample_s3_data):
        """Test date range filtering works correctly."""
        base_path, manifest_paths = sample_s3_data
        
        with patch('vendors.aws.manifest.boto3.client') as mock_boto_client:
            mock_s3 = MagicMock()
            mock_boto_client.return_value = mock_s3
            
            # Mock S3 responses
            all_files = [
                {'Key': 'cur-reports/test-export/20240101-20240201/test-export-Manifest.json'},
                {'Key': 'cur-reports/test-export/20240201-20240301/test-export-Manifest.json'}
            ]
            
            mock_paginator = MagicMock()
            mock_s3.get_paginator.return_value = mock_paginator
            mock_paginator.paginate.return_value = [{'Contents': all_files}]
            
            locator = ManifestLocator(
                bucket="test-bucket",
                prefix="cur-reports",
                export_name="test-export",
                cur_version="v1"
            )
            
            # Test filtering to only January
            manifests = locator.list_manifests(start_date="2024-01", end_date="2024-01")
            assert len(manifests) == 1
            assert manifests[0].billing_period == "2024-01"
            
            # Test no filtering - should get all
            manifests = locator.list_manifests()
            assert len(manifests) == 2
    
    @pytest.fixture
    def aws_config(self):
        """Create test AWS configuration."""
        return AWSConfig(
            bucket="test-bucket",
            prefix="cur-reports",
            export_name="test-export",
            cur_version="v1",
            export_format="csv",
            region="us-east-1"
        )
    
    def test_aws_config_validation(self, aws_config):
        """Test AWS configuration validation."""
        from core.config import Config
        
        config = Config()
        config.aws = aws_config
        
        # Should not raise with all required fields
        config.validate_aws_config()
        
        # Should raise with missing bucket
        config.aws.bucket = None
        with pytest.raises(ValueError, match="Missing required AWS configuration"):
            config.validate_aws_config()