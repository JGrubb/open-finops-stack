"""Main CLI entry point with plugin discovery."""

import argparse
import sys
from typing import Dict, Type

from .base import VendorCommands


class FinOpsCLI:
    """Main CLI coordinator that discovers and manages vendor plugins.
    
    Automatically discovers vendor plugins via setuptools entry points,
    with fallback to direct imports for development environments.
    """
    
    def __init__(self):
        self.vendors: Dict[str, Type[VendorCommands]] = {}
        self._discover_vendors()
    
    def _discover_vendors(self):
        """Discover vendor plugins via entry points with development fallback."""
        vendors_found = False
        
        try:
            # Primary method: Auto-discovery via setuptools entry points
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
            # pkg_resources not available (rare case)
            pass
        
        # Development fallback: Direct import when entry points not set up
        if not vendors_found:
            try:
                from vendors.aws.cli import AWSCommands
                self.vendors['aws'] = AWSCommands
            except ImportError:
                # AWS vendor not available in this installation
                pass
    
    def run(self):
        """Parse arguments and execute the appropriate vendor command."""
        parser = self._create_parser()
        args = parser.parse_args()
        
        # Show help if no command specified
        if not args.command:
            parser.print_help()
            sys.exit(0)
        
        # Execute vendor command
        vendor_class = self.vendors.get(args.command)
        if vendor_class:
            vendor_instance = vendor_class()
            vendor_instance.execute(args)
        else:
            # Handle unknown vendor with helpful error message
            print(f"Vendor '{args.command}' not available")
            if self.vendors:
                print(f"Available vendors: {', '.join(self.vendors.keys())}")
            else:
                print("No vendor plugins found. Check your installation.")
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
        
        # Register subcommands from each discovered vendor plugin
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