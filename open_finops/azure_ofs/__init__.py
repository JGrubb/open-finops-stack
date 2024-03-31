import os
import shutil

import dateutil.parser
from tqdm import tqdm
import duckdb
import pytz

from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from clickhouse.schema_handler import AzureSchemaHandler


class AzureSchemaSetup:
    def __init__(self, version: str):
        self.schema_handler = AzureSchemaHandler(version)
        self.version = version

    def setup(self):
        self.schema_handler.create_state_table()
        self.schema_handler.create_data_table()


class AzureBlobStorageClient:
    def __init__(
        self, storage_container=None, storage_directory=None, credential_file=None
    ):
        self.storage_container = storage_container
        self.storage_directory = storage_directory
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if self.connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
        elif credential_file:
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient.from_connection_string(
                credential_file, credential
            )
        else:
            raise ValueError(
                "Either connection_string or credential_file must be provided."
            )
        self.container_client = self.blob_service_client.get_container_client(
            self.storage_container
        )

    def list_objects(self, prefix=None, suffix=None):
        blob_list = self.container_client.list_blobs(name_starts_with=prefix)
        if suffix:
            return [blob.name for blob in blob_list if blob.name.endswith(suffix)]
        else:
            return [blob.name for blob in blob_list]

    def download_object(self, blob_name, destination_path):
        blob_client = self.container_client.get_blob_client(blob_name)
        filesize = blob_client.get_blob_properties().size
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        with open(destination_path, "ab") as file, tqdm(
            total=filesize,
            unit="B",
            unit_scale=True,
            desc=destination_path.split("/")[-1],
            colour="green",
        ) as t:
            bytes_read = 0

            def update_progress(bytes_amount, *args):
                nonlocal bytes_read
                t.update(bytes_amount - bytes_read)
                bytes_read = bytes_amount

            blob_data = blob_client.download_blob(progress_hook=update_progress)
            file.write(blob_data.readall())
            t.close()

    def get_most_recent_object(self, prefix=None):
        blob_list = self.container_client.list_blobs(name_starts_with=prefix)
        most_recent_blob = max(blob_list, key=lambda blob: blob.last_modified)
        return most_recent_blob.name


class AzureHandler:
    def __init__(
        self,
        storage_container,
        storage_directory,
        export_name,
        export_version,
        partitioned=False,
    ):
        self.storage_client = AzureBlobStorageClient(
            storage_container, storage_directory
        )
        self.storage_directory = storage_directory
        self.export_name = export_name
        self.partitioned = partitioned
        self.version = export_version
        self.file_paths = []
        self.manifests = []
        self.columns = [
            {"name": "InvoiceSectionName", "type": "VARCHAR"},
            {"name": "AccountName", "type": "VARCHAR"},
            {"name": "AccountOwnerId", "type": "VARCHAR"},
            {"name": "SubscriptionId", "type": "VARCHAR"},
            {"name": "SubscriptionName", "type": "VARCHAR"},
            {"name": "ResourceGroup", "type": "VARCHAR"},
            {"name": "ResourceLocation", "type": "VARCHAR"},
            {"name": "Date", "type": "DATE"},
            {"name": "ProductName", "type": "VARCHAR"},
            {"name": "MeterCategory", "type": "VARCHAR"},
            {"name": "MeterSubCategory", "type": "VARCHAR"},
            {"name": "MeterId", "type": "VARCHAR"},
            {"name": "MeterName", "type": "VARCHAR"},
            {"name": "MeterRegion", "type": "VARCHAR"},
            {"name": "UnitOfMeasure", "type": "VARCHAR"},
            {"name": "Quantity", "type": "DOUBLE"},
            {"name": "EffectivePrice", "type": "DOUBLE"},
            {"name": "CostInBillingCurrency", "type": "DOUBLE"},
            {"name": "CostCenter", "type": "VARCHAR"},
            {"name": "ConsumedService", "type": "VARCHAR"},
            {"name": "ResourceId", "type": "VARCHAR"},
            {"name": "Tags", "type": "VARCHAR"},
            {"name": "OfferId", "type": "VARCHAR"},
            {"name": "AdditionalInfo", "type": "VARCHAR"},
            {"name": "ServiceInfo1", "type": "VARCHAR"},
            {"name": "ServiceInfo2", "type": "VARCHAR"},
            {"name": "ResourceName", "type": "VARCHAR"},
            {"name": "ReservationId", "type": "VARCHAR"},
            {"name": "ReservationName", "type": "VARCHAR"},
            {"name": "UnitPrice", "type": "DOUBLE"},
            {"name": "ProductOrderId", "type": "VARCHAR"},
            {"name": "ProductOrderName", "type": "VARCHAR"},
            {"name": "Term", "type": "VARCHAR"},
            {"name": "PublisherType", "type": "VARCHAR"},
            {"name": "PublisherName", "type": "VARCHAR"},
            {"name": "ChargeType", "type": "VARCHAR"},
            {"name": "Frequency", "type": "VARCHAR"},
            {"name": "PricingModel", "type": "VARCHAR"},
            {"name": "AvailabilityZone", "type": "VARCHAR"},
            {"name": "BillingAccountId", "type": "BIGINT"},
            {"name": "BillingAccountName", "type": "VARCHAR"},
            {"name": "BillingCurrencyCode", "type": "VARCHAR"},
            {"name": "BillingPeriodStartDate", "type": "DATE"},
            {"name": "BillingPeriodEndDate", "type": "DATE"},
            {"name": "BillingProfileId", "type": "BIGINT"},
            {"name": "BillingProfileName", "type": "VARCHAR"},
            {"name": "InvoiceSectionId", "type": "VARCHAR"},
            {"name": "IsAzureCreditEligible", "type": "BOOLEAN"},
            {"name": "PartNumber", "type": "VARCHAR"},
            {"name": "PayGPrice", "type": "DOUBLE"},
            {"name": "PlanName", "type": "VARCHAR"},
            {"name": "ServiceFamily", "type": "VARCHAR"},
            {"name": "CostAllocationRuleName", "type": "VARCHAR"},
            {"name": "benefitId", "type": "VARCHAR"},
            {"name": "benefitName", "type": "VARCHAR"},
        ]

    def preclean(self):
        tmp_dir = f"storage/tmp/azure"
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        return None

    def extract_months(self):
        objects = self.storage_client.list_objects(
            f"{self.storage_directory}/{self.export_name}/"
        )
        month_dirs = sorted(
            list(set([obj.split("/")[2] for obj in objects])), reverse=True
        )
        for month in month_dirs:
            print(f"Found month: {month}")
        return month_dirs

    def get_most_recent_for_month(self, month):
        self.file_paths.append(
            self.storage_client.get_most_recent_object(
                f"{self.storage_directory}/{self.export_name}/{month}"
            )
        )

    def build_manifests(self):
        for file_path in self.file_paths:
            # print(f"Building manifest for {file_path}. Partitioned: {self.partitioned}")
            if self.partitioned:
                directory = file_path.rsplit("/", 1)[0]
                data_files = self.storage_client.list_objects(
                    prefix=directory, suffix=(".csv", ".csv.gz")
                )
                manifest = {
                    "billing_period": dateutil.parser.parse(
                        file_path.split("/")[2].split("-")[0]
                    ).replace(day=1, tzinfo=pytz.UTC),
                    "execution_id": file_path.split("/")[-2],
                    "data_files": data_files,
                    "columns": self.columns,
                    "vendor": "azure",
                    "version": self.version,
                }

            else:
                manifest = {
                    "billing_period": dateutil.parser.parse(
                        file_path.split("/")[-2].split("-")[0]
                    ).replace(day=1, tzinfo=pytz.UTC),
                    "execution_id": file_path.split("_")[1].split(".")[0],
                    "data_files": [file_path],
                    "columns": self.columns,
                    "vendor": "azure",
                    "version": self.version,
                }
            self.manifests.append(manifest)

    def main(self):
        self.preclean()
        months = self.extract_months()
        for month in months:
            self.get_most_recent_for_month(month)
        self.build_manifests()
        return self.manifests

    def download_datafiles(self, manifest):
        local_files = []
        # schema_string = (
        #     "("
        #     + ",".join(
        #         [
        #             column["name"] + " " + column["type"]
        #             for column in manifest["columns"]
        #         ]
        #     )
        #     + ")"
        # )
        con = duckdb.connect()
        for data_file in manifest["data_files"]:
            destination_path = f"storage/tmp/azure/{data_file}"
            print(f"Downloading to {destination_path}")
            self.storage_client.download_object(data_file, destination_path)
            local_files.append(destination_path)
            print(f"Downloaded {data_file}")
        dirname = os.path.dirname(local_files[0])
        con.sql(
            f"""CREATE TABLE azure_tmp AS SELECT * FROM read_csv('{dirname}/*.csv', 
                header = true, 
                dateformat = '%m/%d/%Y'
            )"""
        )
        columns = [
            {"name": result[0], "type": result[1]}
            for result in con.sql("DESCRIBE azure_tmp").fetchall()
        ]
        con.sql(
            f"COPY (SELECT * FROM azure_tmp) TO 'storage/tmp/azure/azure-tmp.parquet' (FORMAT 'parquet')"
        )
        con.close()
        return ["storage/tmp/azure/azure-tmp.parquet"], columns
