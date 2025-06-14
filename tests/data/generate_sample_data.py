"""Generate FOCUS-compliant sample billing data for testing."""

import csv
import gzip
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any


def generate_focus_record(
    billing_period: str,
    service_name: str,
    region: str,
    usage_date: datetime
) -> Dict[str, Any]:
    """Generate a single FOCUS-compliant billing record."""
    
    # Core FOCUS columns
    record = {
        # Temporal
        "BillingPeriodStart": f"{billing_period}-01T00:00:00Z",
        "BillingPeriodEnd": f"{billing_period}-01T00:00:00Z",  # Will be adjusted
        "ChargePeriodStart": usage_date.strftime("%Y-%m-%dT%H:00:00Z"),
        "ChargePeriodEnd": (usage_date + timedelta(hours=1)).strftime("%Y-%m-%dT%H:00:00Z"),
        
        # Service and Resource
        "ServiceName": service_name,
        "ServiceCategory": "Compute" if service_name in ["EC2", "Lambda"] else "Storage",
        "ResourceId": f"arn:aws:{service_name.lower()}:{region}:123456789012:instance/i-{random.randint(1000000, 9999999):07d}",
        "ResourceName": f"test-{service_name.lower()}-{random.randint(1, 100)}",
        "Region": region,
        "AvailabilityZone": f"{region}{random.choice(['a', 'b', 'c'])}",
        
        # Usage
        "UsageQuantity": round(random.uniform(0.1, 100.0), 6),
        "UsageUnit": "Hours" if service_name in ["EC2", "RDS"] else "GB",
        "PricingQuantity": round(random.uniform(0.1, 100.0), 6),
        "PricingUnit": "Hours",
        
        # Cost
        "BilledCost": round(random.uniform(0.01, 100.0), 6),
        "EffectiveCost": round(random.uniform(0.01, 90.0), 6),
        "ListCost": round(random.uniform(0.01, 110.0), 6),
        "ListUnitPrice": round(random.uniform(0.001, 1.0), 6),
        "ContractedUnitPrice": round(random.uniform(0.001, 0.9), 6),
        "EffectiveUnitPrice": round(random.uniform(0.001, 0.8), 6),
        "BillingCurrency": "USD",
        
        # Provider
        "Provider": "AWS",
        "InvoiceIssuer": "AWS",
        "BillingAccountId": "123456789012",
        "BillingAccountName": "Test Account",
        
        # Tags
        "Tags": json.dumps({
            "Environment": random.choice(["Production", "Development", "Staging"]),
            "Project": f"Project-{random.randint(1, 10)}",
            "Owner": f"team-{random.randint(1, 5)}"
        }),
        
        # Commitment
        "CommitmentDiscountCategory": random.choice(["None", "Spend", "Usage"]),
        "CommitmentDiscountType": random.choice(["None", "Reserved Instance", "Savings Plan"]),
        
        # Additional metadata
        "ChargeCategory": "Purchase",
        "ChargeFrequency": "Usage-Based",
        "ChargeType": "Usage",
        "ConsumedQuantity": round(random.uniform(0.1, 100.0), 6),
        "ConsumedUnit": "Hours",
        "SkuId": f"SKU{random.randint(10000, 99999)}",
        "SkuPriceId": f"PRICE{random.randint(10000, 99999)}"
    }
    
    # Fix billing period end
    year, month = billing_period.split('-')
    if int(month) == 12:
        next_month = f"{int(year) + 1}-01"
    else:
        next_month = f"{year}-{int(month) + 1:02d}"
    record["BillingPeriodEnd"] = f"{next_month}-01T00:00:00Z"
    
    return record


def generate_sample_cur_data(
    billing_period: str,
    num_records: int = 1000,
    output_format: str = "csv"
) -> List[Dict[str, Any]]:
    """Generate sample CUR data for a billing period."""
    
    services = ["EC2", "S3", "RDS", "Lambda", "DynamoDB", "CloudFront"]
    regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
    
    records = []
    year, month = map(int, billing_period.split('-'))
    start_date = datetime(year, month, 1)
    
    # Calculate days in month
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    days_in_month = (end_date - start_date).days
    
    for _ in range(num_records):
        # Random day and hour within the billing period
        day = random.randint(1, days_in_month)
        hour = random.randint(0, 23)
        usage_date = datetime(year, month, day, hour)
        
        service = random.choice(services)
        region = random.choice(regions)
        
        record = generate_focus_record(billing_period, service, region, usage_date)
        records.append(record)
    
    return records


def create_sample_manifest(
    bucket: str,
    prefix: str,
    export_name: str,
    billing_period: str,
    cur_version: str = "v1",
    report_keys: List[str] = None
) -> Dict[str, Any]:
    """Create a sample CUR manifest file."""
    
    manifest = {
        "assemblyId": f"{billing_period}-{random.randint(10000, 99999)}",
        "bucket": bucket,
        "reportKeys": report_keys or [],
        "billingPeriod": {
            "start": f"{billing_period}-01T00:00:00.000Z",
            "end": f"{billing_period}-01T00:00:00.000Z"  # Will be adjusted
        },
        "columns": [
            {"category": "temporalColumns", "name": "BillingPeriodStart"},
            {"category": "temporalColumns", "name": "BillingPeriodEnd"},
            {"category": "temporalColumns", "name": "ChargePeriodStart"},
            {"category": "temporalColumns", "name": "ChargePeriodEnd"},
            {"category": "providerColumns", "name": "Provider"},
            {"category": "providerColumns", "name": "BillingAccountId"},
            {"category": "serviceColumns", "name": "ServiceName"},
            {"category": "serviceColumns", "name": "ServiceCategory"},
            {"category": "resourceColumns", "name": "ResourceId"},
            {"category": "resourceColumns", "name": "Region"},
            {"category": "usageColumns", "name": "UsageQuantity"},
            {"category": "usageColumns", "name": "UsageUnit"},
            {"category": "costColumns", "name": "BilledCost"},
            {"category": "costColumns", "name": "EffectiveCost"},
            {"category": "costColumns", "name": "BillingCurrency"}
        ]
    }
    
    # Fix billing period end
    year, month = billing_period.split('-')
    if int(month) == 12:
        next_month = f"{int(year) + 1}-01"
    else:
        next_month = f"{year}-{int(month) + 1:02d}"
    manifest["billingPeriod"]["end"] = f"{next_month}-01T00:00:00.000Z"
    
    return manifest


def save_sample_data(
    data: List[Dict[str, Any]],
    output_path: Path,
    format: str = "csv",
    compress: bool = True
) -> str:
    """Save sample data to file."""
    
    if format == "csv":
        if compress:
            output_file = output_path.with_suffix('.csv.gz')
            with gzip.open(output_file, 'wt', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
        else:
            output_file = output_path.with_suffix('.csv')
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
    else:
        # For parquet format, would need to use pyarrow
        raise NotImplementedError("Parquet format not yet implemented")
    
    return str(output_file)


def create_test_s3_structure(
    base_path: Path,
    bucket_name: str,
    prefix: str,
    export_name: str,
    billing_periods: List[str],
    cur_version: str = "v1",
    num_records_per_period: int = 100
) -> Dict[str, str]:
    """Create a test S3-like directory structure with sample data."""
    
    bucket_path = base_path / bucket_name
    bucket_path.mkdir(parents=True, exist_ok=True)
    
    manifest_paths = {}
    
    for billing_period in billing_periods:
        # Generate sample data
        data = generate_sample_cur_data(billing_period, num_records_per_period)
        
        # Create directory structure based on CUR version
        if cur_version == "v1":
            # v1 structure: prefix/export_name/YYYYMMDD-YYYYMMDD/
            year, month = billing_period.split('-')
            start_date = f"{year}{month}01"
            if int(month) == 12:
                end_date = f"{int(year) + 1}0101"
            else:
                end_date = f"{year}{int(month) + 1:02d}01"
            
            period_dir = bucket_path / prefix / export_name / f"{start_date}-{end_date}"
        else:
            # v2 structure: prefix/export_name/metadata/BILLING_PERIOD=YYYY-MM/
            period_dir = bucket_path / prefix / export_name / "metadata" / f"BILLING_PERIOD={billing_period}"
        
        period_dir.mkdir(parents=True, exist_ok=True)
        
        # Save data file
        data_filename = f"{export_name}-00001"
        data_path = period_dir / data_filename
        saved_file = save_sample_data(data, data_path, format="csv", compress=True)
        
        # Create manifest
        manifest_data = create_sample_manifest(
            bucket=bucket_name,
            prefix=prefix,
            export_name=export_name,
            billing_period=billing_period,
            cur_version=cur_version,
            report_keys=[saved_file.replace(str(bucket_path) + "/", "")]
        )
        
        # Save manifest
        manifest_path = period_dir / f"{export_name}-Manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest_data, f, indent=2)
        
        manifest_paths[billing_period] = str(manifest_path)
    
    return manifest_paths


if __name__ == "__main__":
    # Example usage
    base_path = Path("./test-data")
    
    # Create sample data for testing
    manifest_paths = create_test_s3_structure(
        base_path=base_path,
        bucket_name="test-bucket",
        prefix="cur-reports",
        export_name="test-export",
        billing_periods=["2024-01", "2024-02", "2024-03"],
        cur_version="v1",
        num_records_per_period=100
    )
    
    print("Created sample data:")
    for period, path in manifest_paths.items():
        print(f"  {period}: {path}")