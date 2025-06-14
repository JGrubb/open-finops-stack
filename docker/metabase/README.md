# Metabase with DuckDB for FinOps Visualization

This directory contains the Docker setup for running Metabase with the official MotherDuck DuckDB driver.

## Quick Start

1. Start the services:
```bash
docker-compose up -d
```

2. Wait for Metabase to initialize (check logs):
```bash
docker-compose logs -f metabase
```

3. Access Metabase at http://localhost:3000

4. Complete the initial setup:
   - Create your admin account
   - Skip the "Add your data" step (we'll do this manually)

## Connecting to DuckDB

After initial setup:

1. Go to **Settings** > **Admin settings** > **Databases** > **Add database**

2. Choose **DuckDB** as the database type

3. Configure the connection:
   - **Display name**: FinOps Data
   - **Database file**: `/data/finops.duckdb`
   - Leave other settings as default

4. Click **Save**

## Exploring Your Data

Once connected, you can:

1. **Browse Data**: Click "Browse" to see your AWS billing tables
   - Schema: `aws_billing`
   - Tables: `billing_2024_01`, `billing_2024_02`, etc.

2. **Ask Questions**: Use Metabase's query builder to analyze your costs

3. **Create Dashboards**: Build visualizations for:
   - Monthly cost trends
   - Service breakdown
   - Cost by account
   - Daily spending patterns

## Sample Queries

Here are some useful starting queries:

### Monthly Cost Summary
```sql
SELECT 
    SUBSTRING(time_interval, 1, 7) as month,
    SUM(CAST(unblended_cost AS DECIMAL)) as total_cost
FROM aws_billing.billing_2024_01
GROUP BY month
ORDER BY month
```

### Top Services by Cost
```sql
SELECT 
    product_name,
    SUM(CAST(unblended_cost AS DECIMAL)) as cost
FROM aws_billing.billing_2024_01
WHERE unblended_cost IS NOT NULL
GROUP BY product_name
ORDER BY cost DESC
LIMIT 10
```

## Troubleshooting

- **Driver not found**: Make sure the Docker build completes successfully
- **Cannot connect to database**: Verify the file path is `/data/finops.duckdb`
- **Permission denied**: The data volume should be mounted as read-only (`:ro`)

## Updates

To update the DuckDB driver version:
1. Check latest releases at: https://github.com/MotherDuck-Open-Source/metabase_duckdb_driver/releases
2. Update the version in `Dockerfile`
3. Rebuild: `docker-compose build metabase`