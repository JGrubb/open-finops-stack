import argparse
import json

from aws import Aws_v1, Aws_v2
from aws.manifest_normalizer import AWSManifestNormalizer
from open_finops import bootstrap, do_we_load_it, update_state
from clickhouse.schema_handler import SchemaHandler
from clickhouse import load_file

# Create the parser
parser = argparse.ArgumentParser(description="AWS FinOps")

# Add the arguments
parser.add_argument(
    "--bucket",
    type=str,
    help="The S3 bucket name",
    required=True,
)
parser.add_argument(
    "--prefix",
    type=str,
    help="The S3 bucket prefix",
    required=True,
)
parser.add_argument(
    "--export_name",
    type=str,
    help="The export name",
    required=True,
)

parser.add_argument(
    "--cur_version",
    type=str,
    help="The version to import",
    choices=["v1", "v2"],
    default="v1",
)

parser.add_argument(
    "--export_format", type=str, help="The export format", choices=["csv", "parquet"]
)

parser.add_argument(
    "--reset",
    action="store_true",
    help="Drops all data tables and starts over",
)

# Parse the arguments
args = parser.parse_args()

# set up the tables if this is a fresh install
bootstrap()

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
        if not do_we_load_it(manifest, cur_version=args.cur_version):
            continue
        billing_file_paths = aws.download_billing_files(manifest)
        schema_handler = SchemaHandler()
        if manifest["data_files"][0].endswith(".csv.gz"):
            schema_handler.align_schemas(manifest["columns"], args.cur_version)
        schema_handler.drop_partition(manifest["billing_period"], args.cur_version)
        for file in billing_file_paths:
            load_file(args.cur_version, file, manifest["columns"])
        update_state(manifest, args.cur_version)
        print(f"Loaded {manifest['billing_period']}")


print(aws.manifest_paths)
