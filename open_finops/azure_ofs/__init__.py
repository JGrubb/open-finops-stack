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
        self, storage_container, storage_directory, export_name, partitioned=False
    ):
        self.storage_client = AzureBlobStorageClient(
            storage_container, storage_directory
        )
        self.storage_directory = storage_directory
        self.export_name = export_name
        self.partitioned = partitioned
        self.file_paths = []
        self.manifests = []

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
        return month_dirs

    def get_most_recent_for_month(self, month):
        self.file_paths.append(
            self.storage_client.get_most_recent_object(
                f"{self.storage_directory}/{self.export_name}/{month}"
            )
        )

    def build_manifests(self):
        for file_path in self.file_paths:
            if self.partitioned:
                directory = file_path.rsplit("/", 1)[0]
                data_files = self.storage_client.list_objects(
                    prefix=directory, suffix=(".csv", ".csv.gz")
                )
                manifest = {
                    "billing_period": dateutil.parser.parse(
                        file_path.split("/")[2].split("-")[0]
                    ).replace(day=1),
                    "execution_id": file_path.split("/")[-2],
                    "data_files": data_files,
                }

            else:
                manifest = {
                    "billing_period": dateutil.parser.parse(
                        file_path.split("/")[-2].split("-")[0]
                    ).replace(day=1),
                    "execution_id": file_path.split("_")[1].split(".")[0],
                    "data_files": [file_path],
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
        for data_file in manifest["data_files"]:
            destination_path = f"storage/tmp/azure/{data_file.split('/')[-1]}"
            self.storage_client.download_object(data_file, destination_path)
            local_files.append(destination_path)
        return local_files
