import os

import clickhouse.clickhouse_client as clickhouse_client
import clickhouse.schema_handler as schema_handler


class ClickHouseLoader:
    def __init__(self, format):
        self.client = clickhouse_client.create_client()
        self.schema_handler = schema_handler.SchemaHandler(self.client)
        self.format = format

    def picker(self, cur_format):
        return {
            "csv": self.load_csv,
            "parquet": self.load_parquet,
        }[cur_format]

    def setup(self, manifest, config):
        self.schema_handler.create_aws_table(config["cur_version"], manifest["columns"])
        self.schema_handler.align_schemas(manifest["columns"], config["cur_version"])
        self.schema_handler.drop_partition(
            manifest["billing_period"], config["cur_version"]
        )

    def load_csv(self, manifest, data_files):
        # TODO: Implement
        pass

    def load_parquet(self, manifest, config):
        # TODO: Implement
        pass

    def load_month(manifest, columns):
        """
        Loads data for a specific month into ClickHouse.

        Args:
            manifest (dict): The manifest containing information about the data to be loaded.
            columns (list): The list of columns for the ClickHouse table.

        Returns:
            None
        """

        for f in manifest["data_files"]:
            file_path = f"{os.getenv('OFS_STORAGE_DIR')}/tmp/{f}"
            load_file(file_path, columns)
