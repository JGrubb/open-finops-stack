What is the open finops stack?

It's a pretty simple idea, it's an open source implementation of basic, cross-cloud FinOps visibility tooling.  It handles the ingestion and normalization of AWS, Azure, and eventually GCP billing data and others into a Clickhouse database (open source columnar, analytics data warehouse). 

Soon it will use DBT to normalize all that data into the FOCUS - finops open cost and usage spec - schema.  Eventually it will merge all of that together into 1 big billing data table, which is the end goal of FOCUS as far as I'm concerned.  This will let practitioners build cost reporting in whatever BI tool they want, but the stack will come with scripts to set up Metabase, which is what we use at my employer.

---

