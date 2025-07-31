"""
API Schemas Package - Version-agnostic schema management.

This package provides schema definitions and utilities for all API versions,
including base classes, validation utilities, and version management.
"""

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
    validate_v1_data,
    validate_v2_data,
    validate_with_version_fallback as validate_fallback,
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
    "validate_v1_data",
    "validate_v2_data",
    "validate_fallback",
    "compare_version_schemas",
    
    # Migration utilities
    "create_business_rule_validator",
    "create_field_migration_rule",
    "create_default_value_migration",
    
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

# Initialize on import
_initialize_global_validator()