"""Generate realistic AWS Cost and Usage Report (CUR) test data."""

import csv
import gzip
import json
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional


# AWS service configurations
AWS_SERVICES = {
    "AmazonEC2": {
        "usage_types": [
            "BoxUsage:t3.micro",
            "BoxUsage:t3.small", 
            "BoxUsage:t3.medium",
            "BoxUsage:m5.large",
            "BoxUsage:c5.xlarge",
            "EBS:VolumeUsage.gp2",
            "EBS:VolumeUsage.gp3"
        ],
        "operations": ["RunInstances", "CreateVolume", "AttachVolume"],
        "pricing_units": ["Hrs", "GB-Mo"],
        "instance_families": ["t3", "t2", "m5", "c5", "r5"]
    },
    "AmazonS3": {
        "usage_types": [
            "TimedStorage-ByteHrs",
            "Requests-Tier1",
            "Requests-Tier2", 
            "DataTransfer-Out-Bytes"
        ],
        "operations": ["PutObject", "GetObject", "ListBucket", "DeleteObject"],
        "pricing_units": ["GB-Mo", "Requests", "GB"],
        "storage_classes": ["STANDARD", "STANDARD_IA", "GLACIER"]
    },
    "AmazonRDS": {
        "usage_types": [
            "InstanceUsage:db.t3.micro",
            "InstanceUsage:db.t3.small",
            "InstanceUsage:db.r5.large",
            "StorageUsage"
        ],
        "operations": ["CreateDBInstance", "RunDBInstance"],
        "pricing_units": ["Hrs", "GB-Mo"],
        "engines": ["mysql", "postgres", "aurora"]
    },
    "AmazonCloudFront": {
        "usage_types": [
            "Requests-HTTP",
            "Requests-HTTPS",
            "DataTransfer-Out-Bytes"
        ],
        "operations": ["OriginRequest", "ViewerRequest"],
        "pricing_units": ["Requests", "GB"],
        "edge_locations": ["US", "EU", "Asia"]
    },
    "AWSLambda": {
        "usage_types": [
            "Request-Count",
            "Duration-Arm",
            "Duration-x86"
        ],
        "operations": ["Invoke", "InvokeAsync"],
        "pricing_units": ["Requests", "GB-Second"],
        "runtimes": ["python3.9", "nodejs18.x", "java11"]
    }
}

# Line item types and their characteristics
LINE_ITEM_TYPES = {
    "Usage": {"weight": 70, "has_usage": True, "has_cost": True},
    "DiscountedUsage": {"weight": 15, "has_usage": True, "has_cost": True}, 
    "Credit": {"weight": 3, "has_usage": False, "has_cost": True},
    "Discount": {"weight": 5, "has_usage": False, "has_cost": True},
    "Fee": {"weight": 4, "has_usage": False, "has_cost": True},
    "Tax": {"weight": 2, "has_usage": False, "has_cost": True},
    "Refund": {"weight": 1, "has_usage": False, "has_cost": True}
}

REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "eu-west-1", "eu-west-2", "eu-central-1",
    "ap-southeast-1", "ap-southeast-2", "ap-northeast-1"
]

AVAILABILITY_ZONES = {
    "us-east-1": ["us-east-1a", "us-east-1b", "us-east-1c"],
    "us-west-2": ["us-west-2a", "us-west-2b", "us-west-2c"],
    "eu-west-1": ["eu-west-1a", "eu-west-1b", "eu-west-1c"]
}


def generate_line_item_id() -> str:
    """Generate a realistic AWS line item ID."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=50))


def generate_resource_id(service: str, region: str) -> str:
    """Generate a realistic AWS resource ID."""
    account_id = "123456789012"
    
    if service == "AmazonEC2":
        instance_id = f"i-{random.randint(100000000, 999999999):09x}"
        return f"arn:aws:ec2:{region}:{account_id}:instance/{instance_id}"
    elif service == "AmazonS3":
        bucket_name = f"test-bucket-{random.randint(1000, 9999)}"
        return f"arn:aws:s3:::{bucket_name}"
    elif service == "AmazonRDS":
        db_name = f"test-db-{random.randint(100, 999)}"
        return f"arn:aws:rds:{region}:{account_id}:db:{db_name}"
    elif service == "AWSLambda":
        func_name = f"test-function-{random.randint(100, 999)}"
        return f"arn:aws:lambda:{region}:{account_id}:function:{func_name}"
    else:
        return f"arn:aws:{service.lower()}:{region}:{account_id}:resource/test-{random.randint(1000, 9999)}"


def generate_cur_record(
    billing_period: str,
    usage_date: datetime,
    account_id: str = "123456789012"
) -> Dict[str, Any]:
    """Generate a single AWS CUR record."""
    
    # Select service and line item type
    service_name = random.choice(list(AWS_SERVICES.keys()))
    service_config = AWS_SERVICES[service_name]
    
    # Weighted selection of line item type
    line_item_type = random.choices(
        list(LINE_ITEM_TYPES.keys()),
        weights=[info["weight"] for info in LINE_ITEM_TYPES.values()]
    )[0]
    line_item_config = LINE_ITEM_TYPES[line_item_type]
    
    # Select region and AZ
    region = random.choice(REGIONS)
    availability_zone = random.choice(AVAILABILITY_ZONES.get(region, [f"{region}a"]))
    
    # Generate usage details
    usage_type = random.choice(service_config["usage_types"])
    operation = random.choice(service_config["operations"])
    pricing_unit = random.choice(service_config["pricing_units"])
    
    # Generate time intervals
    usage_start = usage_date
    usage_end = usage_start + timedelta(hours=1)
    
    # Billing period dates
    year, month = map(int, billing_period.split('-'))
    billing_start = datetime(year, month, 1)
    if month == 12:
        billing_end = datetime(year + 1, 1, 1)
    else:
        billing_end = datetime(year, month + 1, 1)
    
    # Generate costs and usage
    if line_item_config["has_usage"]:
        usage_amount = round(random.uniform(0.1, 24.0), 10)  # Hours for most services
        if "GB" in pricing_unit:
            usage_amount = round(random.uniform(0.1, 1000.0), 10)  # GB for storage
        elif "Requests" in pricing_unit:
            usage_amount = round(random.uniform(1, 10000), 0)  # Request count
    else:
        usage_amount = 0.0
    
    if line_item_config["has_cost"]:
        if line_item_type in ["Credit", "Discount", "Refund"]:
            unblended_cost = -round(random.uniform(0.01, 50.0), 10)
            blended_cost = unblended_cost
        else:
            unblended_cost = round(random.uniform(0.001, 100.0), 10)
            blended_cost = round(unblended_cost * random.uniform(0.8, 1.2), 10)
    else:
        unblended_cost = 0.0
        blended_cost = 0.0
    
    # Generate unit prices
    if usage_amount > 0:
        unblended_rate = round(unblended_cost / usage_amount, 10)
        blended_rate = round(blended_cost / usage_amount, 10)
    else:
        unblended_rate = 0.0
        blended_rate = 0.0
    
    # Base CUR record
    record = {
        # Identity columns
        "identity/LineItemId": generate_line_item_id(),
        "identity/TimeInterval": f"{usage_start.strftime('%Y-%m-%dT%H:%M:%S')}Z/{usage_end.strftime('%Y-%m-%dT%H:%M:%S')}Z",
        
        # Bill columns
        "bill/BillingEntity": "AWS",
        "bill/BillType": "Anniversary",
        "bill/PayerAccountId": account_id,
        "bill/BillingPeriodStartDate": billing_start.strftime('%Y-%m-%dT%H:%M:%S') + "Z",
        "bill/BillingPeriodEndDate": billing_end.strftime('%Y-%m-%dT%H:%M:%S') + "Z",
        
        # LineItem columns
        "lineItem/UsageAccountId": account_id,
        "lineItem/LineItemType": line_item_type,
        "lineItem/UsageStartDate": usage_start.strftime('%Y-%m-%dT%H:%M:%S') + "Z",
        "lineItem/UsageEndDate": usage_end.strftime('%Y-%m-%dT%H:%M:%S') + "Z",
        "lineItem/ProductCode": service_name,
        "lineItem/UsageType": usage_type,
        "lineItem/Operation": operation,
        "lineItem/AvailabilityZone": availability_zone,
        "lineItem/ResourceId": generate_resource_id(service_name, region),
        "lineItem/UsageAmount": usage_amount,
        "lineItem/CurrencyCode": "USD",
        "lineItem/UnblendedRate": unblended_rate,
        "lineItem/UnblendedCost": unblended_cost,
        "lineItem/BlendedRate": blended_rate,
        "lineItem/BlendedCost": blended_cost,
        "lineItem/LineItemDescription": f"{service_name} {operation} in {region}",
        
        # Product columns
        "product/ProductName": service_name,
        "product/servicecode": service_name,
        "product/servicename": service_name,
        "product/region": region,
        "product/location": region.replace('-', ' ').title(),
        "product/usagetype": usage_type,
        "product/operation": operation,
        
        # Pricing columns
        "pricing/unit": pricing_unit,
        "pricing/currency": "USD",
        "pricing/publicOnDemandRate": unblended_rate,
        "pricing/publicOnDemandCost": unblended_cost,
        "pricing/term": "OnDemand"
    }
    
    # Add service-specific product attributes
    if service_name == "AmazonEC2":
        record.update({
            "product/instanceType": usage_type.split(':')[-1] if ':' in usage_type else "t3.micro",
            "product/operatingSystem": random.choice(["Linux", "Windows"]),
            "product/tenancy": "Shared",
            "product/vcpu": str(random.randint(1, 8)),
            "product/memory": f"{random.randint(1, 32)} GiB"
        })
    elif service_name == "AmazonS3":
        record.update({
            "product/storageClass": random.choice(service_config["storage_classes"]),
            "product/volumeType": "Standard"
        })
    elif service_name == "AmazonRDS":
        record.update({
            "product/databaseEngine": random.choice(service_config["engines"]),
            "product/instanceType": usage_type.split(':')[-1] if ':' in usage_type else "db.t3.micro",
            "product/deploymentOption": random.choice(["Single-AZ", "Multi-AZ"])
        })
    
    # Add some resource tags
    tag_keys = ["Environment", "Project", "Owner", "CostCenter"]
    for i, tag_key in enumerate(random.sample(tag_keys, random.randint(1, 3))):
        record[f"resourceTags/user:{tag_key}"] = f"tag-value-{random.randint(1, 10)}"
    
    return record


def generate_aws_cur_data(
    billing_period: str,
    num_records: int = 1000,
    account_id: str = "123456789012"
) -> List[Dict[str, Any]]:
    """Generate AWS CUR data for a billing period."""
    
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
        
        record = generate_cur_record(billing_period, usage_date, account_id)
        records.append(record)
    
    return records


def create_aws_cur_manifest(
    bucket: str,
    prefix: str,
    export_name: str,
    billing_period: str,
    report_keys: List[str],
    account_id: str = "123456789012"
) -> Dict[str, Any]:
    """Create an AWS CUR manifest file."""
    
    year, month = map(int, billing_period.split('-'))
    billing_start = datetime(year, month, 1)
    if month == 12:
        billing_end = datetime(year + 1, 1, 1)
    else:
        billing_end = datetime(year, month + 1, 1)
    
    # Get all possible columns from a sample record
    sample_record = generate_cur_record(billing_period, billing_start, account_id)
    columns = []
    
    for col_name in sorted(sample_record.keys()):
        category = col_name.split('/')[0] + "Columns"
        columns.append({
            "category": category,
            "name": col_name
        })
    
    manifest = {
        "assemblyId": f"{billing_period}-{random.randint(10000, 99999)}",
        "account": account_id,
        "columns": columns,
        "charset": "UTF-8",
        "compression": "GZIP",
        "contentType": "text/csv",
        "reportId": export_name,
        "reportName": export_name,
        "billingPeriod": {
            "start": billing_start.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "Z",
            "end": billing_end.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "Z"
        },
        "bucket": bucket,
        "reportKeys": report_keys,
        "additionalArtifacts": [
            {
                "name": "REDSHIFT_MANIFEST",
                "location": f"{prefix}/{export_name}/redshift-manifest"
            },
            {
                "name": "QUICKSIGHT_MANIFEST", 
                "location": f"{prefix}/{export_name}/quicksight-manifest.json"
            }
        ]
    }
    
    return manifest


def save_aws_cur_data(
    data: List[Dict[str, Any]],
    output_path: Path,
    compress: bool = True
) -> str:
    """Save AWS CUR data to CSV file."""
    
    if not data:
        raise ValueError("No data to save")
    
    # Get all columns across all records
    all_columns = set()
    for record in data:
        all_columns.update(record.keys())
    
    # Sort columns by category (identity, bill, lineItem, product, etc.)
    column_order = ["identity", "bill", "lineItem", "product", "pricing", "reservation", "savingsPlans", "resourceTags"]
    sorted_columns = []
    
    for category in column_order:
        category_cols = [col for col in all_columns if col.startswith(f"{category}/")]
        sorted_columns.extend(sorted(category_cols))
    
    # Add any remaining columns
    remaining_cols = [col for col in all_columns if not any(col.startswith(f"{cat}/") for cat in column_order)]
    sorted_columns.extend(sorted(remaining_cols))
    
    if compress:
        output_file = output_path.with_suffix('.csv.gz')
        with gzip.open(output_file, 'wt', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sorted_columns)
            writer.writeheader()
            for record in data:
                # Fill missing columns with empty strings
                complete_record = {col: record.get(col, '') for col in sorted_columns}
                writer.writerow(complete_record)
    else:
        output_file = output_path.with_suffix('.csv')
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sorted_columns)
            writer.writeheader()
            for record in data:
                complete_record = {col: record.get(col, '') for col in sorted_columns}
                writer.writerow(complete_record)
    
    return str(output_file)


def create_aws_cur_test_structure(
    base_path: Path,
    bucket_name: str,
    prefix: str,
    export_name: str,
    billing_periods: List[str],
    cur_version: str = "v1",
    num_records_per_period: int = 1000,
    account_id: str = "123456789012"
) -> Dict[str, str]:
    """Create a test AWS CUR S3 structure with realistic data."""
    
    bucket_path = base_path / bucket_name
    bucket_path.mkdir(parents=True, exist_ok=True)
    
    manifest_paths = {}
    
    for billing_period in billing_periods:
        print(f"Generating AWS CUR data for {billing_period}...")
        
        # Generate CUR data
        data = generate_aws_cur_data(billing_period, num_records_per_period, account_id)
        
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
        
        # Save CUR data file
        data_filename = f"{export_name}-00001"
        data_path = period_dir / data_filename
        saved_file = save_aws_cur_data(data, data_path, compress=True)
        
        # Get relative path for manifest
        relative_path = str(Path(saved_file).relative_to(bucket_path))
        
        # Create manifest
        manifest_data = create_aws_cur_manifest(
            bucket=bucket_name,
            prefix=prefix,
            export_name=export_name,
            billing_period=billing_period,
            report_keys=[relative_path],
            account_id=account_id
        )
        
        # Save manifest
        manifest_path = period_dir / f"{export_name}-Manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest_data, f, indent=2)
        
        manifest_paths[billing_period] = str(manifest_path)
        print(f"  Created {len(data)} records")
    
    return manifest_paths


if __name__ == "__main__":
    # Example usage
    base_path = Path("./test-aws-cur-data")
    
    # Create sample AWS CUR data for testing
    manifest_paths = create_aws_cur_test_structure(
        base_path=base_path,
        bucket_name="test-cur-bucket",
        prefix="cur-reports",
        export_name="test-cur-export",
        billing_periods=["2024-01", "2024-02", "2024-03"],
        cur_version="v1",
        num_records_per_period=500
    )
    
    print("\nCreated AWS CUR sample data:")
    for period, path in manifest_paths.items():
        print(f"  {period}: {path}")