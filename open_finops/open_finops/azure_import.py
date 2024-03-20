import argparse
import datetime

from azure_ofs import AzureBlobStorageClient

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

args = parser.parse_args()

print(args)

client = AzureBlobStorageClient(
    storage_container=args.storage_container,
    storage_directory=args.storage_directory,
    export_version=args.export_version,
    partitioned=args.partitioned,
)

if args.partitioned:
    objects = client.list_objects(prefix=f"{args.storage_directory}/{args.export_name}")
    print(objects)
