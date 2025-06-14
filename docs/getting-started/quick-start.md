---
layout: page
title: Quick Start Guide
parent: Getting Started
---

# 5-Minute Quick Start

Get Open FinOps Stack running with real data in under 5 minutes.

## Step 1: Clone and Configure (1 minute)

```bash
# Clone repository
git clone https://github.com/JGrubb/open-finops-stack.git
cd open-finops-stack

# Copy and edit configuration
cp config.toml.example config.toml
```

Edit `config.toml` with your AWS details:
```toml
[aws]
bucket = "your-cur-bucket-name"
prefix = "path/to/your/cur/data"
export_name = "your-export-name"
cur_version = "v1"  # or "v2"
```

## Step 2: Import Your First Data (2 minutes)

```bash
# Import AWS billing data (Docker method)
./finops-docker.sh aws import-cur

# OR Python method
python -m src.cli.main aws import-cur
```

You should see output like:
```
✓ Found 3 manifests in your CUR bucket
✓ Processing manifest for 2024-01
✓ Imported 1,247 billing records
✓ Data saved to ./data/finops.duckdb
```

## Step 3: Start Dashboards (1 minute)

```bash
# Start Metabase with your data
docker-compose up -d

# Wait for startup (about 30 seconds)
echo "Waiting for Metabase to start..."
sleep 30
```

## Step 4: Explore Your Data (1 minute)

1. **Open dashboards**: http://localhost:3000
2. **Initial setup**: Create admin account when prompted
3. **Connect to data**: Database will be pre-configured
4. **Browse data**: Click "Browse Data" → "aws_billing"

## What You'll See

### Database Tables
- `aws_billing.billing_2024_01` - January 2024 costs
- `aws_billing.billing_2024_02` - February 2024 costs
- (One table per month of data)

### Sample Data Exploration
```sql
-- Total spend by service
SELECT 
  product_product_name as service,
  SUM(line_item_blended_cost) as total_cost
FROM aws_billing.billing_2024_01 
GROUP BY product_product_name 
ORDER BY total_cost DESC 
LIMIT 10;

-- Daily cost trends
SELECT 
  line_item_usage_start_date::date as date,
  SUM(line_item_blended_cost) as daily_cost
FROM aws_billing.billing_2024_01 
GROUP BY date 
ORDER BY date;
```

## Next Steps (Optional)

### Import More Data
```bash
# Import specific month
./finops-docker.sh aws import-cur --month 2024-02

# Import all available data
./finops-docker.sh aws import-cur --all
```

### Create Your First Dashboard
1. In Metabase, click "New" → "Dashboard"
2. Add visualizations:
   - Cost over time (line chart)
   - Top services (bar chart)
   - Resource breakdown (table)

### Explore Advanced Features
- [Set up automated imports](../deployment/production.md)
- [Create custom dashboards](../user-guide/dashboards.md)
- [Configure alerts and monitoring](../user-guide/monitoring.md)

## Troubleshooting Quick Fixes

**"No manifests found"**
- Double-check bucket name and prefix in config.toml
- Verify AWS credentials: `aws s3 ls s3://your-bucket/your-prefix/`

**"Port 3000 already in use"**
```bash
# Stop other services using port 3000
docker-compose down
# Or change port in docker-compose.yml
```

**"Permission denied"**
```bash
chmod +x finops-docker.sh
```

## Success! 🎉

You now have:
- ✅ AWS billing data imported and queryable
- ✅ Metabase dashboards running locally
- ✅ A complete FinOps platform ready for customization

**Total time**: ~5 minutes
**Total cost**: $0 (vs $100-150k/year for vendor solutions)

Ready to dive deeper? Check out the [User Guide](../user-guide/) for advanced features and customization options.