# Open FinOps Stack

**Mission**: Kill paid finops visibility tooling as a market segment by building a complete, open source alternative.

## What is this?

The Open FinOps Stack is a FOCUS-first data platform that ingests cloud billing data from AWS, Azure, and GCP, transforms it into standardized formats, and provides visualization through pre-built dashboards. It's designed to replace expensive FinOps vendors that charge 2-3% of your cloud spend with open source infrastructure that costs pennies on the dollar.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/JGrubb/open-finops-stack.git
cd open-finops-stack

# Install dependencies
pip install -e .

# Run your first pipeline (AWS example)
finops ingest aws --bucket your-cur-bucket --prefix path/to/cur

# Start the visualization layer
docker-compose up -d
```

Visit http://localhost:3000 to see your cloud costs in Metabase.

## Architecture

The stack is built on modern open source tools:

- **DLT (Data Load Tool)** - Handles data ingestion with automatic schema evolution
- **DuckDB** - Local development and data processing (upgrades to ClickHouse/etc for production)
- **dbt** - Transforms vendor billing formats to FOCUS specification
- **Metabase** - Pre-built dashboards and self-service analytics
- **Docker** - One-command deployment of the entire stack

## FOCUS: The Foundation

This project is built around the [FinOps Open Cost and Usage Specification (FOCUS)](https://focus.finops.org/), which standardizes billing data across cloud providers. Instead of maintaining separate transformations for each vendor's format, we build once using FOCUS columns:

- `BillingPeriod` - When the cost was incurred
- `ServiceName` - What service generated the cost
- `ResourceId` - Specific resource identifier
- `UsageQuantity` - How much was consumed
- `EffectiveCost` - Actual cost after discounts
- `BilledCost` - What appears on your invoice

## Blog Series

This project is being built in public through a blog series on [The FinOperator](https://www.thefinoperator.com/):

1. [Building FinOps Data Infrastructure That Scales with FOCUS](./docs/blog-posts/01-building-finops-infrastructure-with-focus.md)
2. Data Pipeline Architecture and CLI Design with DLT (coming soon)
3. AWS Billing Pipeline Implementation (coming soon)
4. Azure Integration and Multi-cloud Refactoring (coming soon)
5. dbt Transformations - Building the FOCUS Conversion Library (coming soon)
6. Metabase Dashboards and Visualization Layer (coming soon)
7. Docker Packaging and Deployment Automation (coming soon)
8. Production Scaling, Cost Allocation, and Advanced Analytics (coming soon)

## 🚀 Current Status: Phase 2 Complete!

This is a complete reboot of the Open FinOps Stack with **FOCUS-first architecture**. 

- **✅ Phase 1 (Foundation)**: Complete AWS CUR pipeline, centralized database, comprehensive testing
- **✅ Phase 2 (Visualization & Docker)**: Metabase integration, full Docker deployment, no Python setup required

**🔄 Next: Dashboard Templates & Advanced Analytics** - Pre-built dashboards, advanced features, and multi-cloud support.

We're building this in public through a blog series on [The FinOperator](https://www.thefinoperator.com). Each blog post corresponds to new functionality added to the codebase.

## 🐳 Docker Deployment (Ready!)

Full Docker support for one-command deployment:

```bash
# Import AWS CUR data (no Python setup needed)
./finops-docker.sh aws import-cur

# Start complete stack (pipeline + Metabase)
docker-compose up -d

# Access Metabase dashboards
open http://localhost:3000
```

See [docs/DOCKER.md](docs/DOCKER.md) for complete setup instructions.

## Key Features

- **AWS CUR Integration**: ✅ COMPLETE - Automatic ingestion of Cost and Usage Reports
- **Centralized Database**: ✅ COMPLETE - DuckDB for local development and analysis
- **CLI Interface**: ✅ COMPLETE - Simple commands for data import and management
- **Comprehensive Testing**: ✅ COMPLETE - 34 tests covering unit and integration scenarios
- **Metabase Integration**: ✅ COMPLETE - Pre-built dashboards and self-service analytics
- **Docker Deployment**: ✅ COMPLETE - One-command setup for the entire stack
- **Dashboard Templates**: 🔄 PLANNED - Pre-built FinOps dashboards (#22)
- **Advanced Analytics**: 🔄 PLANNED - Forecasting, anomaly detection, optimization (#23)

## Contributing

We welcome contributions! The goal is to build the FinOps platform that should have existed all along. Areas where we need help:

- Cloud provider billing format expertise
- FOCUS transformation patterns
- Production deployment patterns
- Dashboard and visualization improvements
- Documentation and tutorials

## License

MIT - Because FinOps infrastructure should be free.

## Why This Matters

Current FinOps vendors charge percentage-of-spend pricing that penalizes growth. A company spending $5M/year on cloud pays $100-150k/year for basic visibility. This is predatory and it needs to stop.

We're building the alternative: open source infrastructure that treats data engineering seriously, respects your existing tools, and costs orders of magnitude less than vendor solutions.

The FinOps vendor tax ends here. Let's build something better.

---

*Star this repo to follow along as we build the future of FinOps tooling.*