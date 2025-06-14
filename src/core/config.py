"""Configuration management for Open FinOps Stack."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import toml
from dataclasses import dataclass, field


@dataclass
class AWSConfig:
    """AWS pipeline configuration."""
    bucket: Optional[str] = None
    prefix: Optional[str] = None
    export_name: Optional[str] = None
    cur_version: str = "v1"
    export_format: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    reset: bool = False
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    region: Optional[str] = None


@dataclass
class ProjectConfig:
    """Project-level configuration."""
    name: str = "open-finops-stack"
    data_dir: str = "./data"


@dataclass
class Config:
    """Main configuration container."""
    project: ProjectConfig = field(default_factory=ProjectConfig)
    aws: AWSConfig = field(default_factory=AWSConfig)
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from TOML file and environment variables."""
        config_data = {}
        
        # Load from TOML file if it exists
        if config_path is None:
            config_path = Path("config.toml")
        
        if config_path.exists():
            with open(config_path, "r") as f:
                config_data = toml.load(f)
        
        # Create config instances
        config = cls()
        
        # Update with TOML data
        if "project" in config_data:
            config.project = ProjectConfig(**config_data["project"])
        
        if "aws" in config_data:
            config.aws = AWSConfig(**config_data["aws"])
        
        # Override with environment variables
        config._load_env_overrides()
        
        return config
    
    def _load_env_overrides(self):
        """Override configuration with environment variables."""
        # AWS environment overrides
        if env_bucket := os.getenv("OPEN_FINOPS_AWS_BUCKET"):
            self.aws.bucket = env_bucket
        if env_prefix := os.getenv("OPEN_FINOPS_AWS_PREFIX"):
            self.aws.prefix = env_prefix
        if env_export := os.getenv("OPEN_FINOPS_AWS_EXPORT_NAME"):
            self.aws.export_name = env_export
        
        # AWS credentials from standard AWS env vars
        if not self.aws.access_key_id:
            self.aws.access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        if not self.aws.secret_access_key:
            self.aws.secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        if not self.aws.region:
            self.aws.region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    def merge_cli_args(self, args: Dict[str, Any]) -> None:
        """Merge command-line arguments into configuration."""
        # Map CLI args to config attributes
        aws_mappings = {
            "bucket": "bucket",
            "prefix": "prefix",
            "export_name": "export_name",
            "cur_version": "cur_version",
            "export_format": "export_format",
            "start_date": "start_date",
            "end_date": "end_date",
            "reset": "reset"
        }
        
        for cli_arg, config_attr in aws_mappings.items():
            if cli_arg in args and args[cli_arg] is not None:
                setattr(self.aws, config_attr, args[cli_arg])
    
    def validate_aws_config(self) -> None:
        """Validate AWS configuration has required fields."""
        required = ["bucket", "prefix", "export_name"]
        missing = [f for f in required if not getattr(self.aws, f)]
        
        if missing:
            raise ValueError(
                f"Missing required AWS configuration: {', '.join(missing)}. "
                "Set these in config.toml, environment variables, or CLI flags."
            )