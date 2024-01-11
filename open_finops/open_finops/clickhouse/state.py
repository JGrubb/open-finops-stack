import pytz

import dateutil.parser as date_parser
import clickhouse.clickhouse_client
import clickhouse.schema_handler


def do_we_load_it(manifest: dict, config: dict):
    """
    Determine if we should load the given manifest.  Three things to check in this order:
    - The ingest_start_date variable is set and the manifest's start date is after it.
    - The ingest_end_date is set and the manifest's end date is before it.
    - The billing_month in scope for that manifest has already been loaded into the aws_state table.

    Unfortunately the v2 CUR doesn't contain the billing month, so we have to use the file path to determine it.

    Args:
        manifest (dict): The manifest containing the report keys.
        file_path (str): The path to the file, this (unfortunately) contains useful information.

    Returns:
        bool: True if we should load the manifest, False otherwise.
    """
    if manifest["billing_period"] < config["start_date"].replace(tzinfo=pytz.UTC):
        print(
            f"Skipping {manifest['billing_period']}: before configured start date of {config['start_date']}"
        )
        return False

    # If the manifest represents a billing period from after the configured end date, skip it
    if config["end_date"] is not None and manifest["billing_period"] >= config[
        "end_date"
    ].replace(tzinfo=pytz.UTC):
        print(
            f"Skipping {manifest['billing_period']}: after configured end date of {end_date}"
        )
        return False

    # If the manifest represents a billing period that has already been loaded, skip it
    client = clickhouse.clickhouse_client.create_client()
    schema_handler = clickhouse.schema_handler.SchemaHandler(client)
    schema_handler.create_aws_state_table(config["cur_version"])

    result = client.command(
        f"""
        SELECT 1 FROM aws_state_{config['cur_version']} 
          WHERE execution_id = '{manifest['execution_id']}' 
          AND billing_month = toDateTime('{manifest['billing_period'].strftime("%Y-%m-%d %H:%M:%S")}')"""
    )
    if result == 1:
        print(
            f"Skipping manifest {manifest['execution_id']} for {manifest['billing_period']} - already loaded"
        )
        return False
    return True
