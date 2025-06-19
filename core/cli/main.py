"""Main CLI entry point with plugin discovery."""

import argparse
import sys
from typing import Dict, Type

from .base import VendorCommands


class FinOpsCLI:
    """Main CLI with plugin discovery."""
    
    def __init__(self):
        self.vendors: Dict[str, Type[VendorCommands]] = {}
        self._discover_vendors()
    
    def _discover_vendors(self):
        """Discover vendor plugins via entry points."""
        vendors_found = False
        
        try:
            # Phase 2: Automatic discovery via entry points
            import pkg_resources
            
            entry_points = list(pkg_resources.iter_entry_points('open_finops.vendors'))
            
            for entry_point in entry_points:
                try:
                    vendor_class = entry_point.load()
                    self.vendors[entry_point.name] = vendor_class
                    print(f"✓ Loaded vendor plugin: {entry_point.name}")
                    vendors_found = True
                except Exception as e:
                    print(f"⚠ Failed to load vendor plugin {entry_point.name}: {e}")
                    
        except ImportError:
            pass  # pkg_resources not available
        
        # Fallback: Manual discovery for development mode
        if not vendors_found:
            try:
                from vendors.aws.cli import AWSCommands
                self.vendors['aws'] = AWSCommands
            except ImportError:
                pass  # AWS not installed
    
    def run(self):
        """Run the CLI."""
        parser = self._create_parser()
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            sys.exit(0)
        
        # Execute vendor command
        vendor_class = self.vendors.get(args.command)
        if vendor_class:
            vendor_instance = vendor_class()
            vendor_instance.execute(args)
        else:
            print(f"Vendor '{args.command}' not available")
            print(f"Available vendors: {', '.join(self.vendors.keys())}")
            sys.exit(1)
    
    def _create_parser(self):
        """Create the main argument parser."""
        parser = argparse.ArgumentParser(
            description='Open FinOps Stack - FOCUS-first FinOps platform'
        )
        parser.add_argument(
            '--config', '-c',
            help='Path to config.toml file (default: ./config.toml)'
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Let each vendor add its subcommands
        for name, vendor_class in self.vendors.items():
            vendor_instance = vendor_class()
            vendor_instance.add_subparser(subparsers)
        
        return parser


def main():
    """CLI entry point."""
    cli = FinOpsCLI()
    cli.run()


if __name__ == '__main__':
    main()