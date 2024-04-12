import argparse
import json
import datetime

from aws_ofs import Aws_v1, Aws_v2, AWSSchemaSetup
from aws_ofs.manifest_normalizer import AWSManifestNormalizer
from open_finops import do_we_load_it, update_state, parse_date_str
from clickhouse.schema_handler import AwsSchemaHandler
from clickhouse import load_file

# Create the parser
parser = argparse.ArgumentParser(description="AWS FinOps")

# Add the arguments
parser.add_argument(
    "--bucket",
    "-b",
    type=str,
    help="The S3 bucket name",
)
parser.add_argument(
    "--prefix",
    "-p",
    type=str,
    help="The S3 bucket prefix",
)
parser.add_argument(
    "--export_name",
    "-e",
    type=str,
    help="The export name",
)

parser.add_argument(
    "--cur_version",
    "-v",
    type=str,
    help="The version to import",
    choices=["v1", "v2"],
    default="v1",
)

parser.add_argument(
    "--export_format", type=str, help="The export format", choices=["csv", "parquet"]
)

parser.add_argument(
    "--start_date",
    type=parse_date_str,
    help="The start date for the import in the format YYYY-MM",
)

parser.add_argument(
    "--end_date",
    type=parse_date_str,
    help="The end date for the import in the format YYYY-MM",
)

parser.add_argument(
    "--reset",
    action="store_true",
    help="Drops all tables and starts over",
)

# Parse the arguments
args = parser.parse_args()
if args.reset:
    AwsSchemaHandler(args.cur_version).reset()
    raise SystemExit


# set up the tables if this is a fresh install
AWSSchemaSetup(args.cur_version).setup()

# fetch the manifest files
if args.cur_version == "v1":
    aws = Aws_v1(args.bucket, args.prefix, args.export_name)
else:
    aws = Aws_v2(args.bucket, args.prefix, args.export_name)
aws.main()

for path in aws.manifest_paths:
    with open(path, "r") as f:
        manifest = json.load(f)
        manifest = AWSManifestNormalizer(manifest, args.cur_version, path).normalize()
        if not do_we_load_it(
            manifest,
            start_date=args.start_date,
            end_date=args.end_date,
        ):
            continue
        local_files = aws.download_billing_files(manifest)
        schema_handler = AwsSchemaHandler(args.cur_version)
        schema_handler.align_schemas(manifest.columns)
        schema_handler.drop_partition(manifest.billing_period)
        for local_file in local_files:
            load_file(manifest, local_file)
        update_state(manifest)
        print(f"Loaded {manifest.billing_period}")
