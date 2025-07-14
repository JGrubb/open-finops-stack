"""Integration tests for AWS CUR data format and processing."""

import csv
import gzip
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.config import AWSConfig
from vendors.aws.manifest import ManifestLocator
from tests.data.generate_aws_cur_data import create_aws_cur_test_structure


class TestAWSCURFormat:
    """Test AWS CUR data format and processing."""
    
    @pytest.fixture
    def aws_cur_sample_data(self, temp_dir):
        """Create sample AWS CUR structure with test data."""
        manifest_paths = create_aws_cur_test_structure(
            base_path=temp_dir,
            bucket_name="test-cur-bucket",
            prefix="cur-reports",
            export_name="test-cur-export",
            billing_periods=["2024-01", "2024-02"],
            cur_version="v1",
            num_records_per_period=100
        )
        return temp_dir, manifest_paths
    
    def test_aws_cur_csv_structure(self, aws_cur_sample_data):
        """Test that generated AWS CUR CSV has correct structure."""
        base_path, manifest_paths = aws_cur_sample_data
        
        # Find a generated CSV file
        csv_files = list(base_path.rglob("*.csv.gz"))
        assert len(csv_files) > 0
        
        csv_file = csv_files[0]
        
        # Parse the CSV
        with gzip.open(csv_file, 'rt') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 100  # Should match num_records_per_period
        
        # Check required AWS CUR columns are present
        required_columns = [
            "identity/LineItemId",
            "identity/TimeInterval",
            "bill/BillingPeriodStartDate",
            "bill/BillingPeriodEndDate",
            "bill/PayerAccountId",
            "lineItem/UsageAccountId",
            "lineItem/LineItemType",
            "lineItem/UsageStartDate",
            "lineItem/UsageEndDate",
            "lineItem/ProductCode",
            "lineItem/UsageType",
            "lineItem/Operation",
            "lineItem/AvailabilityZone",
            "lineItem/ResourceId",
            "lineItem/UsageAmount",
            "lineItem/UnblendedCost",
            "lineItem/BlendedCost",
            "lineItem/CurrencyCode",
            "product/ProductName",
            "product/servicecode",
            "product/region",
            "pricing/unit",
            "pricing/currency"
        ]
        
        first_row = rows[0]
        for col in required_columns:
            assert col in first_row, f"Missing required AWS CUR column: {col}"
        
        # Verify column naming convention (category/columnName)
        for col_name in first_row.keys():
            if col_name:  # Skip empty column names
                assert '/' in col_name, f"AWS CUR column should have category/name format: {col_name}"
    
    def test_aws_cur_line_item_types(self, aws_cur_sample_data):
        """Test that AWS CUR contains valid line item types."""
        base_path, manifest_paths = aws_cur_sample_data
        
        csv_files = list(base_path.rglob("*.csv.gz"))
        csv_file = csv_files[0]
        
        with gzip.open(csv_file, 'rt') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        valid_line_item_types = [
            "Usage", "DiscountedUsage", "Credit", "Discount", 
            "Fee", "Tax", "Refund", "BundledDiscount"
        ]
        
        found_types = set()
        for row in rows:
            line_item_type = row["lineItem/LineItemType"]
            assert line_item_type in valid_line_item_types
            found_types.add(line_item_type)
        
        # Should have at least Usage type
        assert "Usage" in found_types
    
    def test_aws_cur_service_codes(self, aws_cur_sample_data):
        """Test that AWS CUR contains valid AWS service codes."""
        base_path, manifest_paths = aws_cur_sample_data
        
        csv_files = list(base_path.rglob("*.csv.gz"))
        csv_file = csv_files[0]
        
        with gzip.open(csv_file, 'rt') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        valid_services = [
            "AmazonEC2", "AmazonS3", "AmazonRDS", 
            "AmazonCloudFront", "AWSLambda"
        ]
        
        found_services = set()
        for row in rows:
            service_code = row["product/servicecode"]
            assert service_code in valid_services
            found_services.add(service_code)
            
            # Verify consistency between columns
            assert row["lineItem/ProductCode"] == service_code
            assert row["product/ProductName"] == service_code
    
    def test_aws_cur_cost_data_types(self, aws_cur_sample_data):
        """Test AWS CUR cost and usage data types."""
        base_path, manifest_paths = aws_cur_sample_data
        
        csv_files = list(base_path.rglob("*.csv.gz"))
        csv_file = csv_files[0]
        
        with gzip.open(csv_file, 'rt') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        for row in rows:
            # Test numeric fields
            if row["lineItem/UsageAmount"]:
                usage_amount = float(row["lineItem/UsageAmount"])
                assert usage_amount >= 0
            
            if row["lineItem/UnblendedCost"]:
                cost = float(row["lineItem/UnblendedCost"])
                # Cost can be negative for credits/refunds
            
            if row["lineItem/BlendedCost"]:
                blended_cost = float(row["lineItem/BlendedCost"])
            
            # Test currency
            assert row["lineItem/CurrencyCode"] == "USD"
            assert row["pricing/currency"] == "USD"
            
            # Test date formats (ISO 8601)
            assert "T" in row["lineItem/UsageStartDate"]
            assert "Z" in row["lineItem/UsageStartDate"]
            assert "T" in row["bill/BillingPeriodStartDate"]
    
    def test_aws_cur_resource_identifiers(self, aws_cur_sample_data):
        """Test AWS CUR resource identifier formats."""
        base_path, manifest_paths = aws_cur_sample_data
        
        csv_files = list(base_path.rglob("*.csv.gz"))
        csv_file = csv_files[0]
        
        with gzip.open(csv_file, 'rt') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        for row in rows:
            resource_id = row["lineItem/ResourceId"]
            if resource_id:
                # Should be an ARN format
                assert resource_id.startswith("arn:aws:")
                
                # Verify ARN structure
                arn_parts = resource_id.split(":")
                assert len(arn_parts) >= 6
                assert arn_parts[0] == "arn"
                assert arn_parts[1] == "aws"
                # arn_parts[2] is service
                # arn_parts[3] is region
                # arn_parts[4] is account-id
                # arn_parts[5] is resource
            
            # Test line item ID format
            line_item_id = row["identity/LineItemId"]
            assert len(line_item_id) == 50  # AWS line item IDs are 50 chars
            assert line_item_id.islower()  # Should be lowercase
    
    def test_aws_cur_manifest_structure(self, aws_cur_sample_data):
        """Test AWS CUR manifest file structure."""
        base_path, manifest_paths = aws_cur_sample_data
        
        for period, manifest_path in manifest_paths.items():
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
            
            # Check required manifest fields
            required_fields = [
                "assemblyId", "account", "columns", "charset",
                "compression", "contentType", "reportId", "reportName",
                "billingPeriod", "bucket", "reportKeys"
            ]
            
            for field in required_fields:
                assert field in manifest_data, f"Missing manifest field: {field}"
            
            # Check billing period structure
            billing_period = manifest_data["billingPeriod"]
            assert "start" in billing_period
            assert "end" in billing_period
            assert period in billing_period["start"]
            
            # Check columns structure
            columns = manifest_data["columns"]
            assert len(columns) > 0
            
            for column in columns:
                assert "category" in column
                assert "name" in column
                assert column["category"].endswith("Columns")
                assert "/" in column["name"]  # Should have category/name format
            
            # Verify report keys exist
            assert len(manifest_data["reportKeys"]) > 0
            for report_key in manifest_data["reportKeys"]:
                report_file = base_path / "test-cur-bucket" / report_key
                assert report_file.exists()
    
    def test_aws_cur_region_consistency(self, aws_cur_sample_data):
        """Test AWS region consistency across columns."""
        base_path, manifest_paths = aws_cur_sample_data
        
        csv_files = list(base_path.rglob("*.csv.gz"))
        csv_file = csv_files[0]
        
        with gzip.open(csv_file, 'rt') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        valid_regions = [
            "us-east-1", "us-east-2", "us-west-1", "us-west-2",
            "eu-west-1", "eu-west-2", "eu-central-1",
            "ap-southeast-1", "ap-southeast-2", "ap-northeast-1"
        ]
        
        for row in rows:
            region = row["product/region"]
            az = row["lineItem/AvailabilityZone"]
            
            if region:
                assert region in valid_regions
                
                # AZ should be in the same region
                if az and not az == "":
                    assert az.startswith(region)
    
    def test_aws_cur_with_manifest_locator(self, aws_cur_sample_data):
        """Test AWS CUR data with the manifest locator."""
        base_path, manifest_paths = aws_cur_sample_data
        
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
                manifest_key = f"cur-reports/test-cur-export/{date_range}/test-cur-export-Manifest.json"
                test_files.append({'Key': manifest_key})
            
            mock_paginator = MagicMock()
            mock_s3.get_paginator.return_value = mock_paginator
            mock_paginator.paginate.return_value = [{'Contents': test_files}]
            
            # Mock get_object to read actual files
            def mock_get_object(Bucket, Key):
                local_path = base_path / "test-cur-bucket" / Key
                if local_path.exists():
                    content = local_path.read_text()
                    return {'Body': MagicMock(read=lambda: content.encode())}
                raise Exception(f"File not found: {local_path}")
            
            mock_s3.get_object.side_effect = mock_get_object
            
            # Test the locator with AWS CUR format
            locator = ManifestLocator(
                bucket="test-cur-bucket",
                prefix="cur-reports",
                export_name="test-cur-export",
                cur_version="v1"
            )
            
            manifests = locator.list_manifests()
            assert len(manifests) == 2
            
            # Test fetching AWS CUR manifest content
            for manifest in manifests:
                fetched = locator.fetch_manifest(manifest)
                assert fetched.data is not None
                assert "columns" in fetched.data
                assert "reportKeys" in fetched.data
                
                # Check that columns include AWS CUR specific fields
                column_names = [col["name"] for col in fetched.data["columns"]]
                assert "identity/LineItemId" in column_names
                assert "lineItem/ProductCode" in column_names
                assert "product/servicecode" in column_names