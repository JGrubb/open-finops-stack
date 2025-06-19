"""Base classes for CLI commands."""

from abc import ABC, abstractmethod


class VendorCommands(ABC):
    """Base class for vendor command implementations."""
    
    @abstractmethod
    def add_subparser(self, subparsers):
        """Add vendor subcommands to the CLI parser."""
        pass
    
    @abstractmethod  
    def execute(self, args):
        """Execute vendor commands."""
        pass


class BaseCommand(ABC):
    """Base class for individual commands."""
    
    @abstractmethod
    def run(self, args):
        """Execute the command."""
        pass