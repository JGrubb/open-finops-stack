import os
import argparse
import json
import datetime

import dateutil.parser as date_parser

from aws.downloader import DataDownloader, refresh_manifests
from aws.manifest_normalizer import AWSManifestNormalizer
import clickhouse.state as state

from clickhouse import ClickHouseLoader

parser = argparse.ArgumentParser(
    prog="AWS loader", description="Load AWS data into ClickHouse"
)


def validate_date(date_text):
    if date_text is not None:
        try:
            return parser.parse(date_text).replace(day=1)
        except ValueError:
            raise argparse.ArgumentTypeError("Invalid date format, must be YYYY-MM")


default_start_date = date_parser.parse(
    os.getenv("OFS_INGEST_START_DATE", "2023-01-01")
).replace(day=1)

parser.add_argument(
    "--start_date",
    help="""Start date for loading AWS data in the format YYYY-MM.  
    Defaults to the value of OFS_INGEST_START_DATE environment variable, or 2023-01 if not set.""",
    type=validate_date,
    default=default_start_date,
)

parser.add_argument(
    "--end_date",
    help="""End date for loading AWS data in the format YYYY-MM.  
    This will likely only be used if you are trying to convert from v1 to v2, or are backfilling
    old data.""",
    type=validate_date,
    default=None,
)

parser.add_argument(
    "--cur-version", help="CUR version to ingest", choices=["v1", "v2"], default="v2"
)
parser.add_argument(
    "-f",
    "--cur-format",
    help="CUR format to ingest",
    choices=["parquet", "csv"],
    default="csv",
)
parser.add_argument(
    "--export-name",
    help="""Name of the AWS billing data export to load.  
    Export names can have up to 128 characters and must be unique. 
    Valid characters are a-z, A-Z, 0-9, - (hyphen), and _ (underscore). 
    Defaults to the value of OFS_CUR_EXPORT_NAME environment variable.""",
    default=os.getenv("OFS_CUR_EXPORT_NAME"),
)

parser.add_argument(
    "--bucket",
    help="Name of the S3 bucket to load data from.  Defaults to the bucket specified in the OFS_CUR_BUCKET environment variable.",
    default=os.getenv("OFS_CUR_BUCKET"),
)

parser.add_argument(
    "--prefix",
    help="Path prefix for the S3 bucket to load data from.  Defaults to the prefix specified in the OFS_CUR_PREFIX environment variable.",
    default=os.getenv("OFS_CUR_PREFIX"),
)

args = parser.parse_args()

cur_config = {
    "bucket_name": args.bucket,
    "prefix": args.prefix,
    "export_name": args.export_name,
}

ingest_config = {
    "start_date": args.start_date,
    "end_date": args.end_date,
    "cur_version": args.cur_version,
    "cur_format": args.cur_format,
}

manifest_paths = refresh_manifests(args.cur_version, cur_config)

for path in manifest_paths:
    manifest = json.load(open(path))
    normalized_manifest = AWSManifestNormalizer(
        manifest, args.cur_version, path
    ).normalize()
    if state.do_we_load_it(normalized_manifest, ingest_config) is False:
        continue
    data_files = DataDownloader(cur_config).download_data(
        normalized_manifest["data_files"]
    )
    ClickHouseLoader(ingest_config).load(normalized_manifest, data_files)
    print(f"Loading {path}")
