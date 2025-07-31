"""
API Schemas Package - Version-agnostic schema management.

This package provides schema definitions and utilities for all API versions,
including base classes, validation utilities, and version management.
"""

from typing import Dict, Type, Callable

from .base import (
    BaseSchema,
    TimestampMixin,
    IDMixin,
    PaginationRequest,
    PaginationResponse,
    SuccessResponse,
    ErrorResponse,
    VersionedSchemaMixin,
    SchemaEvolutionMixin,
    schema_manager,
    create_versioned_schema,
    validate_with_version_fallback,
    create_schema_validator_chain,
    compare_schema_fields,
    get_schema_field_types
)

from .validators import (
    ValidationResult,
    VersionAwareValidator,
    global_validator,
    # Dynamic validation functions (recommended)
    validate_data_by_version,
    validate_data_with_latest,
    validate_with_smart_fallback,
    validate_with_auto_version,
    # Version management utilities
    get_supported_versions,
    get_latest_version,
    is_version_supported,
    get_version_for_resource,
    # Legacy validation functions (for backward compatibility)
    validate_v1_data,
    validate_v2_data,
    validate_with_version_fallback as validate_fallback,
    # Comparison and migration utilities
    compare_version_schemas,
    create_business_rule_validator,
    create_field_migration_rule,
    create_default_value_migration
)

# Version-specific imports
from . import v1
from . import v2

__all__ = [
    # Base schema classes
    "BaseSchema",
    "TimestampMixin",
    "IDMixin",
    "PaginationRequest",
    "PaginationResponse",
    "SuccessResponse",
    "ErrorResponse",
    
    # Version management
    "VersionedSchemaMixin",
    "SchemaEvolutionMixin",
    "schema_manager",
    
    # Schema utilities
    "create_versioned_schema",
    "validate_with_version_fallback",
    "create_schema_validator_chain",
    "compare_schema_fields",
    "get_schema_field_types",
    
    # Validation utilities
    "ValidationResult",
    "VersionAwareValidator",
    "global_validator",
    
    # Dynamic validation functions (recommended)
    "validate_data_by_version",
    "validate_data_with_latest", 
    "validate_with_smart_fallback",
    "validate_with_auto_version",
    
    # Version management utilities
    "get_supported_versions",
    "get_latest_version",
    "is_version_supported",
    "get_version_for_resource",
    
    # Legacy validation functions (for backward compatibility)
    "validate_v1_data",
    "validate_v2_data",
    "validate_fallback",
    
    # Comparison utilities
    "compare_version_schemas",
    
    # Migration utilities
    "create_business_rule_validator",
    "create_field_migration_rule",
    "create_default_value_migration",
    
    # Dynamic version management
    "register_version_schemas",
    "register_version_migrations", 
    "add_new_api_version",
    
    # Version modules
    "v1",
    "v2"
]

# Schema version information
SUPPORTED_VERSIONS = ["v1", "v2"]
DEFAULT_VERSION = "v2"
LEGACY_VERSION = "v1"

# Initialize global validator with common migration rules
def _initialize_global_validator():
    """Initialize the global validator with common migration patterns."""
    
    # V1 to V2 migration rules
    def v1_to_v2_migration(data: dict) -> dict:
        """Default V1 to V2 migration."""
        migrated = data.copy()
        
        # Add V2-specific defaults
        if "metadata" not in migrated:
            migrated["metadata"] = {"migrated_from": "v1"}
        if "preferences" not in migrated:
            migrated["preferences"] = {}
        if "settings" not in migrated:
            migrated["settings"] = {}
        
        return migrated
    
    # V2 to V1 migration rules (for backward compatibility)
    def v2_to_v1_migration(data: dict) -> dict:
        """Default V2 to V1 migration (strip V2-only fields)."""
        migrated = data.copy()
        
        # Remove V2-specific fields
        v2_only_fields = ["metadata", "preferences", "settings", "tags"]
        for field in v2_only_fields:
            migrated.pop(field, None)
        
        return migrated
    
    # Register migrations
    global_validator.register_migration("v1", "v2", v1_to_v2_migration)
    global_validator.register_migration("v2", "v1", v2_to_v1_migration)

# Dynamic schema registration utilities
def register_version_schemas(version: str, schemas_dict: Dict[str, Type]):
    """
    Register all schemas for a new version.
    
    Args:
        version: Version identifier (e.g., "v3", "v4")
        schemas_dict: Dictionary mapping resource names to schema classes
    """
    for resource, schema_class in schemas_dict.items():
        global_validator.register_schema(version, resource, schema_class)


def register_version_migrations(version_migrations: Dict[str, Callable]):
    """
    Register migration functions for version transitions.
    
    Args:
        version_migrations: Dictionary mapping "from_to" keys to migration functions
                          e.g., {"v2_to_v3": migration_func, "v3_to_v2": reverse_func}
    """
    for migration_key, migration_func in version_migrations.items():
        parts = migration_key.split('_to_')
        if len(parts) == 2:
            from_version, to_version = parts
            global_validator.register_migration(from_version, to_version, migration_func)


def add_new_api_version(
    version: str, 
    schemas: Dict[str, Type],
    migrations_from: Dict[str, Callable] = None,
    migrations_to: Dict[str, Callable] = None
):
    """
    Add a complete new API version with schemas and migrations.
    
    Args:
        version: New version identifier
        schemas: Dictionary of resource schemas
        migrations_from: Migration functions FROM other versions TO this version
        migrations_to: Migration functions FROM this version TO other versions
    """
    # Register schemas
    register_version_schemas(version, schemas)
    
    # Register migrations from other versions to this version
    if migrations_from:
        for from_version, migration_func in migrations_from.items():
            global_validator.register_migration(from_version, version, migration_func)
    
    # Register migrations from this version to other versions
    if migrations_to:
        for to_version, migration_func in migrations_to.items():
            global_validator.register_migration(version, to_version, migration_func)
    
    # Update supported versions if not already included
    if version not in SUPPORTED_VERSIONS:
        SUPPORTED_VERSIONS.append(version)
        # Sort versions to maintain order
        SUPPORTED_VERSIONS.sort(key=lambda v: int(v[1:]) if v[1:].isdigit() else 0)


# Initialize on import
_initialize_global_validator()