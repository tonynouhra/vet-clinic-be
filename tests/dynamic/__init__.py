"""
Dynamic API testing framework for version-agnostic testing.

This package provides utilities for testing API endpoints across multiple versions
without code duplication through configuration-driven testing.
"""

from .config_manager import VersionConfigManager, get_config_manager, ConfigurationError
from .base_test import BaseDynamicTest

__all__ = [
    'VersionConfigManager',
    'get_config_manager', 
    'ConfigurationError',
    'BaseDynamicTest'
]