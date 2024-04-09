from clickhouse.clickhouse_client import create_client
from clickhouse_connect.driver.tools import insert_file


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
                column_names=[column.name for column in manifest.columns],
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
        raise SystemExit
