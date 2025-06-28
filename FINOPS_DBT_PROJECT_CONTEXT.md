# FinOps FOCUS Transformations - DBT Project Context

## Project Mission
Create a comprehensive DBT project that transforms cloud provider billing data into standardized FOCUS (FinOps Open Cost and Usage Specification) format, enabling consistent multi-cloud cost analysis and eliminating vendor-specific data model complexity.

## Repository Scope
This would be a standalone DBT project repository (`finops-focus-transformations` or `open-finops-dbt`) that provides:

### Core Capabilities
- **FOCUS Standardization**: Transform AWS CUR, Azure billing exports, and GCP billing data into standardized FOCUS columns
- **Multi-Cloud Unified Schema**: Single analytical layer across all cloud providers
- **Cost Allocation Models**: Implement standard FinOps allocation methodologies
- **Data Quality**: Validation and testing for FOCUS compliance
- **Incremental Processing**: Efficient transformation of large billing datasets

### FOCUS Specification Compliance
Transform vendor-specific columns into standard FOCUS dimensions:

**Core FOCUS Columns:**
- `BillingPeriod` - When the cost was incurred
- `ServiceName` - What service generated the cost  
- `ResourceId` - Specific resource identifier
- `UsageQuantity` - How much was consumed
- `EffectiveCost` - Actual cost after discounts
- `BilledCost` - What appears on your invoice
- `ChargeCategory` - Usage, Tax, Credit, etc.
- `ChargeClass` - On-Demand, Reservation, Spot, etc.
- `ChargeFrequency` - One-Time, Recurring, Usage-Based
- `AccountId` - Billing account identifier
- `SubAccountId` - Sub-account or subscription ID

**Extended FOCUS Columns:**
- `PricingCategory` - Standard, Spot, Reservation, Savings Plan
- `CommitmentDiscountCategory` - Reservation, Savings Plan
- `Region` - Standardized region naming
- `AvailabilityZone` - Standardized AZ naming
- `Tags` - Normalized tag structure

## Architecture Integration

### Data Flow
```
Raw Cloud Data → [Main Pipeline] → DuckDB → [DBT Transformations] → FOCUS Tables → [Visualization]
     ↓                              ↓                               ↓
AWS CUR (CSV/Parquet)         aws_billing.*              focus_billing.*
Azure Billing Export          azure_billing.*            focus_billing.*  
GCP Billing Export           gcp_billing.*               focus_billing.*
```

### Database Integration
- **Input**: Raw billing tables created by main ingestion pipeline
- **Output**: Standardized `focus_*` tables for visualization layer
- **Database**: Shared DuckDB instance (`./data/finops.duckdb`)
- **Deployment**: DBT runs as transformation layer between ingestion and visualization

### Repository Structure
```
finops-focus-transformations/
├── dbt_project.yml              # DBT project configuration
├── profiles.yml.example         # DuckDB connection template
├── models/                      # Transformation models
│   ├── staging/                 # Source data cleaning
│   │   ├── aws/                 # AWS CUR staging models
│   │   │   ├── stg_aws_line_items.sql
│   │   │   ├── stg_aws_reservations.sql
│   │   │   └── stg_aws_resources.sql
│   │   ├── azure/               # Azure staging models
│   │   │   ├── stg_azure_usage.sql
│   │   │   └── stg_azure_costs.sql
│   │   └── gcp/                 # GCP staging models
│   │       ├── stg_gcp_billing.sql
│   │       └── stg_gcp_projects.sql
│   ├── intermediate/            # Business logic transformations
│   │   ├── int_unified_costs.sql
│   │   ├── int_resource_mapping.sql
│   │   └── int_allocation_rules.sql
│   └── marts/                   # Final FOCUS-compliant tables
│       ├── focus_billing.sql    # Main FOCUS billing table
│       ├── focus_resources.sql  # Resource dimension
│       └── focus_summary.sql    # Pre-aggregated summaries
├── macros/                      # Reusable transformation logic
│   ├── focus_standardization.sql
│   ├── cost_allocation.sql
│   └── tag_normalization.sql
├── tests/                       # Data quality tests
│   ├── focus_compliance.yml     # FOCUS spec validation
│   ├── cost_reconciliation.yml  # Cost totals validation
│   └── data_quality.yml         # General quality checks
├── seeds/                       # Reference data
│   ├── focus_service_mapping.csv
│   ├── region_standardization.csv
│   └── charge_categories.csv
├── docs/                        # Documentation
│   ├── FOCUS_MAPPING.md         # Cloud provider → FOCUS mapping
│   ├── SETUP.md                 # Integration setup guide
│   └── CUSTOMIZATION.md         # Extending transformations
└── examples/                    # Sample configurations
    ├── profiles/                # DBT profiles for different setups
    └── vars/                    # Variable examples for customization
```

## Key Transformation Challenges

### AWS CUR → FOCUS Mapping
```sql
-- Example: AWS line items to FOCUS standardization
SELECT 
    -- Temporal
    DATE_TRUNC('month', lineitem_usagestartdate) as billing_period,
    lineitem_usagestartdate as billing_period_start,
    lineitem_usageenddate as billing_period_end,
    
    -- Identity  
    lineitem_productcode as service_name,
    lineitem_resourceid as resource_id,
    lineitem_usageaccountid as account_id,
    
    -- Financial
    lineitem_unblendedcost as billed_cost,
    CASE 
        WHEN lineitem_lineitemtype = 'DiscountedUsage' 
        THEN lineitem_unblendedcost 
        ELSE lineitem_netunblendedcost 
    END as effective_cost,
    
    -- Usage
    lineitem_usagequantity as usage_quantity,
    lineitem_usageunit as usage_unit,
    
    -- Classification
    CASE lineitem_lineitemtype
        WHEN 'Usage' THEN 'Usage'
        WHEN 'Tax' THEN 'Tax' 
        WHEN 'Credit' THEN 'Credit'
        ELSE 'Other'
    END as charge_category
    
FROM {{ ref('stg_aws_line_items') }}
```

### Multi-Cloud Service Name Standardization
```sql
-- Macro: standardize_service_name
{% macro standardize_service_name(cloud_provider, raw_service_name) %}
    CASE 
        WHEN '{{ cloud_provider }}' = 'aws' AND {{ raw_service_name }} = 'AmazonEC2' THEN 'Compute'
        WHEN '{{ cloud_provider }}' = 'azure' AND {{ raw_service_name }} = 'Virtual Machines' THEN 'Compute'
        WHEN '{{ cloud_provider }}' = 'gcp' AND {{ raw_service_name }} = 'Compute Engine' THEN 'Compute'
        -- Add comprehensive mapping...
        ELSE {{ raw_service_name }}
    END
{% endmacro %}
```

## Integration with Main Pipeline

### Deployment Options

**Option 1: Integrated Deployment**
- DBT transformations run as part of main pipeline
- Triggered after data ingestion completes
- Single `./finops transform` command

**Option 2: Separate Service**
- Independent DBT deployment
- Scheduled transformations (hourly/daily)
- API endpoints for triggering transforms

**Option 3: Event-Driven**
- Transformations triggered by data ingestion events
- Queue-based processing for large datasets
- Incremental updates only

### Configuration Integration
```toml
# config.toml - Main pipeline configuration
[transformations]
enabled = true
dbt_project_dir = "./transformations"  # Git submodule or separate install
run_after_import = true
incremental_only = true

[transformations.focus]
include_extended_columns = true
cost_allocation_method = "proportional"  # or "direct", "custom"
tag_inheritance = true
currency_standardization = "USD"

[transformations.outputs]
create_summary_tables = true
partition_by_month = true
retain_source_columns = false  # FOCUS-only output
```

## Value Proposition

### For End Users
- **Vendor Independence**: Consistent data model regardless of cloud provider
- **Cost Analysis**: Standard FinOps metrics across all environments  
- **Migration Flexibility**: Easy cloud provider transitions
- **Compliance**: FOCUS specification adherence

### For the Ecosystem
- **Reusable Library**: DBT transformations usable across organizations
- **Community Contributions**: Cloud provider expertise from different users
- **Extensibility**: Custom allocation rules and business logic
- **Standardization**: Industry adoption of FOCUS specification

### For Integration
- **Metabase Ready**: FOCUS tables optimized for visualization
- **API Compatible**: Standard schema for programmatic access
- **Export Friendly**: Clean data for external systems
- **Performance Optimized**: Pre-aggregated summary tables

## Implementation Phases

### Phase 1: AWS FOCUS Foundation
- Core AWS CUR → FOCUS transformations
- Basic data quality testing
- Integration with existing DuckDB pipeline
- Documentation and setup guides

### Phase 2: Multi-Cloud Support  
- Azure billing export transformations
- GCP billing API transformations
- Cross-cloud service name standardization
- Unified FOCUS output schema

### Phase 3: Advanced FinOps Features
- Cost allocation methodologies
- Chargeback and showback models
- Reserved Instance and Savings Plan analytics
- Custom business rule framework

### Phase 4: Production Hardening
- Performance optimization for large datasets
- Incremental processing strategies
- Data lineage and audit trails
- Enterprise features (RBAC, compliance)

## Technical Requirements

### Dependencies
- **DBT Core**: Latest stable version with DuckDB adapter
- **DuckDB**: Compatible with main pipeline version
- **Python**: For custom macros and testing
- **Git**: For version control and submodule integration

### Performance Considerations
- **Incremental Models**: Process only new/changed data
- **Partitioning**: Monthly partitions for large datasets
- **Indexing**: Optimize for common query patterns
- **Materialization**: Balance between speed and storage

### Testing Strategy
- **FOCUS Compliance**: Validate against official specification
- **Cost Reconciliation**: Ensure transformation accuracy
- **Performance Testing**: Benchmark with realistic data volumes
- **Integration Testing**: End-to-end pipeline validation

## Questions for Further Definition

1. **Repository Naming**: `finops-focus-transformations`, `open-finops-dbt`, or `focus-dbt-library`?

2. **Versioning Strategy**: How to handle FOCUS specification updates and breaking changes?

3. **Customization Level**: Should organizations fork the repo, or provide extensive configuration options?

4. **Cloud Provider Priority**: Start with AWS-only, or design multi-cloud from day one?

5. **Data Retention**: Should transformed data replace raw data, or maintain both layers?

6. **Performance vs. Flexibility**: Optimize for speed, or prioritize customization capabilities?

This DBT project would be the critical transformation layer that makes the Open FinOps Stack truly vendor-agnostic and FOCUS-compliant, providing the standardized data foundation that visualization and analytics tools require.