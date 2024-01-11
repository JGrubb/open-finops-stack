import os
import boto3
import re

from aws.aws_utils import key_formatter


class S3Downloader:
    def __init__(self, cur_config={}):
        self.bucket_name = cur_config["bucket_name"]
        self.prefix = cur_config["prefix"]
        self.export_name = cur_config["export_name"]
        self.bucket_resource = boto3.resource("s3").Bucket(self.bucket_name)
        self.s3_objects = []
        self.file_paths = []
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.storage_dir = os.getenv("OFS_STORAGE_DIR")

    def fetch_s3_object(self, key):
        # key = key_formatter(key)
        storage_path = f"{self.storage_dir}/{key}"
        os.makedirs(os.path.dirname(f"{storage_path}"), exist_ok=True)
        print(f"Downloading {key} to {storage_path}")
        self.bucket_resource.download_file(key, f"{storage_path}")
        return f"{storage_path}"


class DataDownloader(S3Downloader):
    def download_data(self, files):
        file_paths = []
        for file_path in files:
            path = key_formatter(file_path, self.prefix)
            file_path = self.fetch_s3_object(path)
            file_paths.append(file_path)
        return file_paths


class ManifestDownloader(S3Downloader):
    def fetch_manifest_objects(self):
        raise NotImplementedError("Subclasses must implement this method")

    def download_manifests(self):
        manifests = self.s3_objects
        file_paths = []
        for manifest in manifests:
            file_path = self.fetch_s3_object(manifest.key)
            file_paths.append(file_path)
        return file_paths

    def main(self):
        self.fetch_manifest_objects()
        file_paths = self.download_manifests()
        return file_paths


class ManifestDownloaderV1(ManifestDownloader):
    def fetch_manifest_objects(self):
        # Implement the logic to fetch manifest objects for version 1
        pattern = rf"\d{{8}}-\d{{8}}/{self.export_name}-Manifest\.json"
        for item in self.bucket_resource.objects.filter(
            Prefix=f"{self.prefix}/{self.export_name}",
        ):  # this needs to be configurable
            last_two = "/".join(item.key.split("/")[-2:])
            if re.match(pattern, last_two):
                self.s3_objects.append(item)
        return None


class ManifestDownloaderV2(ManifestDownloader):
    def fetch_manifest_objects(self):
        # Implement the logic to fetch manifest objects for version 2
        pattern = rf"{self.prefix}/{self.export_name}/metadata/BILLING_PERIOD=\d{{4}}-\d{{2}}/{self.export_name}-Manifest\.json"
        for item in self.bucket_resource.objects.filter(
            Prefix=f"{self.prefix}/{self.export_name}/metadata/",
        ):
            if re.match(pattern, item.key):
                self.s3_objects.append(item)
        return None


def refresh_manifests(cur_version, cur_config={}):
    if cur_version == "v1":
        downloader = ManifestDownloaderV1(cur_config)
    else:
        downloader = ManifestDownloaderV2(cur_config)

    paths = downloader.main()
    return paths
    # Do something with paths_v1 and paths_v2


if __name__ == "__main__":
    cur_config = {
        "bucket_name": os.getenv("OFS_CUR_BUCKET"),
        "prefix": os.getenv("OFS_CUR_PREFIX"),
        "export_name": os.getenv("OFS_CUR_EXPORT_NAME"),
    }
    refresh_manifests("v1", cur_config)
