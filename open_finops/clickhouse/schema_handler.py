import datetime

from clickhouse.clickhouse_client import create_client


class SchemaHandler:
    def __init__(self):
        self.client = create_client()
        self.vendor = None
        self.version = None

    def create_data_table(self):
        self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS {self.vendor}_data_{self.version}
            (
                {self.partition_column} DateTime,
                {self.ordering_column} DateTime
            )
            ENGINE = MergeTree
            ORDER BY {self.ordering_column}
            PARTITION BY toYYYYMM({self.partition_column})
            """
        )

    def create_state_table(self):
        self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS {self.vendor}_state_{self.version}
            (
                billing_month DateTime,
                execution_id String,
                loaded_at DateTime
            )
            ENGINE = MergeTree
            ORDER BY billing_month
            """
        )

    def align_schemas(self, columns: list):
        for column in columns:
            self.client.command(
                f"ALTER TABLE {self.vendor}_data_{self.version} ADD COLUMN IF NOT EXISTS {column['name']} {column['type']}"
            )

    def drop_partition(self, billing_period: datetime.datetime):
        partition_label = billing_period.strftime("%Y%m")
        results = self.client.command(
            f"""
            SELECT count(*) FROM {self.vendor}_data_{self.version} WHERE toYYYYMM({self.partition_column}) = '{partition_label}'
            """
        )
        if results == 0:
            print(f"Partition {partition_label} does not exist")
            return None
        print(f"Dropping partition {partition_label}")
        self.client.command(
            f"""
            ALTER TABLE {self.vendor}_data_{self.version} DROP PARTITION '{partition_label}'
            """
        )


class AwsSchemaHandler(SchemaHandler):

    def __init__(self, cur_version: str):
        super().__init__()
        self.version = cur_version
        self.vendor = "aws"
        if cur_version == "v1":
            self.partition_column = "bill_BillingPeriodStartDate"
            self.ordering_column = "lineItem_UsageStartDate"
        else:  # cur_version == "v2"
            self.partition_column = "bill_billing_period_start_date"
            self.ordering_column = "line_item_usage_start_date"


class AzureSchemaHandler(SchemaHandler):

    def __init__(self, export_version: str):
        super().__init__()
        self.version = export_version
        self.vendor = "azure"
        self.partition_column = "BillingPeriodStartDate"
        self.ordering_column = "Date"
