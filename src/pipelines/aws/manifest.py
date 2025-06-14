"""AWS CUR manifest file handling."""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import boto3
from botocore.exceptions import ClientError


@dataclass
class ManifestFile:
    """Represents an AWS CUR manifest file."""
    bucket: str
    key: str
    billing_period: str
    version: str
    data: Optional[Dict] = None
    
    @property
    def report_keys(self) -> List[str]:
        """Get the S3 keys for the actual report files."""
        if not self.data:
            return []
        return self.data.get("reportKeys", [])
    
    @property
    def assembly_id(self) -> Optional[str]:
        """Get the assembly ID from the manifest."""
        if not self.data:
            return None
        return self.data.get("assemblyId")


class ManifestLocator:
    """Locates and retrieves AWS CUR manifest files."""
    
    def __init__(self, bucket: str, prefix: str, export_name: str, cur_version: str = "v1"):
        self.bucket = bucket
        self.prefix = prefix
        self.export_name = export_name
        self.cur_version = cur_version
        self.s3_client = None
    
    def _get_s3_client(self, access_key_id: Optional[str] = None, 
                       secret_access_key: Optional[str] = None,
                       region: Optional[str] = None) -> boto3.client:
        """Get or create S3 client."""
        if self.s3_client is None:
            if access_key_id and secret_access_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    region_name=region or 'us-east-1'
                )
            else:
                # Use default credential chain
                self.s3_client = boto3.client('s3', region_name=region or 'us-east-1')
        return self.s3_client
    
    def _get_v1_pattern(self) -> str:
        """Get regex pattern for v1 manifest files."""
        return rf"{self.prefix}/{self.export_name}/\d{{8}}-\d{{8}}/{self.export_name}-Manifest\.json"
    
    def _get_v2_pattern(self) -> str:
        """Get regex pattern for v2 manifest files."""
        return rf"{self.prefix}/{self.export_name}/metadata/BILLING_PERIOD=\d{{4}}-\d{{2}}/{self.export_name}-Manifest\.json"
    
    def list_manifests(self, start_date: Optional[str] = None, 
                      end_date: Optional[str] = None,
                      **aws_credentials) -> List[ManifestFile]:
        """List all manifest files in the bucket."""
        s3 = self._get_s3_client(**aws_credentials)
        pattern = self._get_v1_pattern() if self.cur_version == "v1" else self._get_v2_pattern()
        
        manifests = []
        paginator = s3.get_paginator('list_objects_v2')
        
        try:
            for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix):
                if 'Contents' not in page:
                    continue
                    
                for obj in page['Contents']:
                    key = obj['Key']
                    if re.match(pattern, key):
                        manifest = self._parse_manifest_key(key)
                        if manifest and self._is_in_date_range(manifest, start_date, end_date):
                            manifests.append(manifest)
        
        except ClientError as e:
            raise Exception(f"Failed to list S3 objects: {e}")
        
        return sorted(manifests, key=lambda m: m.billing_period)
    
    def _parse_manifest_key(self, key: str) -> Optional[ManifestFile]:
        """Parse manifest file S3 key to extract metadata."""
        if self.cur_version == "v1":
            # Extract date range from v1 path
            match = re.search(r'/(\d{8})-(\d{8})/', key)
            if match:
                start_date = match.group(1)
                # Convert to YYYY-MM format
                billing_period = f"{start_date[:4]}-{start_date[4:6]}"
                return ManifestFile(
                    bucket=self.bucket,
                    key=key,
                    billing_period=billing_period,
                    version="v1"
                )
        else:
            # Extract billing period from v2 path
            match = re.search(r'BILLING_PERIOD=(\d{4}-\d{2})', key)
            if match:
                billing_period = match.group(1)
                return ManifestFile(
                    bucket=self.bucket,
                    key=key,
                    billing_period=billing_period,
                    version="v2"
                )
        return None
    
    def _is_in_date_range(self, manifest: ManifestFile, 
                         start_date: Optional[str], 
                         end_date: Optional[str]) -> bool:
        """Check if manifest is within the specified date range."""
        if not start_date and not end_date:
            return True
        
        manifest_date = manifest.billing_period
        
        if start_date and manifest_date < start_date:
            return False
        if end_date and manifest_date > end_date:
            return False
        
        return True
    
    def fetch_manifest(self, manifest_file: ManifestFile, **aws_credentials) -> ManifestFile:
        """Fetch and parse a manifest file from S3."""
        s3 = self._get_s3_client(**aws_credentials)
        
        try:
            response = s3.get_object(Bucket=manifest_file.bucket, Key=manifest_file.key)
            manifest_data = json.loads(response['Body'].read())
            manifest_file.data = manifest_data
            return manifest_file
        
        except ClientError as e:
            raise Exception(f"Failed to fetch manifest {manifest_file.key}: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse manifest JSON: {e}")