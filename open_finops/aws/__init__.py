import os
import re
import shutil
import boto3
import json


class S3Handler:
    def __init__(self, bucket, prefix, export_name):
        self.bucket_name = bucket
        self.bucket_resource = None
        self.prefix = prefix
        self.export_name = export_name
        self.manifest_s3_objects = []
        self.manifest_paths = []
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.storage_dir = os.getenv("OFS_STORAGE_DIR", "storage")
        self.billing_path_property = None

    def preclean(self):
        if os.path.exists(self.storage_dir):
            shutil.rmtree(self.storage_dir)

    def return_s3_bucket(self):
        resource = boto3.resource(
            "s3",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )
        self.bucket_resource = resource.Bucket(self.bucket_name)

    def fetch_manifest_objects(self):
        for item in self.bucket_resource.objects.filter(
            Prefix=f"{self.prefix}/{self.export_name}",
        ):
            if re.match(self.pattern, item.key):
                self.manifest_s3_objects.append(item)
        return None

    def download_manifests(self):
        """
        Download manifests from an S3 bucket.

        Args:
          bucket (S3Bucket): The S3 bucket object.
          manifests (list): A list of manifest objects.

        Returns:
          None
        """
        for manifest in self.manifest_s3_objects:
            storage_path = f"{self.storage_dir}/{manifest.key}"
            os.makedirs(
                os.path.dirname(storage_path),
                exist_ok=True,
            )
            print(f"Downloading {manifest.key}")
            self.bucket_resource.download_file(manifest.key, storage_path)
            self.manifest_paths.append(storage_path)
        return None

    def download_billing_files(self, manifest):
        """
        Download files from an S3 bucket based on the given manifest.

        Args:
            manifest (dict): The manifest containing the report keys.

        Returns:
            None
        """
        billing_file_paths = []
        tmp_dir = f"{self.storage_dir}/tmp"
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        for f in manifest["data_files"]:
            os.makedirs(
                os.path.dirname(f"{tmp_dir}/{f}"),
                exist_ok=True,
            )
            print(f"Downloading {f}")
            try:
                self.bucket_resource.download_file(
                    f,
                    f"{tmp_dir}/{f}",
                )
                billing_file_paths.append(f"{tmp_dir}/{f}")
            except Exception as e:
                print(f"Error downloading {f}: {e}")
        return billing_file_paths

    def main(self):
        self.preclean()
        self.return_s3_bucket()
        self.fetch_manifest_objects()
        self.download_manifests()
        return self.manifest_paths


class Aws_v1(S3Handler):
    def __init__(self, bucket, prefix, export_name):
        super().__init__(bucket, prefix, export_name)
        self.pattern = rf"{self.prefix}/{self.export_name}/\d{{8}}-\d{{8}}/{self.export_name}-Manifest\.json"


class Aws_v2(S3Handler):
    def __init__(self, bucket, prefix, export_name):
        super().__init__(bucket, prefix, export_name)
        self.pattern = rf"{self.prefix}/{self.export_name}/metadata/BILLING_PERIOD=\d{{4}}-\d{{2}}/{self.export_name}-Manifest\.json"


if __name__ == "__main__":
    aws = Aws_v2("reports.commerceguys.com", "billing", "aws-cost-usage-v2")
    aws.main()
