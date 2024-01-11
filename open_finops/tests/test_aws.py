import unittest
from unittest.mock import patch, MagicMock
import boto3
from botocore.stub import Stubber
from open_finops.open_finops.aws.downloader import (
    ManifestDownloaderV1,
    ManifestDownloaderV2,
)


class TestManifestDownloader(unittest.TestCase):
    @patch("boto3.resource")
    def test_manifest_downloader_v1(self, mock_resource):
        mock_bucket = MagicMock()
        mock_resource.return_value.Bucket.return_value = mock_bucket
        mock_bucket.objects.filter.return_value = [{"Key": "test_manifest_v1.json"}]

        downloader = ManifestDownloaderV1("test_bucket", "test_dir")
        paths = downloader.download_manifests()

        mock_resource.assert_called_once_with("s3")
        mock_bucket.objects.filter.assert_called_once_with(Prefix="test_dir")
        self.assertEqual(paths, ["test_dir/test_manifest_v1.json"])

    @patch("boto3.resource")
    def test_manifest_downloader_v2(self, mock_resource):
        mock_bucket = MagicMock()
        mock_resource.return_value.Bucket.return_value = mock_bucket
        mock_bucket.objects.filter.return_value = [{"Key": "test_manifest_v2.json"}]

        downloader = ManifestDownloaderV2("test_bucket", "test_dir")
        paths = downloader.download_manifests()

        mock_resource.assert_called_once_with("s3")
        mock_bucket.objects.filter.assert_called_once_with(Prefix="test_dir")
        self.assertEqual(paths, ["test_dir/test_manifest_v2.json"])


if __name__ == "__main__":
    unittest.main()
