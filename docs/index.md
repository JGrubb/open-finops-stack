---
layout: home
title: Open FinOps Stack Documentation
---

# Open FinOps Stack

**Mission**: Kill paid finops visibility tooling as a market segment by building a complete, open source alternative.

The Open FinOps Stack is a FOCUS-first data platform that ingests cloud billing data from AWS, Azure, and GCP, transforms it into standardized formats, and provides visualization through pre-built dashboards.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/JGrubb/open-finops-stack.git
cd open-finops-stack

# Docker deployment (recommended)
./finops-docker.sh aws import-cur
docker-compose up -d

# Access dashboards
open http://localhost:3000
```

## Documentation Sections

### 🚀 [Getting Started](getting-started/)
- [Installation](getting-started/installation.md)
- [Quick Start Guide](getting-started/quick-start.md)
- [Configuration](getting-started/configuration.md)

### 📖 [User Guide](user-guide/)
- [AWS Integration](user-guide/aws-integration.md)
- [Data Management](user-guide/data-management.md)
- [Dashboards & Analytics](user-guide/dashboards.md)

### 🐳 [Deployment](deployment/)
- [Docker Setup](deployment/docker.md)
- [Production Deployment](deployment/production.md)
- [Troubleshooting](deployment/troubleshooting.md)

### 🛠️ [Development](development/)
- [Contributing](development/contributing.md)
- [Architecture](development/architecture.md)
- [Testing](development/testing.md)

### 📚 [Reference](reference/)
- [CLI Commands](reference/cli.md)
- [API Documentation](reference/api.md)
- [FOCUS Specification](reference/focus.md)

### 📝 [Blog Series](blog-posts/)
- [Building FinOps Data Infrastructure That Scales with FOCUS](blog-posts/01-building-finops-infrastructure-with-focus.md)
- [Data Pipeline Architecture and CLI Design with DLT](blog-posts/02-data-pipeline-architecture-cli-design-dlt.md)
- [AWS Billing Pipeline: From Basic Implementation to Production-Ready](blog-posts/03-aws-billing-pipeline-implementation.md)

## Current Status

- **✅ Phase 1**: AWS CUR pipeline, centralized database, comprehensive testing
- **✅ Phase 1.5**: Performance optimizations, state tracking, multi-export support
- **🔄 Phase 2**: Container runtime with Podman (Docker alternative)
- **⏳ Phase 3**: Metabase visualization, pre-built dashboards
- **⏳ Phase 4**: Multi-cloud support (Azure, GCP)
- **⏳ Phase 5**: Production features, dbt transformations

## Why Open FinOps?

Current FinOps vendors charge 2-3% of your cloud spend for basic visibility. A company spending $5M/year pays $100-150k/year for dashboards.

We're building the alternative: open source infrastructure that costs pennies on the dollar and gives you complete control over your data.