import json
import os
import re
import glob
from dateutil import parser
import shutil

import boto3
import botocore.exceptions as botoexceptions

import clickhouse_connect
from clickhouse_connect.driver.tools import insert_file

from utils.configurator import Config
from dataeng.clickhouse.schema_handling import (
    create_aws_table,
    align_schemas,
    drop_partition,
    create_aws_state_table,
)

config = Config("config.toml")


def fetch_all_manifests():
    manifests = []
    for path in config.get("settings.report_dirs"):
        pattern = f"**/{path}-Manifest.json"
        glob_path = f"{config.get('settings.project_dir')}/{config.get('settings.storage_dir')}/{config.get('settings.cur_prefix')}/{pattern}"
        for manifest in glob.glob(
            glob_path,
            recursive=True,
        ):
            manifests.append(manifest)
    return sorted(manifests)


def load_manifest(file):
    with open(file, "r") as f:
        manifest = json.load(f)
    return manifest


def parse_columns(manifest):
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
    tmp_dir = (
        f"{config.get('settings.project_dir')}/{config.get('settings.storage_dir')}/tmp"
    )
    shutil.rmtree(tmp_dir)
    resource = boto3.resource("s3")
    bucket = resource.Bucket(config.get("settings.cur_bucket"))
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
                f"{config.get('settings.cur_prefix') + f}",
                f"{tmp_dir}/{f}",
            )


def load_month(manifest, columns):
    client = clickhouse_connect.get_client(host="localhost", username="default")
    schema_string = ", ".join([f"{item['name']} {item['type']}" for item in columns])
    partition = int(parser.parse(manifest["billingPeriod"]["start"]).strftime("%Y%m"))

    create_aws_table(client, schema_string)
    align_schemas(client, columns)
    drop_partition(client, partition)

    for f in manifest["reportKeys"]:
        print(f"Loading {f}")
        settings = {
            "input_format_csv_skip_first_lines": 1,
            "date_time_input_format": "best_effort",
            "session_timezone": "UTC",
        }
        # parameters = {
        #     "access_key_id": config["settings"]["aws_access_key_id"],
        #     "secret_access_key": config["settings"]["aws_secret_access_key"],
        #     "s3_file_path": f"s3://{config['settings']['cur_bucket']}/{f}",
        # }
        # client.command(
        #     """
        # INSERT INTO aws
        # SELECT * FROM s3(
        #                 %(s3_file_path)s,
        #                 %(access_key_id)s,
        #                 %(secret_access_key)s,
        #                 'CSVWithNames'
        # )
        # """,
        #     parameters=parameters,
        #     settings=settings,
        # )

        insert_file(
            client=client,
            table="aws",
            file_path=f"{config['settings']['project_dir']}/{config['settings']['storage_dir']}/tmp/{f}",
            column_names=[column["name"] for column in columns],
            settings=settings,
        )
    update_state(manifest)


def do_we_load_it(manifest):
    start_date = parser.parse(manifest["billingPeriod"]["start"])
    if start_date < config.get("settings.ingest_start_date"):
        print(f"Skipping {start_date}")
        return False
    client = clickhouse_connect.get_client(host="localhost", username="default")
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
    client = clickhouse_connect.get_client(host="localhost", username="default")
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


if __name__ == "__main__":
    manifests = fetch_all_manifests()
    for manifest in manifests:
        definition = load_manifest(manifest)
        if do_we_load_it(definition) == False:
            continue
        columns = parse_columns(definition)
        download_files(definition)
        load_month(definition, columns)
