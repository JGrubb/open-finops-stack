class SchemaHandler:
    def __init__(self, client):
        self.client = client

    def create_aws_table(
        self,
        cur_version: str,
        columns: list,
    ):
        schema_string = ",".join(
            [f"{column['name']} {column['type']}" for column in columns]
        )
        self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS aws_{cur_version}
            (
                {schema_string}
            )
            ENGINE = MergeTree
            ORDER BY lineItem_UsageStartDate
            PARTITION BY toYYYYMM(bill_BillingPeriodStartDate)
            """
        )

    def create_aws_state_table(self, cur_version: str):
        result = self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS aws_state_{cur_version}
            (
                billing_month DateTime,
                execution_id String,
                loaded_at DateTime,
            )
            ENGINE = MergeTree
            ORDER BY billing_month
            """
        )
        return None

    def align_schemas(self, columns: list, cur_version: str):
        if cur_version == "v2":
            return None
        for column in columns:
            self.client.command(
                f"ALTER TABLE aws_{cur_version} ADD COLUMN IF NOT EXISTS {column['name']} {column['type']}"
            )

    def drop_partition(self, billing_period: str, cur_version: str):
        self.client.command(
            f"""
            ALTER TABLE aws_{cur_version} DROP PARTITION toYYYYMM({billing_period})
            """
        )
