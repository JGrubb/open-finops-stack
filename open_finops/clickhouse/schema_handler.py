from clickhouse.clickhouse_client import create_client


class SchemaHandler:
    def __init__(self):
        self.client = create_client()

    def create_aws_v1_table(
        self,
    ):
        self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS aws_data_v1
            (
                bill_BillingPeriodStartDate DateTime,
                lineItem_UsageStartDate DateTime
            )
            ENGINE = MergeTree
            ORDER BY lineItem_UsageStartDate
            PARTITION BY toYYYYMM(bill_BillingPeriodStartDate)
            """
        )

    def create_aws_v2_table(self):
        self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS aws_data_v2
            (
                bill_billing_period_start_date DateTime, 
                line_item_usage_start_date DateTime
            )
            ENGINE = MergeTree
            ORDER BY line_item_usage_start_date
            PARTITION BY toYYYYMM(bill_billing_period_start_date)
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
        for column in columns:
            self.client.command(
                f"ALTER TABLE aws_data_{cur_version} ADD COLUMN IF NOT EXISTS {column['name']} {column['type']}"
            )

    def drop_partition(self, billing_period: str, cur_version: str):
        partition_label = billing_period.strftime("%Y%m")
        if cur_version == "v1":
            partition_column = "bill_BillingPeriodStartDate"
        else:  # cur_version == "v2"
            partition_column = "bill_billing_period_start_date"
        results = self.client.command(
            f"""
            SELECT count(*) FROM aws_data_{cur_version} WHERE toYYYYMM({partition_column}) = '{partition_label}'
            """
        )
        if results == 0:
            return None
        self.client.command(
            f"""
            ALTER TABLE aws_data_{cur_version} DROP PARTITION {partition_label})
            """
        )
