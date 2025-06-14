# Open FinOps Stack Setup Guide

## AWS Prerequisites

### Required AWS Permissions

To use the AWS billing pipeline, you'll need an IAM user or role with the following permissions:

#### S3 Permissions
The IAM entity needs read access to your Cost and Usage Report (CUR) S3 bucket:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-cur-bucket-name",
                "arn:aws:s3:::your-cur-bucket-name/*"
            ]
        }
    ]
}
```

### AWS Credentials Configuration

Configure your AWS credentials using one of these methods:

1. **AWS CLI Configuration** (Recommended)
   ```bash
   aws configure
   ```

2. **Environment Variables**
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1  # or your preferred region
   ```

3. **AWS Credentials File**
   Create or edit `~/.aws/credentials`:
   ```ini
   [default]
   aws_access_key_id = your_access_key
   aws_secret_access_key = your_secret_key
   ```

### Cost and Usage Report Setup

Before running the pipeline, ensure you have:

1. **Created a Cost and Usage Report** in AWS Billing Console
   - Navigate to AWS Billing Console → Cost & Usage Reports
   - Create a new report with:
     - Time granularity: Hourly (recommended) or Daily
     - Include resource IDs: Yes
     - Data integration: Amazon S3
     - Compression: GZIP
     - Format: Text files (.csv) or Parquet

2. **Note your CUR configuration**:
   - S3 bucket name
   - Report path prefix
   - Report name
   - CUR version (v1 or v2)

### Verify Access

Test your access with AWS CLI:
```bash
# List the CUR bucket
aws s3 ls s3://your-cur-bucket-name/your-prefix/

# Test reading a manifest file (adjust path based on your CUR version)
# For v1:
aws s3 cp s3://your-cur-bucket-name/your-prefix/your-report-name/20240101-20240131/your-report-name-Manifest.json -

# For v2:
aws s3 cp s3://your-cur-bucket-name/your-prefix/your-report-name/metadata/BILLING_PERIOD=2024-01/your-report-name-Manifest.json -
```

## Development Setup

### Installing Dependencies

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install development dependencies (includes testing tools)
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run with coverage
python run_tests.py --coverage

# Run with code quality checks
python run_tests.py --quality

# Run specific test types
python -m pytest tests/unit/          # Unit tests only
python -m pytest tests/integration/   # Integration tests only
```

### Testing with Sample Data

The test suite includes a sample data generator that creates FOCUS-compliant billing data for testing:

```bash
# Generate sample data
python -c "from tests.data.generate_sample_data import create_test_s3_structure; create_test_s3_structure('./sample-data', 'test-bucket', 'test-prefix', 'test-export', ['2024-01', '2024-02'], 'v1', 100)"
```

This creates a mock S3 directory structure with:
- Realistic FOCUS billing data
- Proper manifest files
- Both v1 and v2 CUR formats supported
