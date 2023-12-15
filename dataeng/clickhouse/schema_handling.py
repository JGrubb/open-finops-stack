def create_aws_table(client, schema_string: str):
    client.command(
        f"""
        CREATE TABLE IF NOT EXISTS default.aws
        (
            {schema_string}
        )
        ENGINE = MergeTree
        ORDER BY lineItem_UsageStartDate
        PARTITION BY toYYYYMM(bill_BillingPeriodStartDate)
        """
    )


def create_aws_state_table(client):
    client.command(
        f"""
        CREATE TABLE IF NOT EXISTS default.aws_state
        (
            billing_month DateTime,
            assembly_id String,
            loaded_at DateTime,
        )
        ENGINE = MergeTree
        ORDER BY billing_month
        """
    )


def align_schemas(client, columns: list):
    for column in columns:
        client.command(
            f"ALTER TABLE aws ADD COLUMN IF NOT EXISTS {column['name']} {column['type']}"
        )


def drop_partition(client, partition: str):
    client.command(
        f"""
        ALTER TABLE aws DROP PARTITION {partition}
        """
    )
