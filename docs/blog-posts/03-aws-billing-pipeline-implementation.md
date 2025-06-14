# AWS Billing Pipeline Implementation: From S3 to Analytics-Ready Data

In the [previous post](./02-data-pipeline-architecture-cli-design-dlt.md), we built the foundation: modern pipeline architecture, flexible configuration, and comprehensive testing. Today we're implementing the first cloud provider integration with full AWS Cost and Usage Report (CUR) support.

This isn't a toy implementation. By the end of this post, you'll have a production-ready pipeline that processes real AWS billing data from S3 to DuckDB, handles both CUR v1 and v2 formats, and includes comprehensive test coverage with realistic sample data.

## Understanding AWS Cost and Usage Reports

AWS billing data comes in multiple formats, but Cost and Usage Reports (CUR) provide the most comprehensive view. CUR files contain line-item detail for every charge on your AWS bill, including usage amounts, pricing information, and resource-level metadata.

The complexity comes from AWS supporting two CUR versions with different directory structures and data formats:

### CUR v1 Structure
```
s3://bucket/prefix/export-name/
└── 20240101-20240201/          # Date range directory
    ├── export-name-Manifest.json
    ├── export-name-00001.csv.gz
    └── export-name-00002.csv.gz
```

### CUR v2 Structure  
```
s3://bucket/prefix/export-name/
└── metadata/
    └── BILLING_PERIOD=2024-01/  # Partition-style directory
        ├── export-name-Manifest.json
        ├── export-name-00001.csv.gz
        └── export-name-00002.csv.gz
```

Both formats include a **manifest file**—a JSON metadata file that's critical for reliable processing. The manifest tells you which CSV files contain the most current data for that billing period, because AWS will create multiple versions as they apply final pricing and discounts.

## The Manifest-First Pipeline Pattern

Rather than scanning S3 for CSV files and hoping we get the right ones, our pipeline follows a manifest-first pattern:

1. **Discover** manifests within the date range
2. **Fetch** manifest content to get the current report file list  
3. **Process** only the files listed in each manifest
4. **Replace** existing data for that billing period

This approach handles late-arriving data correctly and ensures we're always processing the most current version of each billing period.

Here's the manifest locator implementation:

```python
class ManifestLocator:
    """Locates and retrieves AWS CUR manifest files."""
    
    def __init__(self, bucket: str, prefix: str, export_name: str, cur_version: str = "v1"):
        self.bucket = bucket
        self.prefix = prefix
        self.export_name = export_name
        self.cur_version = cur_version
    
    def _get_v1_pattern(self) -> str:
        """Get regex pattern for v1 manifest files."""
        return rf"{self.prefix}/{self.export_name}/\d{{8}}-\d{{8}}/{self.export_name}-Manifest\.json"
    
    def _get_v2_pattern(self) -> str:
        """Get regex pattern for v2 manifest files."""
        return rf"{self.prefix}/{self.export_name}/metadata/BILLING_PERIOD=\d{{4}}-\d{{2}}/{self.export_name}-Manifest\.json"
    
    def list_manifests(self, start_date: Optional[str] = None, 
                      end_date: Optional[str] = None) -> List[ManifestFile]:
        """List all manifest files in the bucket within date range."""
        s3 = boto3.client('s3')
        pattern = self._get_v1_pattern() if self.cur_version == "v1" else self._get_v2_pattern()
        
        manifests = []
        paginator = s3.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix):
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                key = obj['Key']
                if re.match(pattern, key):
                    manifest = self._parse_manifest_key(key)
                    if manifest and self._is_in_date_range(manifest, start_date, end_date):
                        manifests.append(manifest)
        
        return sorted(manifests, key=lambda m: m.billing_period)
```

## DLT Pipeline Implementation: Handling Data Replacement

The core pipeline uses DLT's source/resource pattern with our "separate tables" strategy. Each billing period gets its own table that's completely replaced when new data arrives (we'll union those tables together into 1 comprehensive table later on):

```python
@dlt.source(name="aws_cur")
def aws_cur_source(config: AWSConfig):
    """DLT source for AWS Cost and Usage Reports."""
    
    # Initialize manifest locator
    locator = ManifestLocator(
        bucket=config.bucket,
        prefix=config.prefix,
        export_name=config.export_name,
        cur_version=config.cur_version
    )
    
    # List all manifests within date range
    manifests = locator.list_manifests(
        start_date=config.start_date,
        end_date=config.end_date
    )
    
    # Create separate tables for each billing period
    for manifest in manifests:
        table_name = f"billing_{manifest.billing_period.replace('-', '_')}"
        yield dlt.resource(
            billing_period_resource(manifest, config),
            name=table_name,
            write_disposition="replace"  # Always replace the entire table
        )


@dlt.resource
def billing_period_resource(manifest: ManifestFile, config: AWSConfig) -> Iterator[Dict[str, Any]]:
    """DLT resource for a single billing period."""
    
    # Fetch manifest data to get current report files
    manifest = locator.fetch_manifest(manifest)
    
    print(f"Processing billing period: {manifest.billing_period}")
    print(f"  Report files: {len(manifest.report_keys)}")
    
    # Process each report file listed in the manifest
    for report_key in manifest.report_keys:
        # Determine format from file extension or config
        file_format = "parquet" if report_key.endswith('.parquet') else "csv"
        
        # Yield records from the file
        yield from read_report_file(
            bucket=config.bucket,
            key=report_key,
            file_format=file_format
        )
```

## Real AWS CUR Data Format

AWS CUR files use a specific column naming convention: `category/columnName`. Understanding this format is crucial for building transformations and ensuring compatibility:

```csv
identity/LineItemId,identity/TimeInterval,bill/BillingPeriodStartDate,lineItem/UsageAccountId,lineItem/LineItemType,lineItem/UsageStartDate,lineItem/ProductCode,lineItem/UsageType,lineItem/Operation,lineItem/UsageAmount,lineItem/UnblendedCost,product/servicecode,product/region
rm7ubabfqxwsmmutpeljlwx6bfckcandfk4di77zjvspx36aohvq,2024-01-03T00:00:00Z/2024-01-04T00:00:00Z,2024-01-01T00:00:00Z,123456789012,Usage,2024-01-03T03:00:00Z,AmazonEC2,BoxUsage:t3.micro,RunInstances,1.000000000,0.0116000000,AmazonEC2,us-east-1
```

Key column categories include:
- **identity/**: Unique identifiers and time intervals
- **bill/**: Billing period and payer account information  
- **lineItem/**: Core usage and cost data
- **product/**: Service and resource metadata
- **pricing/**: Rate and pricing information

## Sample Data Generation: Testing with Realistic Data

Rather than depending on real AWS accounts for testing, we generate realistic CUR data that matches AWS formats exactly. This enables comprehensive testing without AWS dependencies:

```python
def generate_cur_record(billing_period: str, usage_date: datetime) -> Dict[str, Any]:
    """Generate a single AWS CUR record."""
    
    # Select realistic service and usage patterns
    service_name = random.choice(["AmazonEC2", "AmazonS3", "AmazonRDS", "AWSLambda"])
    line_item_type = random.choices(
        ["Usage", "DiscountedUsage", "Credit", "Discount", "Fee"],
        weights=[70, 15, 3, 5, 7]
    )[0]
    
    # Generate authentic resource identifiers
    resource_id = f"arn:aws:ec2:{region}:{account_id}:instance/i-{random.randint(100000000, 999999999):09x}"
    
    return {
        # Identity columns
        "identity/LineItemId": generate_line_item_id(),  # 50-character lowercase string
        "identity/TimeInterval": f"{usage_start}Z/{usage_end}Z",
        
        # Bill columns  
        "bill/BillingPeriodStartDate": billing_start.strftime('%Y-%m-%dT%H:%M:%S') + "Z",
        "bill/PayerAccountId": account_id,
        
        # LineItem columns
        "lineItem/LineItemType": line_item_type,
        "lineItem/UsageStartDate": usage_start + "Z",
        "lineItem/ProductCode": service_name,
        "lineItem/UsageAmount": round(random.uniform(0.1, 24.0), 10),
        "lineItem/UnblendedCost": round(random.uniform(0.001, 100.0), 10),
        
        # Product columns
        "product/servicecode": service_name,
        "product/region": region,
        
        # Pricing columns
        "pricing/currency": "USD",
        "pricing/unit": "Hrs"
    }
```

This generates data that's indistinguishable from real AWS CUR files, including:
- Proper column naming conventions
- Realistic cost and usage relationships
- Authentic resource ARN formats
- Valid service codes and line item types

## Comprehensive Testing Strategy

Our testing approach validates both the data format and the pipeline logic:

### Unit Tests (21 tests)
- Configuration loading with precedence rules
- Manifest parsing for both CUR v1 and v2
- Date range filtering and S3 key pattern matching

### Integration Tests (13 tests)  
- End-to-end pipeline execution with sample data
- AWS CUR format validation (column structure, data types, ARN formats)
- Manifest structure compliance
- CSV parsing with proper column ordering

The test runner generates fresh sample data for each execution:

```bash
# Run all tests
python run_tests.py

# Results:
# 📊 Generating sample test data...
# ✅ FOCUS sample data generated  
# ✅ AWS CUR sample data generated
# 🔄 Running unit tests - ✅ 21 passed
# 🔄 Running integration tests - ✅ 13 passed  
# 🎉 All tests passed!
```

## Running the AWS Pipeline

With everything implemented, here's how to use the AWS pipeline:

```bash
# List available billing periods
./finops aws list-manifests \
  --bucket your-cur-bucket \
  --prefix cur-reports \
  --export-name monthly-cur

# Import specific date range
./finops aws import-cur \
  --bucket your-cur-bucket \
  --prefix cur-reports \
  --export-name monthly-cur \
  --start-date 2024-01 \
  --end-date 2024-03 \
  --cur-version v2

# Import with configuration file
cp config.toml.example config.toml
# Edit config.toml with your settings
./finops aws import-cur
```

The pipeline creates separate DuckDB tables for each billing period:
- `aws_billing.billing_2024_01`
- `aws_billing.billing_2024_02` 
- `aws_billing.billing_2024_03`

## Performance and Scale Considerations

This implementation handles realistic production volumes:

- **Memory efficiency**: Streaming CSV processing without loading entire files
- **Incremental updates**: Only processes manifests within specified date ranges
- **Parallel processing**: DLT handles concurrent file processing automatically
- **Error recovery**: Failed billing periods don't affect successful ones

For organizations with large AWS bills, the separate tables strategy provides natural partitioning that keeps query performance fast and data management simple.

## What's Next: Multi-Cloud and FOCUS Transformations

We now have a complete AWS billing pipeline that processes real CUR data reliably. In the next post, we'll add Azure billing support and refactor for multi-cloud patterns. Then we'll build the transformation layer that converts vendor billing formats into standardized FOCUS schemas.

The foundation is solid, the first integration is working, and we're building infrastructure that scales. The goal remains unchanged: make multi-cloud, open source finops so accessible that vendor premiums become indefensible.

---

*This post is part of the Open FinOps Stack blog series. All code is available in the [GitHub repository](https://github.com/your-repo/open-finops-stack) and each post corresponds to working, tested functionality.*