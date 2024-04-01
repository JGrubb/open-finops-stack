import argparse
import datetime

from open_finops import do_we_load_it, update_state
from azure_ofs import AzureSchemaSetup, AzureHandler, AzureSchemaHandler
from clickhouse import load_file

# Create the parser
parser = argparse.ArgumentParser(description="Azure FinOps")
parser.add_argument(
    "--storage_container",
    type=str,
    help="The storage container name, set in the Azure billing export config",
    required=True,
)

parser.add_argument(
    "--storage_directory",
    type=str,
    help="The storage directory in the container, set in the Azure billing export config",
    required=True,
)

parser.add_argument(
    "--export_name",
    type=str,
    help="The export name",
    required=True,
)

parser.add_argument(
    "--export_version",
    type=str,
    help="The export version - Amortized or Actual",
    choices=["actual", "amortized"],
    default="amortized",
)

parser.add_argument(
    "--partitioned",
    action="store_true",
    help="Whether the billing export is partitioned",
)

parser.add_argument(
    "--start_date",
    type=lambda s: datetime.datetime.strptime(s, "%Y-%m"),
    help="The start date for the import in the format YYYY-MM",
)

parser.add_argument(
    "--end_date",
    type=lambda s: datetime.datetime.strptime(s, "%Y-%m"),
    help="The end date for the import in the format YYYY-MM",
)

parser.add_argument(
    "--mock",
    action="store_true",
    help="Loads local data instead of the whole pipeline",
)

args = parser.parse_args()

AzureSchemaSetup(args.export_version).setup()

handler = AzureHandler(
    args.storage_container,
    args.storage_directory,
    args.export_name,
    args.export_version,
    partitioned=args.partitioned,
)

manifests = handler.main()

for manifest in manifests:
    if not args.mock and not do_we_load_it(
        manifest,
        start_date=args.start_date,
        end_date=args.end_date,
    ):
        continue
    local_files = handler.download_datafiles(manifest)
    manifest.columns = extract_schema(local_files[0])
    schema_handler = AzureSchemaHandler(args.export_version)
    schema_handler.align_schemas(manifest.columns)
    schema_handler.drop_partition(manifest.billing_period)
    for local_file in local_files:
        load_file(manifest, local_file)
    update_state(manifest)
    print(f"Loaded {manifest['billing_period']}")
