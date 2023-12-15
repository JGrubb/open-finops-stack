import os
import re
import boto3
from utils.configurator import Config
from dagster import asset, Definitions, FilesystemIOManager
from dagster_aws.s3 import s3_pickle_io_manager, S3Resource

config = Config("config.toml")


@asset
def return_s3_bucket():
    """
    Returns an S3 bucket object based on the configured bucket name.

    Returns:
        boto3.resources.factory.s3.Bucket: The S3 bucket object.
    """
    resource = boto3.resource("s3")
    return resource.Bucket(
        config.get("settings.cur_bucket")
    )  # this needs to be configurable


@asset()
def return_manifests(s3: S3Resource):
    """
    Returns a list of manifest objects from the specified S3 bucket.

    Args:
        my_bucket (S3.Bucket): The S3 bucket object.

    Returns:
        list: A list of manifest objects.

    """
    manifests = []
    for path in config.get("settings.report_dirs"):
        pattern = rf"\d{{8}}-\d{{8}}/{path}-Manifest.json"

        response = s3.get_client().list_objects_v2(
            Bucket=config.get("settings.cur_bucket"),
            Prefix=config.get("settings.cur_prefix") + f"/{path}/",
        )

        for item in response["Contents"]:  # this needs to be configurable
            last_two = "/".join(item["Key"].split("/")[-2:])
            if re.match(pattern, last_two):
                manifests.append(item["Key"])
    return manifests


@asset()
def download_manifests(s3: S3Resource, return_manifests):
    """
    Download manifests from an S3 bucket.

    Args:
      bucket (S3Bucket): The S3 bucket object.
      manifests (list): A list of manifest objects.

    Returns:
      None
    """
    for manifest in return_manifests:
        os.makedirs(
            os.path.dirname(f"{config.get('settings.project_dir')}/storage/{manifest}"),
            exist_ok=True,
        )
        print(f"Downloading {manifest}")
        s3.get_client().download_file(
            config.get("settings.cur_bucket"),
            manifest,
            f"{config.get('settings.project_dir')}/storage/{manifest}",
        )


defs = Definitions(
    assets=[return_manifests, download_manifests],
    resources={
        # "io_manager": s3_pickle_io_manager.configured(
        #     {
        #         "s3_bucket": config.get("settings.cur_bucket"),
        #         "s3_prefix": config.get("settings.cur_prefix"),
        #     }
        # ),
        # "fs_io_manager": FilesystemIOManager(),
        "s3": S3Resource(),
    },
)

# if __name__ == "__main__":
#     my_bucket = return_s3_bucket()
#     manifests = return_manifests(my_bucket)
#     download_manifests(my_bucket, manifests)
