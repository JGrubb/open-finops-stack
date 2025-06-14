# Building FinOps Data Infrastructure That Scales with FOCUS

Every cloud engineer enters finops the same way: a request to "help make sense of our cloud costs" leads to discovering that AWS, Azure, and GCP each have completely different billing formats. You build custom transformations, normalize schemas, and six months later you're maintaining a brittle system that breaks whenever vendors change their APIs. Meanwhile, you're being pitched finops tools that want to charge 2-3% of your cloud spend—essentially charging you more as your infrastructure scales, when the value they provide stays exactly the same.

The FinOps Open Cost and Usage Specification (FOCUS) was designed to solve the first problem by providing a common format across all vendors. More importantly, it lets you build finops data infrastructure once, correctly, with patterns that scale as your organization grows. And that's exactly what we're going to do.

## The Market Problem: Vendor Extraction at Scale

Before we dive into FOCUS, let's acknowledge what's really happening in the finops tooling market. Vendors are charging percentage-of-spend pricing to customers who are already struggling with cloud costs. It's a business model that penalizes growth and extracts more revenue as your pain increases. It's predatory, and it needs to stop.

The good news? The technology exists to build better alternatives. Open source tools like DuckDB, modern data pipeline frameworks, and standardized formats like FOCUS have matured to the point where building your own finops infrastructure isn't just possible—it's practical.

## What We're Building Together

This post kicks off a series where we'll build a complete, open source finops visibility platform from scratch. By the end of this series, you'll have:

- **Multi-cloud billing ingestion** using FOCUS-standardized formats
- **Scalable data pipelines** built with modern open source tools  
- **Standardized transformations** using dbt to convert any vendor format to FOCUS
- **Pre-built dashboards** with Metabase for immediate visibility
- **Docker deployment** that makes the entire platform installable by anyone with basic technical skills
- **Production-ready infrastructure** that costs pennies per dollar compared to vendor solutions

Each post will add functionality while documenting the architectural decisions and trade-offs. You'll see working code, real implementation patterns, and honest assessments of what works (and what doesn't).

The goal isn't just education—it's to kill the finops vendor tax by making the alternative so accessible that paying vendor premiums becomes indefensible.

## Why FOCUS Changes Everything

FOCUS isn't a product—it's a specification that provides "guidance to cloud vendors, practitioners, tooling vendors, and the software engineering community at large" about how billing data should be structured. Think of it as the standardized schema that finally lets you build infrastructure once instead of maintaining vendor-specific transformations forever.

Here's what the architecture looks like before and after FOCUS:

*[FOCUS Architecture Comparison diagram would be embedded here]*

The transformation isn't just about fewer ETL pipelines—it's about fundamentally different infrastructure patterns. With FOCUS, you can:

- **Design data models once** instead of mapping between vendor vocabularies
- **Build reusable components** that work across all cloud providers
- **Focus on business logic** instead of format wrangling
- **Scale infrastructure horizontally** without vendor-specific complexity

## The Technical Foundation: FOCUS Schema Essentials

FOCUS defines a common vocabulary for cloud billing with standardized columns that work across all providers. Instead of learning that AWS calls something `lineItem/UsageAmount` while Azure calls it `Quantity` and GCP calls it `usage.amount`, FOCUS gives us a single `UsageQuantity` column.

Here are the core FOCUS columns that matter for infrastructure design:

```sql
BillingPeriod      # When the cost was incurred
ServiceName        # What service generated the cost  
ResourceId         # Specific resource identifier
UsageQuantity      # How much was consumed
UsageUnit          # Unit of measurement
ListCost           # Published price
EffectiveCost      # Actual cost after discounts
BilledCost         # What appears on your invoice
```

This isn't just about column naming—it's about designing your data models around concepts that are stable across vendors. When you build your warehouse schema using FOCUS patterns, adding a new cloud provider becomes a configuration change instead of a development project.

## Our Technology Stack: Open Source All the Way Down

We're building this with tools that are free, performant, and designed for cloud engineering at scale:

- **DuckDB** - Our starting point for data processing and transformation. It's a single binary that handles massive datasets and speaks SQL fluently.

- **DLT (Data Load Tool)** - Modern Python framework for building data pipelines. It handles the boring parts (incremental loading, schema evolution, error handling) so we can focus on business logic.

- **dbt** - Version-controlled transformations that convert vendor billing formats to FOCUS. We'll build a library of transformations that handles every major cloud provider and billing format.

- **Metabase** - Pre-built dashboards and analytics that work out-of-the-box with FOCUS data.

- **Docker** - Package everything into a deployable platform that works anywhere.

- **FOCUS Specification** - Our data modeling foundation that ensures everything we build works across cloud vendors.

- **Python + SQL** - Because you already know these tools, and they're perfect for the job.

Starting with DuckDB might seem humble, but it's strategically smart. We'll prove the patterns work with the simplest possible setup, then show how they scale to production systems (ClickHouse, BigQuery, Snowflake) in later posts.

## A Quick Taste: FOCUS Transformation with DuckDB

Let's see how FOCUS-first thinking changes data pipeline design. Here's a snippet that transforms raw AWS billing data into FOCUS format:

```sql
-- Transform AWS CUR to FOCUS format
CREATE TABLE focus_billing AS
SELECT 
    bill_billing_period_start_date as BillingPeriod,
    product_product_name as ServiceName,
    line_item_resource_id as ResourceId,
    line_item_usage_amount as UsageQuantity,
    line_item_usage_type as UsageUnit,
    line_item_unblended_cost as ListCost,
    line_item_net_unblended_cost as EffectiveCost,
    line_item_blended_cost as BilledCost
FROM aws_billing_raw;
```

The beauty isn't the SQL—it's that this same pattern works for Azure and GCP data once they're in FOCUS format. One transformation logic, multiple data sources.

## What's Coming Next

The next post will dive into the data pipeline architecture, introducing DLT and designing the CLI interface for our finops platform. We'll start with AWS billing ingestion and build the foundation that makes multi-cloud support trivial.

Here's the roadmap:

- **Post 2**: Data pipeline architecture and CLI design with DLT
- **Post 3**: AWS billing pipeline implementation  
- **Post 4**: Azure billing integration and multi-cloud refactoring
- **Post 5**: dbt transformations - building the FOCUS conversion library
- **Post 6**: Metabase dashboards and visualization layer
- **Post 7**: Docker packaging and deployment automation
- **Posts 8+**: Production scaling, cost allocation, and advanced analytics

By the end, we'll have built the finops platform that should have existed all along—one that treats data engineering seriously, respects your existing infrastructure, and costs orders of magnitude less than vendor alternatives.

## The Path Forward

The choice is "between going fast only to go slow later, or going slow to go fast later." Vendor tools get you to basic visibility quickly, but they can't scale beyond that without vendor lock-in and escalating costs.

We're choosing the second path: building the foundation that lets you scale infinitely while maintaining technical ownership of your finops practice. FOCUS gives us the standardized foundation, open source tools give us the implementation power, and this series gives us the roadmap.

The finops vendor tax ends here. Let's build something better.

---

*The code and configurations from this series will be available in the [open-finops-stack](https://github.com/JGrubb/open-finops-stack) repository. Star it now and follow along as we build the alternative the industry needs.*