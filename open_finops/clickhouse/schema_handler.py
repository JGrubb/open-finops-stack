from clickhouse.clickhouse_client import create_client


class SchemaHandler:
    def __init__(self):
        self.client = create_client()


class AwsSchemaHandler(SchemaHandler):

    def __init__(self, cur_version: str):
        super().__init__()
        self.cur_version = cur_version
        if cur_version == "v1":
            self.partition_column = "bill_BillingPeriodStartDate"
            self.ordering_column = "lineItem_UsageStartDate"
        else:  # cur_version == "v2"
            self.partition_column = "bill_billing_period_start_date"
            self.ordering_column = "line_item_usage_start_date"

    def create_aws_data_table(
        self,
    ):
        self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS aws_data_{self.cur_version}
            (
                {self.partition_column} DateTime,
                {self.ordering_column} DateTime
            )
            ENGINE = MergeTree
            ORDER BY {self.ordering_column}
            PARTITION BY toYYYYMM({self.partition_column})
            """
        )

    def create_aws_state_table(self):
        result = self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS aws_state_{self.cur_version}
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

    def align_schemas(self, columns: list):
        for column in columns:
            self.client.command(
                f"ALTER TABLE aws_data_{self.cur_version} ADD COLUMN IF NOT EXISTS {column['name']} {column['type']}"
            )

    def drop_partition(self, billing_period: str):
        partition_label = billing_period.strftime("%Y%m")
        results = self.client.command(
            f"""
            SELECT count(*) FROM aws_data_{self.cur_version} WHERE toYYYYMM({self.partition_column}) = '{partition_label}'
            """
        )
        if results == 0:
            print(f"Partition {partition_label} does not exist")
            return None
        print(f"Dropping partition {partition_label}")
        self.client.command(
            f"""
            ALTER TABLE aws_data_{self.cur_version} DROP PARTITION '{partition_label}'
            """
        )
