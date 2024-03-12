import time
import pytz

from clickhouse.clickhouse_client import create_client
from clickhouse_connect.driver.tools import insert_file


def do_we_load_it(manifest: dict, **kwargs):
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
        SELECT 1 FROM aws_state_{kwargs.get("cur_version")} 
          WHERE execution_id = '{manifest['execution_id']}' 
          AND billing_month = toDateTime('{manifest['billing_period'].strftime("%Y-%m-%d %H:%M:%S")}')"""
    )
    if result == 1:
        print(
            f"Skipping manifest {manifest['execution_id']} for {manifest['billing_period']} - already loaded"
        )
        return False
    return True


def load_file(version, file_path, columns):
    """
    Loads a single file into ClickHouse.

    Args:
        file (str): The path to the file to be loaded.
        columns (list): The list of columns for the ClickHouse table.

    Returns:
        None
    """
    client = create_client()

    print(f"Loading {file_path}")
    try:
        if file_path.endswith(".csv.gz"):
            settings = {
                "input_format_csv_skip_first_lines": 1,
                "date_time_input_format": "best_effort",
                "session_timezone": "UTC",
            }
            insert_file(
                client=client,
                table=f"aws_data_{version}",
                file_path=file_path,
                column_names=[column["name"] for column in columns],
                settings=settings,
            )
        elif file_path.endswith(".parquet"):
            settings = {
                "date_time_input_format": "best_effort",
                "session_timezone": "UTC",
            }
            insert_file(
                client=client,
                table=f"aws_data_{version}",
                file_path=file_path,
                fmt="Parquet",
                settings=settings,
            )
    except Exception as e:
        print(e)  # not this is not pretty and should be improved
        time.sleep(10)
        load_file(file_path, columns)
