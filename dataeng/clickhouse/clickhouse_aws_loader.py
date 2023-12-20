import json
import os
import re
import time
from dateutil import parser
import shutil

import boto3
import botocore.exceptions as botoexceptions

from clickhouse_connect.driver.tools import insert_file

from clickhouse_client import create_client

from clickhouse.schema_handling import (
    create_aws_table,
    align_schemas,
    drop_partition,
    create_aws_state_table,
)


def fetch_all_manifests():
    """
    Fetches all manifests based in the configured report directories and returns them in sorted order.

    Returns:
        list: A list of file paths representing the manifests.
    """
    manifests = []
    pattern = r"[a-z\-\d]+-Manifest\.json"
    for root, dirs, files in os.walk(os.getenv("OFS_STORAGE_DIR")):
        for file in files:
            if re.match(pattern, file):
                manifests.append(os.path.join(root, file))
    return sorted(manifests)


def load_manifest(file):
    """
    Load a JSON manifest file.

    Args:
        file (str): The path to the manifest file.

    Returns:
        dict: The loaded manifest as a dictionary.
    """
    with open(file, "r") as f:
        manifest = json.load(f)
    return manifest


def parse_columns(manifest):
    """
    Parses the columns from the given manifest and returns a list of dictionaries
    containing the column name and its corresponding type.  This maps AWS CUR types to
    Clickhouse equivalents.

    Note: Early versions of the manifest did not include the type of the column, so we
    provide a default of "String" if the type is not found.

    Args:
        manifest (dict): The manifest containing the columns.

    Returns:
        list: A list of dictionaries, where each dictionary contains the name and type
        of a column.
    """
    type_mapping = {
        "String": "String",
        "Interval": "String",
        "DateTime": "DateTime",
        "Decimal": "Decimal(20, 8)",
        "BigDecimal": "Decimal(20, 8)",
        "OptionalBigDecimal": "Decimal(20, 8)",
        "OptionalString": "String",
    }
    types = []
    for column in manifest["columns"]:
        name = f"{column['category']}_{re.sub(':', '_', column['name'])}"
        typeis = type_mapping.get(column.get("type"), "String")
        types.append(
            {
                "name": name,
                "type": typeis,
            }
        )
    return types


def download_files(manifest):
    """
    Download files from an S3 bucket based on the given manifest.

    Args:
        manifest (dict): The manifest containing the report keys.

    Returns:
        None
    """
    tmp_dir = f"{os.getenv('OFS_STORAGE_DIR')}/tmp"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    resource = boto3.resource(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    bucket = resource.Bucket(os.getenv("OFS_CUR_BUCKET"))
    for f in manifest["reportKeys"]:
        os.makedirs(
            os.path.dirname(f"{tmp_dir}/{f}"),
            exist_ok=True,
        )
        try:
            print(f"Downloading {f}")
            bucket.download_file(
                f,
                f"{tmp_dir}/{f}",
            )
        except botoexceptions.ClientError as e:
            # this is a hack to get around the fact that the complete path
            # to the file is not in the manifest prior to June 2019
            print(f"Error downloading {f} - trying again with prefix")
            bucket.download_file(
                f"{os.getenv('OFS_S3_PATH_PREFIX') + f}",
                f"{tmp_dir}/{f}",
            )


def load_month(manifest, columns):
    """
    Loads data for a specific month into ClickHouse.

    Args:
        manifest (dict): The manifest containing information about the data to be loaded.
        columns (list): The list of columns for the ClickHouse table.

    Returns:
        None
    """
    client = create_client()
    schema_string = ", ".join([f"{item['name']} {item['type']}" for item in columns])
    partition = int(parser.parse(manifest["billingPeriod"]["start"]).strftime("%Y%m"))

    create_aws_table(client, schema_string)
    align_schemas(client, columns)
    drop_partition(client, partition)

    for f in manifest["reportKeys"]:
        file_path = f"{os.getenv('OFS_STORAGE_DIR')}/tmp/{f}"
        load_file(file_path, columns)
    time.sleep(
        300
    )  # if we give it a few minutes, Clickhouse will compress the data and we can save some space


def load_file(file_path, columns):
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
    settings = {
        "input_format_csv_skip_first_lines": 1,
        "date_time_input_format": "best_effort",
        "session_timezone": "UTC",
    }
    try:
        insert_file(
            client=client,
            table="aws",
            file_path=file_path,
            column_names=[column["name"] for column in columns],
            settings=settings,
        )
    except Exception as e:
        print(e)
        time.sleep(10)
        load_file(file_path, columns)


def do_we_load_it(manifest):
    """
    Checks if the given manifest should be loaded into ClickHouse.  This is determined
    by checking the start date of the billing period against the configured ingest_start_date.

    Next we check to see if the assembly_id represented by the manifest has already been loaded
    for the given billing period.  If it has, we don't need to load it again.

    Args:
        manifest (dict): The manifest data.

    Returns:
        bool: True if the manifest should be loaded, False otherwise.
    """
    start_date = parser.parse(manifest["billingPeriod"]["start"])
    if start_date < parser.parse(
        os.getenv("OFS_INGEST_START_DATE", "2023-01-01 00:00:00Z")
    ):
        print(f"Skipping {start_date}")
        return False
    client = create_client()
    # if the statement below returns a row, we've already loaded this month
    create_aws_state_table(client)

    result = client.command(
        f"""
        SELECT 1 FROM aws_state WHERE assembly_id = '{manifest['assemblyId']}' AND billing_month = toDateTime('{start_date.strftime("%Y-%m-%d %H:%M:%S")}')
    """
    )
    if result == 1:
        print(
            f"Skipping manifest {manifest['assemblyId']} for {start_date} - already loaded"
        )
        return False
    return True


def update_state(manifest):
    """
    Update the state in the AWS table to reflect that a given manifest's assembly_id has been loaded.

    Args:
        manifest (dict): The manifest containing the billing period start, assembly ID, and current timestamp.

    Returns:
        None
    """
    client = client = create_client()
    try:
        client.query(
            f"""
            INSERT INTO aws_state
            VALUES (
                toDateTime('{parser.parse(manifest["billingPeriod"]["start"]).strftime("%Y-%m-%d %H:%M:%S")}'),
                '{manifest['assemblyId']}',
                now()
            )
        """
        )
    except Exception as e:
        print(e)


def cleanup():
    tmp_dir = f"{os.getenv('OFS_STORAGE_DIR')}/tmp"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    manifests = fetch_all_manifests()
    for manifest in manifests:
        definition = load_manifest(manifest)
        if do_we_load_it(definition) == False:
            continue
        columns = parse_columns(definition)
        download_files(definition)
        load_month(definition, columns)
        update_state(definition)
        cleanup()
