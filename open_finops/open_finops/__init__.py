import datetime
import pytz

import dateparser
from pydantic import BaseModel

import duckdb
from clickhouse.clickhouse_client import create_client


class Column(BaseModel):
    """
    The column object, represents an individual column of the manifest's
    data files/schema.

    Attributes:
        name (str): The name of the column.
        type (str): The type of the column.
    """

    name: str
    type: str


class ManifestObject(BaseModel):
    """
    The manifest object.

    Attributes:
        billing_period (datetime): The start of the billing period.
        execution_id (str): The assembly ID, a unique ID on the billing export run.
        data_files (list): The list of data files in the manifest.
        columns (list): A list of name:type pairs.
        vendor (str): The vendor name.
        version (str): The version of the manifest.
    """

    billing_period: datetime.datetime
    execution_id: str
    data_files: list[str]
    columns: list[Column]
    vendor: str
    version: str


def parse_date_str(date_str: str):
    date_object = dateparser.parse(date_str).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=pytz.UTC
    )
    return date_object


def do_we_load_it(manifest: ManifestObject, **kwargs):
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
    if kwargs.get("start_date") and manifest.billing_period < kwargs["start_date"]:
        print(
            f"Skipping {manifest.billing_period}: before configured start date of {kwargs['start_date']}"
        )
        return False

    # If the manifest represents a billing period from after the configured end date, skip it
    if kwargs.get("end_date") and manifest.billing_period >= kwargs["end_date"]:
        print(
            f"Skipping {manifest.billing_period}: after configured end date of {kwargs['end_date']}"
        )
        return False

    # If the manifest represents a billing period that has already been loaded, skip it
    client = create_client()

    result = client.query(
        f"""
        SELECT 1 FROM {manifest.vendor}_state_{manifest.version} 
          WHERE execution_id = '{manifest.execution_id}' 
          AND billing_month = toDateTime('{manifest.billing_period.strftime("%Y-%m-%d %H:%M:%S")}')"""
    )
    if int(result.summary["result_rows"]) != 0:
        print(
            f"Skipping manifest {manifest.execution_id} for {manifest.billing_period} - already loaded"
        )
        return False
    print(
        f"{manifest.vendor} manifest {manifest.execution_id} for {manifest.billing_period} has not been loaded"
    )
    return True


def update_state(manifest: ManifestObject):
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
            INSERT INTO {manifest.vendor}_state_{manifest.version}
            VALUES (
                toDateTime('{manifest.billing_period.strftime("%Y-%m-%d %H:%M:%S")}'),
                '{manifest.execution_id}',
                now()
            )
        """
        )
    except Exception as e:
        print(e)


def extract_schema(file_path):
    """
    Extract the schema from a file. Uses duckdb to call DESCRIBE on the file, typically
    a Parquet file, but could theoretically be anything that Duck can eat.

    Args:
        file_path (str): The path to the file.

    Returns:
        list: The schema of the file.
    """
    with duckdb.connect() as con:
        results = con.sql(f"DESCRIBE SELECT * from '{file_path}'").fetchall()
        columns = [Column(name=result[0], type=result[1]) for result in results]
        con.close()
    return columns
