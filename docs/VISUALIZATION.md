# Visualizing Your FinOps Data with Metabase

This guide walks you through setting up Metabase to visualize your AWS billing data stored in DuckDB.

## Prerequisites

- Docker Desktop installed and running
- AWS billing data imported (run `./finops aws import-cur` first)

## Quick Start

```bash
# Start Metabase with DuckDB support
./start-metabase.sh
```

This script will:
1. Build a custom Metabase image with the MotherDuck DuckDB driver
2. Start Metabase and PostgreSQL (for Metabase metadata)
3. Mount your DuckDB database at `/data/finops.duckdb`

## Initial Setup

### 1. Access Metabase

Open http://localhost:3000 in your browser

### 2. Create Admin Account

- Fill in your details
- Remember these credentials!

### 3. Connect to DuckDB

1. Skip the "Add your data" step during setup
2. Go to **Settings** (gear icon) > **Admin settings**
3. Navigate to **Databases** > **Add database**
4. Select **DuckDB** as the database type
5. Configure:
   - **Display name**: `FinOps Data`
   - **Database file**: `/data/finops.duckdb`
6. Click **Save**

## Creating Your First Dashboard

### 1. Explore Your Data

Click **Browse** > **FinOps Data** > **aws_billing**

You'll see tables like:
- `billing_2024_01` (January 2024 data)
- `billing_2024_02` (February 2024 data)
- etc.

### 2. Create a Monthly Cost Trend

1. Click **New** > **Question**
2. Choose **FinOps Data** as your data source
3. Select a billing table (e.g., `billing_2024_01`)
4. Use the query builder or switch to SQL mode

**SQL Example - Monthly Costs**:
```sql
SELECT 
    DATE_TRUNC('month', billing_period_start_date) as month,
    SUM(CAST(unblended_cost AS DECIMAL(10,2))) as total_cost
FROM aws_billing.billing_2024_01
WHERE unblended_cost IS NOT NULL 
  AND unblended_cost != ''
GROUP BY month
ORDER BY month
```

### 3. Service Cost Breakdown

**SQL Example - Top 10 Services**:
```sql
SELECT 
    product_name as service,
    SUM(CAST(unblended_cost AS DECIMAL(10,2))) as cost
FROM aws_billing.billing_2024_01
WHERE unblended_cost IS NOT NULL 
  AND unblended_cost != ''
  AND product_name IS NOT NULL
GROUP BY product_name
ORDER BY cost DESC
LIMIT 10
```

### 4. Daily Spending Pattern

**SQL Example - Daily Costs**:
```sql
SELECT 
    DATE(usage_start_date) as date,
    SUM(CAST(unblended_cost AS DECIMAL(10,2))) as daily_cost
FROM aws_billing.billing_2024_01
WHERE unblended_cost IS NOT NULL
GROUP BY date
ORDER BY date
```

## Building a FinOps Dashboard

1. Create visualizations for:
   - Monthly cost trends (line chart)
   - Service breakdown (pie/donut chart)
   - Daily spending (area chart)
   - Top cost drivers (table)

2. Add them to a dashboard:
   - Click **New** > **Dashboard**
   - Name it "AWS Cost Overview"
   - Add your saved questions
   - Arrange and resize as needed

## Advanced Queries

### Cost by Usage Type
```sql
SELECT 
    usage_type,
    COUNT(*) as line_items,
    SUM(CAST(unblended_cost AS DECIMAL(10,2))) as total_cost
FROM aws_billing.billing_2024_01
WHERE unblended_cost IS NOT NULL
GROUP BY usage_type
HAVING SUM(CAST(unblended_cost AS DECIMAL(10,2))) > 0
ORDER BY total_cost DESC
```

### EC2 Instance Analysis
```sql
SELECT 
    resource_id,
    usage_type,
    SUM(CAST(usage_amount AS DECIMAL(10,2))) as hours,
    SUM(CAST(unblended_cost AS DECIMAL(10,2))) as cost
FROM aws_billing.billing_2024_01
WHERE product_name = 'Amazon Elastic Compute Cloud'
  AND resource_id IS NOT NULL
GROUP BY resource_id, usage_type
ORDER BY cost DESC
```

## Tips

1. **Performance**: DuckDB is fast! Don't hesitate to query across months
2. **Caching**: Enable query caching in Metabase for frequently-used dashboards
3. **Permissions**: Set up user groups if sharing dashboards with your team
4. **Alerts**: Set up cost threshold alerts using Metabase's alerting feature

## Troubleshooting

- **Can't connect to DuckDB**: Ensure the path is exactly `/data/finops.duckdb`
- **No data showing**: Verify you've imported data with `./finops aws list-manifests`
- **Slow queries**: Check if you're casting strings to numbers repeatedly - consider creating a view

## Next Steps

1. Import more months of data for trend analysis
2. Create saved questions for common queries
3. Build team-specific dashboards
4. Set up automated alerts for cost anomalies
5. Export visualizations for reports