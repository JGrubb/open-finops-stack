"""AWS CLI commands for Open FinOps Stack."""

import argparse
import sys
from pathlib import Path
from datetime import datetime

from core.config import Config
from core.state_manager import LoadStateManager, LoadStateTracker
from .pipeline import run_aws_pipeline
from .manifest import ManifestLocator


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
        'reset': args.reset,
        'table_strategy': args.table_strategy
    }
    
    # Override database backend if specified via CLI
    if hasattr(args, 'destination') and args.destination != 'duckdb':
        # CLI override for destination
        config.database.backend = args.destination
    
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
    print(f"  Table Strategy: {config.aws.table_strategy}")
    print(f"  Destination: {config.database.backend}")
    
    if config.aws.reset:
        print(f"  Reset: YES (will drop existing tables)")
    
    print()
    
    # Run the pipeline
    try:
        run_aws_pipeline(
            config=config.aws,
            destination=config.database.backend,
            table_strategy=config.aws.table_strategy,
            project_config=config.project,
            database_config=config.to_dict()  # Pass full config for backend factory
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
    
    # Initialize state manager
    state_manager = LoadStateManager(config.to_dict())
    
    print(f"Load State for export: {config.aws.export_name}")
    print("=" * 80)
    
    if args.billing_period:
        # Show history for specific billing period
        print(f"\nVersion History for {args.billing_period}:")
        print("-" * 80)
        
        versions = state_manager.get_version_history('aws', config.aws.export_name, args.billing_period)
        
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
        
        current_versions = state_manager.get_current_versions('aws', config.aws.export_name)
        
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


def aws_list_exports(args):
    """List all available exports and their tables."""
    
    # Load configuration
    config_path = Path(args.config) if args.config else Path('config.toml')
    config = Config.load(config_path)
    
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
    
    import duckdb
    
    # Initialize state tracker
    state_tracker = LoadStateTracker(str(db_path))
    
    # Connect to database
    conn = duckdb.connect(str(db_path))
    
    try:
        # Get all unique exports from state table
        exports_result = conn.execute("""
            SELECT DISTINCT vendor, export_name 
            FROM billing_state.load_state 
            WHERE load_completed = TRUE
            ORDER BY vendor, export_name
        """).fetchall()
        
        if not exports_result:
            print("No exports found in the database.")
            return
        
        print("Available Exports and Tables")
        print("=" * 80)
        
        for vendor, export_name in exports_result:
            print(f"\n{vendor.upper()} Export: {export_name}")
            print("-" * 40)
            
            # Get all tables for this export
            if vendor == 'aws':
                # Use the sanitized export name to find tables
                from core.utils import sanitize_table_name
                clean_export = sanitize_table_name(export_name)
                
                tables_result = conn.execute(f"""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'aws_billing' 
                    AND table_name LIKE '{clean_export}_%'
                    ORDER BY table_name
                """).fetchall()
                
                if tables_result:
                    print(f"Tables ({len(tables_result)}):")
                    total_rows = 0
                    
                    for (table_name,) in tables_result:
                        # Get row count
                        count_result = conn.execute(f"SELECT COUNT(*) FROM aws_billing.{table_name}").fetchone()
                        row_count = count_result[0] if count_result else 0
                        total_rows += row_count
                        
                        # Extract billing period from table name
                        parts = table_name.split('_')
                        if len(parts) >= 2:
                            billing_period = f"{parts[-2]}-{parts[-1]}"
                        else:
                            billing_period = "unknown"
                        
                        print(f"  - aws_billing.{table_name:<40} {row_count:>10,} rows  ({billing_period})")
                    
                    print(f"\nTotal rows for {export_name}: {total_rows:,}")
                else:
                    print("  No tables found (data may have been deleted)")
        
        # Show summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        # Count total exports by vendor
        vendor_counts = {}
        for vendor, _ in exports_result:
            vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
        
        for vendor, count in vendor_counts.items():
            print(f"{vendor.upper()}: {count} export(s)")
        
        print(f"\nTotal exports: {len(exports_result)}")
        
    finally:
        conn.close()


class AWSCommands:
    """AWS vendor commands."""
    
    def add_subparser(self, subparsers):
        """Add AWS subcommands to the CLI."""
        aws_parser = subparsers.add_parser('aws', help='AWS Cost and Usage Report pipelines')
        aws_subparsers = aws_parser.add_subparsers(dest='aws_command', help='AWS commands')
        
        # AWS import-cur command
        import_parser = aws_subparsers.add_parser(
            'import-cur',
            help='Import AWS Cost and Usage Reports'
        )
        import_parser.add_argument('--config', '-c', help='Path to config.toml file')
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
        list_parser.add_argument('--config', '-c', help='Path to config.toml file')
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
        state_parser.add_argument('--config', '-c', help='Path to config.toml file')
        state_parser.add_argument('--export-name', '-n', help='Name of the CUR export')
        state_parser.add_argument('--billing-period', '-B', help='Show history for specific billing period (YYYY-MM)')
        state_parser.set_defaults(func=aws_show_state)
        
        # AWS list-exports command
        exports_parser = aws_subparsers.add_parser(
            'list-exports',
            help='List all available exports and their tables'
        )
        exports_parser.add_argument('--config', '-c', help='Path to config.toml file')
        exports_parser.set_defaults(func=aws_list_exports)
    
    def execute(self, args):
        """Execute AWS commands."""
        if hasattr(args, 'func'):
            args.func(args)
        else:
            print("No AWS command specified")
            sys.exit(1)