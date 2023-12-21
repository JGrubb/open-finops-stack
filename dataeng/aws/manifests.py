import os
import re
import boto3


def return_s3_bucket():
    resource = boto3.resource(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    return resource.Bucket(os.getenv("OFS_CUR_BUCKET"))


def return_manifests(my_bucket):
    """
    Returns a list of manifest objects from the specified S3 bucket.

    Args:
        my_bucket (S3.Bucket): The S3 bucket object.

    Returns:
        list: A list of manifest objects.

    """
    manifests = []
    pattern = r"\d{8}-\d{8}/[a-z\-\d]+-Manifest\.json"

    for item in my_bucket.objects.filter(
        Prefix=os.getenv("OFS_CUR_PREFIX"),
    ):  # this needs to be configurable
        last_two = "/".join(item.key.split("/")[-2:])
        if re.match(pattern, last_two):
            manifests.append(item)
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
        storage_path = f"{os.getenv('OFS_STORAGE_DIR')}/{manifest.key}"
        os.makedirs(
            os.path.dirname(storage_path),
            exist_ok=True,
        )
        print(f"Downloading {manifest.key}")
        bucket.download_file(manifest.key, storage_path)


if __name__ == "__main__":
    my_bucket = return_s3_bucket()
    manifests = return_manifests(my_bucket)
    download_manifests(my_bucket, manifests)
