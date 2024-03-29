import pytz
from clickhouse.schema_handler import AwsSchemaHandler
from clickhouse.clickhouse_client import create_client


class ClickhouseAwsSetup:

    def __init__(self, cur_version: str):
        self.cur_version = cur_version
        self.schema_handler = AwsSchemaHandler(cur_version)

    def main(self):
        self.schema_handler.create_aws_data_table()
        self.schema_handler.create_aws_state_table(self.cur_version)
        return None


def aws_bootstrap(cur_version: str):
    setup = ClickhouseAwsSetup(cur_version)
    setup.main()


def do_we_load_it(manifest: dict, vendor: str, version: str, **kwargs):
    """
    Determine if we should load the given manifest.  Three things to check in this order:
    - The ingest_start_date variable is set and the manifest's start date is on or after it.
    - The ingest_end_date is set and the manifest's start date is before it.
    - The billing_month in scope for that manifest has already been loaded into the aws_state table.

    Unfortunately the v2 CUR doesn't contain the billing month, so we have to use the file path to determine it.

    Args:
        manifest (dict): The manifest containing the report keys.
        file_path (str): The path to the file, this (unfortunately) contains useful information.

    Returns:
        bool: True if we should load the manifest, False otherwise.
    """
    if kwargs.get("start_date") and manifest["billing_period"] < kwargs[
        "start_date"
    ].replace(tzinfo=pytz.UTC):
        print(
            f"Skipping {manifest['billing_period']}: before configured start date of {kwargs['start_date']}"
        )
        return False

    # If the manifest represents a billing period from after the configured end date, skip it
    if kwargs.get("end_date") and manifest["billing_period"] >= kwargs[
        "end_date"
    ].replace(tzinfo=pytz.UTC):
        print(
            f"Skipping {manifest['billing_period']}: after configured end date of {kwargs['end_date']}"
        )
        return False

    # If the manifest represents a billing period that has already been loaded, skip it
    client = create_client()

    result = client.command(
        f"""
        SELECT 1 FROM {vendor}_state_{version} 
          WHERE execution_id = '{manifest['execution_id']}' 
          AND billing_month = toDateTime('{manifest['billing_period'].strftime("%Y-%m-%d %H:%M:%S")}')"""
    )
    if result == 1:
        print(
            f"Skipping manifest {manifest['execution_id']} for {manifest['billing_period']} - already loaded"
        )
        return False
    return True


def update_state(manifest, vendor, version):
    """
    Update the state in the AWS table to reflect that a given manifest's assembly_id has been loaded.

    Args:
        manifest (dict): The manifest containing the billing period start, assembly ID, and current timestamp.

    Returns:
        None
    """
    client = create_client()
    try:
        client.query(
            f"""
            INSERT INTO {vendor}_state_{version}
            VALUES (
                toDateTime('{manifest['billing_period'].strftime("%Y-%m-%d %H:%M:%S")}'),
                '{manifest['execution_id']}',
                now()
            )
        """
        )
    except Exception as e:
        print(e)
