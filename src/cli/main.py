"""Open FinOps Stack CLI."""

import argparse
import sys
from pathlib import Path

from ..core.config import Config
from ..pipelines.aws import run_aws_pipeline, ManifestLocator


def aws_import_cur(args):
    """Import AWS Cost and Usage Reports."""
    
    # Load configuration
    config_path = Path(args.config) if args.config else Path('config.toml')
    config = Config.load(config_path)
    
    # Merge CLI arguments into configuration
    cli_args = {
        'bucket': args.bucket,
        'prefix': args.prefix,
        'export_name': args.export_name,
        'cur_version': args.cur_version,
        'export_format': args.export_format,
        'start_date': args.start_date,
        'end_date': args.end_date,
        'reset': args.reset
    }
    
    # Remove None values
    cli_args = {k: v for k, v in cli_args.items() if v is not None}
    
    # Merge with config
    config.merge_cli_args(cli_args)
    
    # Validate we have required fields
    try:
        config.validate_aws_config()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("\nRequired parameters can be set via:")
        print("  - config.toml file")
        print("  - Environment variables (OPEN_FINOPS_AWS_*)")
        print("  - Command-line flags")
        sys.exit(1)
    
    # Show configuration
    print("\nAWS CUR Import Configuration:")
    print(f"  Bucket: {config.aws.bucket}")
    print(f"  Prefix: {config.aws.prefix}")
    print(f"  Export Name: {config.aws.export_name}")
    print(f"  CUR Version: {config.aws.cur_version}")
    print(f"  Format: {config.aws.export_format or 'auto-detect'}")
    print(f"  Date Range: {config.aws.start_date or 'all'} to {config.aws.end_date or 'all'}")
    print(f"  Table Strategy: {args.table_strategy}")
    print(f"  Destination: {args.destination}")
    
    if config.aws.reset:
        print(f"  Reset: YES (will drop existing tables)")
    
    print()
    
    # Run the pipeline
    try:
        run_aws_pipeline(
            config=config.aws,
            destination=args.destination,
            table_strategy=args.table_strategy,
            project_config=config.project
        )
        print("\n✅ Import completed successfully!")
    except Exception as e:
        print(f"\n❌ Import failed: {e}", file=sys.stderr)
        sys.exit(1)


def aws_list_manifests(args):
    """List available billing periods in S3."""
    
    # Load configuration
    config_path = Path(args.config) if args.config else Path('config.toml')
    config = Config.load(config_path)
    
    # Merge CLI arguments for bucket/prefix/export_name if provided
    cli_args = {
        'bucket': args.bucket,
        'prefix': args.prefix,
        'export_name': args.export_name,
        'cur_version': args.cur_version
    }
    cli_args = {k: v for k, v in cli_args.items() if v is not None}
    config.merge_cli_args(cli_args)
    
    # Validate we have required fields
    try:
        config.validate_aws_config()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get AWS credentials
    aws_creds = {
        'access_key_id': config.aws.access_key_id,
        'secret_access_key': config.aws.secret_access_key,
        'region': config.aws.region
    }
    
    # Initialize manifest locator
    locator = ManifestLocator(
        bucket=config.aws.bucket,
        prefix=config.aws.prefix,
        export_name=config.aws.export_name,
        cur_version=config.aws.cur_version
    )
    
    try:
        # List manifests
        manifests = locator.list_manifests(
            start_date=args.start_date,
            end_date=args.end_date,
            **aws_creds
        )
        
        if not manifests:
            print("No manifests found.")
            return
        
        print(f"\nFound {len(manifests)} billing periods:")
        for manifest in manifests:
            print(f"  - {manifest.billing_period} ({manifest.version})")
            print(f"    Path: {manifest.key}")
        
    except Exception as e:
        print(f"Error listing manifests: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Open FinOps Stack - FOCUS-first FinOps platform'
    )
    parser.add_argument(
        '--config', '-c',
        help='Path to config.toml file (default: ./config.toml)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # AWS commands
    aws_parser = subparsers.add_parser('aws', help='AWS Cost and Usage Report pipelines')
    aws_subparsers = aws_parser.add_subparsers(dest='aws_command', help='AWS commands')
    
    # AWS import-cur command
    import_parser = aws_subparsers.add_parser(
        'import-cur',
        help='Import AWS Cost and Usage Reports'
    )
    import_parser.add_argument('--bucket', '-b', help='S3 bucket containing CUR files')
    import_parser.add_argument('--prefix', '-p', help='S3 prefix/path to CUR files')
    import_parser.add_argument('--export-name', '-e', help='Name of the CUR export')
    import_parser.add_argument(
        '--cur-version', '-v',
        choices=['v1', 'v2'],
        help='CUR version (default: v1)'
    )
    import_parser.add_argument(
        '--export-format',
        choices=['csv', 'parquet'],
        help='Export file format'
    )
    import_parser.add_argument('--start-date', help='Start date (YYYY-MM) for import')
    import_parser.add_argument('--end-date', help='End date (YYYY-MM) for import')
    import_parser.add_argument(
        '--reset',
        action='store_true',
        help='Drop existing tables before import'
    )
    import_parser.add_argument(
        '--table-strategy',
        choices=['separate', 'single'],
        default='separate',
        help='Table organization strategy (default: separate)'
    )
    import_parser.add_argument(
        '--destination',
        default='duckdb',
        help='DLT destination (default: duckdb)'
    )
    import_parser.set_defaults(func=aws_import_cur)
    
    # AWS list-manifests command
    list_parser = aws_subparsers.add_parser(
        'list-manifests',
        help='List available billing periods in S3'
    )
    list_parser.add_argument('--bucket', '-b', help='S3 bucket containing CUR files')
    list_parser.add_argument('--prefix', '-p', help='S3 prefix/path to CUR files')
    list_parser.add_argument('--export-name', '-e', help='Name of the CUR export')
    list_parser.add_argument(
        '--cur-version', '-v',
        choices=['v1', 'v2'],
        help='CUR version (default: v1)'
    )
    list_parser.add_argument('--start-date', help='Start date (YYYY-MM) to list')
    list_parser.add_argument('--end-date', help='End date (YYYY-MM) to list')
    list_parser.set_defaults(func=aws_list_manifests)
    
    # Azure commands (placeholder)
    azure_parser = subparsers.add_parser('azure', help='Azure billing pipelines (coming soon)')
    azure_subparsers = azure_parser.add_subparsers(dest='azure_command', help='Azure commands')
    
    azure_import = azure_subparsers.add_parser('import-billing', help='Import Azure billing data')
    azure_import.set_defaults(func=lambda args: print("Azure billing import - coming soon!"))
    
    # GCP commands (placeholder)
    gcp_parser = subparsers.add_parser('gcp', help='GCP billing pipelines (coming soon)')
    gcp_subparsers = gcp_parser.add_subparsers(dest='gcp_command', help='GCP commands')
    
    gcp_import = gcp_subparsers.add_parser('import-billing', help='Import GCP billing data')
    gcp_import.set_defaults(func=lambda args: print("GCP billing import - coming soon!"))
    
    # Parse arguments
    args = parser.parse_args()
    
    # Show help if no command provided
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    # Show subcommand help if needed
    if args.command == 'aws' and not args.aws_command:
        aws_parser.print_help()
        sys.exit(0)
    elif args.command == 'azure' and not args.azure_command:
        azure_parser.print_help()
        sys.exit(0)
    elif args.command == 'gcp' and not args.gcp_command:
        gcp_parser.print_help()
        sys.exit(0)
    
    # Execute the command
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()