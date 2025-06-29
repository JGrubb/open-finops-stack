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
    dataset_name: str = "aws_billing"
    table_strategy: str = "separate"
    cur_version: str = "v1"
    export_format: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    reset: bool = False
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    region: Optional[str] = None


@dataclass
class DatabaseConfig:
    """Database backend configuration."""
    backend: str = "duckdb"
    
    # DuckDB-specific settings
    duckdb: Dict[str, Any] = field(default_factory=lambda: {
        "database_path": "./data/finops.duckdb"
    })
    
    # Snowflake-specific settings  
    snowflake: Dict[str, Any] = field(default_factory=dict)
    
    # BigQuery-specific settings
    bigquery: Dict[str, Any] = field(default_factory=dict)
    
    # PostgreSQL-specific settings
    postgresql: Dict[str, Any] = field(default_factory=dict)
    
    # ClickHouse-specific settings
    clickhouse: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectConfig:
    """Project-level configuration."""
    name: str = "open-finops-stack"
    data_dir: str = "./data"


@dataclass
class Config:
    """Main configuration container."""
    project: ProjectConfig = field(default_factory=ProjectConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
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
        
        if "database" in config_data:
            config.database = DatabaseConfig(**config_data["database"])
        
        if "aws" in config_data:
            config.aws = AWSConfig(**config_data["aws"])
        
        # Override with environment variables
        config._load_env_overrides()
        
        return config
    
    def _load_env_overrides(self):
        """Override configuration with environment variables."""
        # Database environment overrides
        if env_backend := os.getenv("OPEN_FINOPS_DATABASE_BACKEND"):
            self.database.backend = env_backend
        if env_db_path := os.getenv("OPEN_FINOPS_DATABASE_PATH"):
            self.database.duckdb["database_path"] = env_db_path
        
        # AWS environment overrides
        if env_bucket := os.getenv("OPEN_FINOPS_AWS_BUCKET"):
            self.aws.bucket = env_bucket
        if env_prefix := os.getenv("OPEN_FINOPS_AWS_PREFIX"):
            self.aws.prefix = env_prefix
        if env_export := os.getenv("OPEN_FINOPS_AWS_EXPORT_NAME"):
            self.aws.export_name = env_export
        if env_dataset := os.getenv("OPEN_FINOPS_AWS_DATASET"):
            self.aws.dataset_name = env_dataset
        
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
            "reset": "reset",
            "table_strategy": "table_strategy"
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format for backend factory."""
        return {
            "project": {
                "name": self.project.name,
                "data_dir": self.project.data_dir
            },
            "database": {
            "backend": self.database.backend,
            "duckdb": self.database.duckdb,
            "snowflake": self.database.snowflake,
            "bigquery": self.database.bigquery,
            "postgresql": self.database.postgresql,
            "clickhouse": self.database.clickhouse
        },
            "aws": {
                "bucket": self.aws.bucket,
                "prefix": self.aws.prefix,
                "export_name": self.aws.export_name,
                "dataset_name": self.aws.dataset_name,
                "cur_version": self.aws.cur_version,
                "export_format": self.aws.export_format,
                "start_date": self.aws.start_date,
                "end_date": self.aws.end_date,
                "reset": self.aws.reset,
                "access_key_id": self.aws.access_key_id,
                "secret_access_key": self.aws.secret_access_key,
                "region": self.aws.region
            }
        }