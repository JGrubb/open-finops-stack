from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

class AzureBlobStorageClient:
    def __init__(self, connection_string=None, credential_file=None):
        if connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        elif credential_file:
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient.from_connection_string(credential_file, credential)
        else:
            raise ValueError("Either connection_string or credential_file must be provided.")

    def list_objects(self, container_name, prefix=None):
        container_client = self.blob_service_client.get_container_client(container_name)
        blob_list = container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blob_list]

    def download_object(self, container_name, blob_name, destination_path):
        container_client = self.blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        with open(destination_path, "wb") as file:
            blob_data = blob_client.download_blob()
            file.write(blob_data.readall())

    def get_most_recent_object(self, container_name, prefix=None):
        container_client = self.blob_service_client.get_container_client(container_name)
        blob_list = container_client.list_blobs(name_starts_with=prefix)
        most_recent_blob = max(blob_list, key=lambda blob: blob.last_modified)
        return most_recent_blob.name