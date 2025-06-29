"""Core utility functions for Open FinOps Stack."""

import re
from typing import Optional


def sanitize_table_name(name: str) -> str:
    """Sanitize a string to be safe for use as a table name.
    
    Rules:
    - Replace spaces with underscores
    - Replace hyphens with underscores
    - Remove or replace special characters
    - Convert to lowercase
    - Ensure it starts with a letter
    - Truncate if too long (max 64 chars for most databases)
    
    Args:
        name: The string to sanitize
        
    Returns:
        A sanitized string safe for use as a table name
    """
    # Convert to lowercase
    name = name.lower()
    
    # Replace common separators with underscores
    name = re.sub(r'[\s\-/\\]+', '_', name)
    
    # Remove any characters that aren't alphanumeric or underscore
    name = re.sub(r'[^a-z0-9_]', '', name)
    
    # Ensure it starts with a letter (prepend 'export_' if it doesn't)
    if not name or not name[0].isalpha():
        name = 'export_' + name
    
    # Remove consecutive underscores
    name = re.sub(r'_+', '_', name)
    
    # Strip underscores from ends
    name = name.strip('_')
    
    # Truncate to 64 characters (leaving room for suffixes)
    if len(name) > 50:
        name = name[:50]
    
    return name


def create_table_name(export_name: str, billing_period: str) -> str:
    """Create a table name from export name and billing period.
    
    Args:
        export_name: The export name (e.g., "production-account")
        billing_period: The billing period (e.g., "2024-01")
        
    Returns:
        A properly formatted table name (e.g., "production_account_2024_01")
    """
    # Sanitize export name
    clean_export = sanitize_table_name(export_name)
    
    # Clean billing period (already in YYYY-MM format)
    clean_period = billing_period.replace('-', '_')
    
    # Combine them
    return f"{clean_export}_{clean_period}"