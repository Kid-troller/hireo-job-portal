"""
Environment configuration utilities for Hireo project
"""
import os
from pathlib import Path

def load_env_file(env_file_path=None):
    """Load environment variables from .env file"""
    if env_file_path is None:
        base_dir = Path(__file__).resolve().parent.parent
        env_file_path = base_dir / '.env'
    
    if not os.path.exists(env_file_path):
        return
    
    with open(env_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

def get_env_var(key, default=None, required=False):
    """Get environment variable with optional default and required validation"""
    value = os.environ.get(key, default)
    if required and value is None:
        raise ValueError(f"Required environment variable '{key}' is not set")
    return value

def get_bool_env(key, default=False):
    """Get boolean environment variable"""
    value = os.environ.get(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')

def get_list_env(key, default=None, separator=','):
    """Get list environment variable"""
    value = os.environ.get(key)
    if value:
        return [item.strip() for item in value.split(separator)]
    return default or []
