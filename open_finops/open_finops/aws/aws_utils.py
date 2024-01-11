import os
import shutil


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
    os.makedirs(
        os.path.dirname(f"{tmp_dir}"),
        exist_ok=True,
    )
    for f in manifest[self.billing_path_property]:
        print(f"Downloading {f}")
        self.bucket_resource.download_file(
            f,
            f"{tmp_dir}/{f}",
        )
        billing_file_paths.append(f"{tmp_dir}/{f}")
    return billing_file_paths


def key_formatter(key, cur_prefix):
    if key.startswith("s3://"):
        return "/".join(key.split("/")[3:])
    if not key.startswith(cur_prefix):
        return f"{cur_prefix}/{key}"
    else:
        return key
