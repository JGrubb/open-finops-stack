import os
import re
import boto3
import utils.configurator as config

config = config.Config("config.toml").config


def get_s3_resource():
    return boto3.resource("s3")


def return_s3_bucket():
    resource = boto3.resource("s3")
    return resource.Bucket(
        config["settings"]["cur_bucket"]
    )  # this needs to be configurable


def return_manifests(my_bucket):
    """
    Returns a list of manifest objects from the specified S3 bucket.

    Args:
        my_bucket (S3.Bucket): The S3 bucket object.

    Returns:
        list: A list of manifest objects.

    """
    manifests = []
    for path in config["settings"]["report_dirs"]:
        pattern = rf"\d{{8}}-\d{{8}}/{path}-Manifest.json"

        for object in my_bucket.objects.filter(
            Prefix=config["settings"]["cur_prefix"] + f"/{path}/"
        ):  # this needs to be configurable
            last_two = "/".join(object.key.split("/")[-2:])
            if re.match(pattern, last_two):
                manifests.append(object)
    return manifests


def download_manifests(bucket, manifests):
    """
    Download manifests from an S3 bucket.

    Args:
      bucket (S3Bucket): The S3 bucket object.
      manifests (list): A list of manifest objects.

    Returns:
      None
    """
    for manifest in manifests:
        os.makedirs(
            os.path.dirname(
                f"{config['settings']['project_dir']}/storage/{manifest.key}"
            ),
            exist_ok=True,
        )
        print(f"Downloading {manifest.key}")
        bucket.download_file(
            manifest.key, f"{config['settings']['project_dir']}/storage/{manifest.key}"
        )


if __name__ == "__main__":
    my_bucket = return_s3_bucket()
    manifests = return_manifests(my_bucket)
    download_manifests(my_bucket, manifests)
