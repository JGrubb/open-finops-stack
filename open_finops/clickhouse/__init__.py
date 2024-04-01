import time
import pytz

from clickhouse.clickhouse_client import create_client
from clickhouse_connect.driver.tools import insert_file


def do_we_load_it(manifest: dict, **kwargs):
    """
    Determines whether to load a manifest based on the provided start and end dates.

    Args:
        manifest (dict): The manifest to be evaluated.
        **kwargs: Additional keyword arguments.
            - start_date (datetime): The start date for loading manifests.
            - end_date (datetime): The end date for loading manifests.
            - cur_version (str): The current version.

    Returns:
        bool: True if the manifest should be loaded, False otherwise.
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


def load_file(manifest: dict, file_path: str):
    """
    Loads a file into ClickHouse database.

    Args:
        manifestm (dict): The version of the data.
        file_path (str): The path to the file to be loaded.

    Returns:
        None
    """

    client = create_client()

    print(f"Loading {file_path}")
    try:
        if file_path.endswith((".csv.gz", ".csv")):
            settings = {
                "date_time_input_format": "best_effort",
                "input_format_csv_skip_first_lines": 1,
                "session_timezone": "UTC",
            }
            insert_file(
                client=client,
                table=f"{manifest.vendor}_data_{manifest.version}",
                file_path=file_path,
                column_names=[column["name"] for column in manifest.columns],
                settings=settings,
            )
        elif file_path.endswith(".parquet"):
            settings = {
                "date_time_input_format": "best_effort",
                "input_format_parquet_allow_missing_columns": "true",
                "session_timezone": "UTC",
            }
            insert_file(
                client=client,
                table=f"{manifest.vendor}_data_{manifest.version}",
                file_path=file_path,
                fmt="Parquet",
                settings=settings,
            )
    except Exception as e:
        print(e)  # not this is not pretty and should be improved
        raise
