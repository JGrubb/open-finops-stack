import os
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from clickhouse.schema_handler import AwsSchemaHandler


class AzureSchemaSetup:
    def __init__(self):
        self.schema_handler = AwsSchemaHandler()

    def setup(self):
        self.schema_handler.create_table("azure_actual_state")
        self.schema_handler.create_table("azure_amortized_state")
        self.schema_handler.create_table("azure_actual_data")
        self.schema_handler.create_table("azure_amortized_data")


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

    def list_objects(self, prefix=None):
        container_client = self.blob_service_client.get_container_client(
            self.storage_container
        )
        blob_list = container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blob_list]

    def download_object(self, blob_name, destination_path):
        container_client = self.blob_service_client.get_container_client(
            self.storage_container
        )
        blob_client = container_client.get_blob_client(blob_name)
        with open(destination_path, "wb") as file:
            blob_data = blob_client.download_blob()
            file.write(blob_data.readall())

    def get_most_recent_object(self, prefix=None):
        container_client = self.blob_service_client.get_container_client(
            self.storage_container
        )
        blob_list = container_client.list_blobs(name_starts_with=prefix)
        most_recent_blob = max(blob_list, key=lambda blob: blob.last_modified)
        return most_recent_blob.name


if __name__ == "__main__":
    azure_client = AzureBlobStorageClient()
    objects = azure_client.list_objects(
        "billingexportamortized",
        "billingexportamortized/billingexportamortized/20240101-20240131",
    )
    most_recent_object = azure_client.get_most_recent_object(
        "billingexportamortized",
        "billingexportamortized/billingexportamortized/20240101-20240131",
    )
    print(most_recent_object)
