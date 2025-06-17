"""Open FinOps Stack CLI."""

import argparse
import sys
from pathlib import Path
from datetime import datetime

from ..core.config import Config
from ..core.state import LoadStateTracker
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


def aws_show_state(args):
    """Show load state and version history."""
    
    # Load configuration
    config_path = Path(args.config) if args.config else Path('config.toml')
    config = Config.load(config_path)
    
    # Override export name if provided
    if args.export_name:
        config.aws.export_name = args.export_name
    
    # Ensure we have an export name
    if not config.aws.export_name:
        print("Error: export_name is required. Set it in config.toml or use --export-name", file=sys.stderr)
        sys.exit(1)
    
    # Set up data directory path
    if config.project and config.project.data_dir:
        db_path = Path(config.project.data_dir) / "finops.duckdb"
    else:
        db_path = Path("./data/finops.duckdb")
    
    # Check if database exists
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        print("Run 'finops aws import-cur' first to create the database.", file=sys.stderr)
        sys.exit(1)
    
    # Initialize state tracker
    state_tracker = LoadStateTracker(str(db_path))
    
    print(f"Load State for export: {config.aws.export_name}")
    print("=" * 80)
    
    if args.billing_period:
        # Show history for specific billing period
        print(f"\nVersion History for {args.billing_period}:")
        print("-" * 80)
        
        versions = state_tracker.get_version_history('aws', config.aws.export_name, args.billing_period)
        
        if not versions:
            print(f"No load history found for billing period {args.billing_period}")
        else:
            print(f"{'Version ID':^40} {'Format':^6} {'Current':^7} {'Status':^10} {'Rows':>10} {'Timestamp':^20}")
            print("-" * 80)
            
            for v in versions:
                status = 'Complete' if v['load_completed'] else ('Failed' if v['error_message'] else 'In Progress')
                current = '✓' if v['current_version'] else ''
                rows = f"{v['row_count']:,}" if v['row_count'] else '-'
                timestamp = v['load_timestamp'].strftime('%Y-%m-%d %H:%M:%S') if v['load_timestamp'] else '-'
                
                print(f"{v['version_id'][:40]:40} {v['data_format_version']:^6} {current:^7} {status:^10} {rows:>10} {timestamp:^20}")
                
                if v['error_message']:
                    print(f"  Error: {v['error_message']}")
    
    else:
        # Show current versions for all billing periods
        print("\nCurrent Versions:")
        print("-" * 80)
        
        current_versions = state_tracker.get_current_versions('aws', config.aws.export_name)
        
        if not current_versions:
            print("No billing periods loaded yet")
        else:
            print(f"{'Billing Period':^15} {'Version ID':^40} {'Format':^6} {'Rows':>10} {'Files':>6} {'Loaded At':^20}")
            print("-" * 80)
            
            for v in current_versions:
                rows = f"{v['row_count']:,}" if v['row_count'] else '-'
                files = str(v['file_count']) if v['file_count'] else '-'
                timestamp = v['load_timestamp'].strftime('%Y-%m-%d %H:%M:%S') if v['load_timestamp'] else '-'
                
                print(f"{v['billing_period']:^15} {v['version_id'][:40]:40} {v['data_format_version']:^6} {rows:>10} {files:>6} {timestamp:^20}")
        
        print("\nTip: Use --billing-period YYYY-MM to see version history for a specific month")


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
    import_parser.add_argument('--export-name', '-n', help='Name of the CUR export')
    import_parser.add_argument(
        '--cur-version', '-v',
        choices=['v1', 'v2'],
        help='CUR version (default: v1)'
    )
    import_parser.add_argument(
        '--export-format', '-f',
        choices=['csv', 'parquet'],
        help='Export file format'
    )
    import_parser.add_argument('--start-date', '-s', help='Start date (YYYY-MM) for import')
    import_parser.add_argument('--end-date', '-e', help='End date (YYYY-MM) for import')
    import_parser.add_argument(
        '--reset', '-r',
        action='store_true',
        help='Drop existing tables before import'
    )
    import_parser.add_argument(
        '--table-strategy', '-t',
        choices=['separate', 'single'],
        default='separate',
        help='Table organization strategy (default: separate)'
    )
    import_parser.add_argument(
        '--destination', '-d',
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
    list_parser.add_argument('--export-name', '-n', help='Name of the CUR export')
    list_parser.add_argument(
        '--cur-version', '-v',
        choices=['v1', 'v2'],
        help='CUR version (default: v1)'
    )
    list_parser.add_argument('--start-date', '-s', help='Start date (YYYY-MM) to list')
    list_parser.add_argument('--end-date', '-e', help='End date (YYYY-MM) to list')
    list_parser.set_defaults(func=aws_list_manifests)
    
    # AWS show-state command
    state_parser = aws_subparsers.add_parser(
        'show-state',
        help='Show load state and version history'
    )
    state_parser.add_argument('--export-name', '-n', help='Name of the CUR export')
    state_parser.add_argument('--billing-period', '-B', help='Show history for specific billing period (YYYY-MM)')
    state_parser.set_defaults(func=aws_show_state)
    
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