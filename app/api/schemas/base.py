"""
Base schema patterns and utilities for API versioning.

Provides common schema patterns, validation utilities, and base classes
that can be used across different API versions.
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration for all API schemas."""
    
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        arbitrary_types_allowed=True
    )


class TimestampMixin(BaseModel):
    """Mixin for models that include timestamp fields."""
    
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class IDMixin(BaseModel):
    """Mixin for models that include ID fields."""
    
    id: Optional[int] = Field(None, description="Unique identifier")


class PaginationRequest(BaseSchema):
    """Standard pagination request schema."""
    
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(10, ge=1, le=100, description="Items per page")


class PaginationResponse(BaseSchema):
    """Standard pagination response metadata."""
    
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    total: int = Field(description="Total number of items")
    pages: int = Field(description="Total number of pages")


class SuccessResponse(BaseSchema):
    """Standard success response schema."""
    
    success: bool = Field(True, description="Operation success flag")
    message: Optional[str] = Field(None, description="Success message")
    data: Optional[Any] = Field(None, description="Response data")


class ErrorResponse(BaseSchema):
    """Standard error response schema."""
    
    success: bool = Field(False, description="Operation success flag")
    message: str = Field(description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


# Schema inheritance patterns for version evolution
class VersionedSchemaMixin(BaseModel):
    """Mixin for schemas that support version evolution."""
    
    @classmethod
    def get_version_fields(cls, version: str) -> Dict[str, Any]:
        """Get fields specific to a version."""
        version_fields = {}
        for field_name, field_info in cls.model_fields.items():
            if hasattr(field_info, 'json_schema_extra') and field_info.json_schema_extra:
                if 'versions' in field_info.json_schema_extra:
                    if version in field_info.json_schema_extra['versions']:
                        version_fields[field_name] = field_info
        return version_fields
    
    @classmethod
    def create_version_schema(cls, version: str, exclude_fields: Optional[list] = None):
        """Create a schema for a specific version."""
        exclude_fields = exclude_fields or []
        
        # Create new schema class with version-specific fields
        class_name = f"{cls.__name__}_{version.upper()}"
        new_schema = type(class_name, (cls,), {})
        
        # Remove excluded fields
        for field in exclude_fields:
            if hasattr(new_schema, field):
                delattr(new_schema, field)
        
        return new_schema


class SchemaEvolutionMixin(BaseModel):
    """Mixin for handling schema evolution between versions."""
    
    @classmethod
    def migrate_from_version(cls, data: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
        """Migrate data from one schema version to another."""
        # This is a base implementation - specific schemas should override
        # to handle version-specific migrations
        return data
    
    @classmethod
    def get_backward_compatible_fields(cls) -> List[str]:
        """Get fields that are backward compatible across versions."""
        return []
    
    @classmethod
    def get_deprecated_fields(cls, version: str) -> List[str]:
        """Get fields that are deprecated in a specific version."""
        return []


# Enhanced schema validation utilities
def validate_schema_compatibility(schema_v1: type, schema_v2: type) -> Dict[str, Any]:
    """Validate compatibility between two schema versions."""
    compatibility_report = {
        'compatible': True,
        'issues': [],
        'warnings': []
    }
    
    v1_fields = set(schema_v1.model_fields.keys())
    v2_fields = set(schema_v2.model_fields.keys())
    
    # Check for removed fields
    removed_fields = v1_fields - v2_fields
    if removed_fields:
        compatibility_report['issues'].append(f"Fields removed in v2: {removed_fields}")
        compatibility_report['compatible'] = False
    
    # Check for added required fields
    added_fields = v2_fields - v1_fields
    for field in added_fields:
        field_info = schema_v2.model_fields[field]
        if field_info.is_required():
            compatibility_report['warnings'].append(f"New required field in v2: {field}")
    
    return compatibility_report


def create_schema_validator(schema_class: type, version: str):
    """Create a version-aware schema validator."""
    def validator(data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            validated = schema_class(**data)
            return validated.model_dump()
        except Exception as e:
            raise ValueError(f"Schema validation failed for version {version}: {str(e)}")
    
    return validator


# Schema validation utilities
def create_response_model(data_model: type, version: str = "v1") -> type:
    """
    Create a versioned response model wrapping the data model.
    
    Args:
        data_model: The Pydantic model for the data
        version: API version string
    
    Returns:
        A new response model class
    """
    version_default = version
    class ResponseModel(BaseSchema):
        success: bool = Field(True, description="Operation success flag")
        data: data_model = Field(description="Response data")
        version: str = Field(default=version_default, description="API version")
    
    ResponseModel.__name__ = f"{data_model.__name__}Response"
    return ResponseModel


def create_list_response_model(data_model: type, version: str = "v1") -> type:
    """
    Create a versioned paginated list response model.
    
    Args:
        data_model: The Pydantic model for list items
        version: API version string
    
    Returns:
        A new list response model class
    """
    from typing import List
    version_default= version
    class ListResponseModel(BaseSchema):
        success: bool = Field(True, description="Operation success flag")
        data: List[data_model] = Field(description="List of items")
        pagination: PaginationResponse = Field(description="Pagination metadata")
        version: str = Field(default=version_default, description="API version")
    
    ListResponseModel.__name__ = f"{data_model.__name__}ListResponse"
    return ListResponseModel


# Additional schema validation utilities
def validate_version_compatibility_detailed(schema_v1: type, schema_v2: type) -> Dict[str, Any]:
    """
    Detailed validation of compatibility between two schema versions.
    
    Args:
        schema_v1: First schema version
        schema_v2: Second schema version
    
    Returns:
        Detailed compatibility report
    """
    compatibility_report = {
        'compatible': True,
        'breaking_changes': [],
        'non_breaking_changes': [],
        'warnings': []
    }
    
    v1_fields = set(schema_v1.model_fields.keys())
    v2_fields = set(schema_v2.model_fields.keys())
    
    # Check for removed fields (breaking change)
    removed_fields = v1_fields - v2_fields
    if removed_fields:
        compatibility_report['breaking_changes'].append(
            f"Fields removed in v2: {list(removed_fields)}"
        )
        compatibility_report['compatible'] = False
    
    # Check for added fields
    added_fields = v2_fields - v1_fields
    for field in added_fields:
        field_info = schema_v2.model_fields[field]
        if hasattr(field_info, 'default') and field_info.default is not None:
            compatibility_report['non_breaking_changes'].append(
                f"New optional field in v2: {field}"
            )
        else:
            compatibility_report['warnings'].append(
                f"New required field in v2: {field}"
            )
    
    return compatibility_report


# Cross-version schema utilities
class SchemaVersionManager:
    """Manager for handling schema versions and migrations."""
    
    def __init__(self):
        self.version_schemas = {}
        self.migration_rules = {}
    
    def register_schema(self, version: str, resource: str, schema_class: type):
        """Register a schema for a specific version and resource."""
        if version not in self.version_schemas:
            self.version_schemas[version] = {}
        self.version_schemas[version][resource] = schema_class
    
    def register_migration(self, from_version: str, to_version: str, migration_func):
        """Register a migration function between versions."""
        migration_key = f"{from_version}_to_{to_version}"
        self.migration_rules[migration_key] = migration_func
    
    def get_schema(self, version: str, resource: str) -> Optional[type]:
        """Get schema class for a specific version and resource."""
        return self.version_schemas.get(version, {}).get(resource)
    
    def migrate_data(self, data: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
        """Migrate data from one version to another."""
        migration_key = f"{from_version}_to_{to_version}"
        migration_func = self.migration_rules.get(migration_key)
        
        if migration_func:
            return migration_func(data)
        else:
            # Default migration - return data as-is
            return data
    
    def validate_cross_version_compatibility(self, v1_schema: type, v2_schema: type) -> bool:
        """Validate that two schema versions are compatible."""
        try:
            compatibility_report = validate_schema_compatibility(v1_schema, v2_schema)
            return compatibility_report['compatible']
        except Exception:
            return False


# Global schema version manager instance
schema_manager = SchemaVersionManager()


# Schema inheritance patterns for version evolution
def create_versioned_schema(base_schema: type, version: str, additional_fields: Dict[str, Any] = None):
    """
    Create a versioned schema based on a base schema.
    
    Args:
        base_schema: Base schema class
        version: Version identifier
        additional_fields: Additional fields for this version
    
    Returns:
        New versioned schema class
    """
    additional_fields = additional_fields or {}
    
    class_name = f"{base_schema.__name__}_{version.upper()}"
    
    # Create new class with additional fields
    class_dict = {
        '__module__': base_schema.__module__,
        '__qualname__': class_name,
        **additional_fields
    }
    
    versioned_schema = type(class_name, (base_schema,), class_dict)
    return versioned_schema


# Validation utilities that work across versions
def validate_with_version_fallback(
    data: Dict[str, Any], 
    primary_schema: type, 
    fallback_schema: type = None
) -> Dict[str, Any]:
    """
    Validate data with primary schema, falling back to secondary if needed.
    
    Args:
        data: Data to validate
        primary_schema: Primary schema to try first
        fallback_schema: Fallback schema if primary fails
    
    Returns:
        Validated data
    """
    try:
        validated = primary_schema(**data)
        return validated.model_dump()
    except Exception as primary_error:
        if fallback_schema:
            try:
                validated = fallback_schema(**data)
                return validated.model_dump()
            except Exception:
                raise primary_error
        else:
            raise primary_error


def create_schema_validator_chain(*schema_classes):
    """
    Create a validator that tries multiple schemas in order.
    
    Args:
        *schema_classes: Schema classes to try in order
    
    Returns:
        Validator function
    """
    def validator(data: Dict[str, Any]) -> Dict[str, Any]:
        last_error = None
        
        for schema_class in schema_classes:
            try:
                validated = schema_class(**data)
                return validated.model_dump()
            except Exception as e:
                last_error = e
                continue
        
        raise ValueError(f"Data validation failed for all schemas: {last_error}")
    
    return validator


# Schema comparison utilities
def compare_schema_fields(schema1: type, schema2: type) -> Dict[str, Any]:
    """
    Compare fields between two schemas.
    
    Args:
        schema1: First schema
        schema2: Second schema
    
    Returns:
        Comparison report
    """
    fields1 = set(schema1.model_fields.keys())
    fields2 = set(schema2.model_fields.keys())
    
    return {
        'common_fields': list(fields1 & fields2),
        'schema1_only': list(fields1 - fields2),
        'schema2_only': list(fields2 - fields1),
        'total_fields_schema1': len(fields1),
        'total_fields_schema2': len(fields2)
    }


def get_schema_field_types(schema: type) -> Dict[str, str]:
    """
    Get field types for a schema.
    
    Args:
        schema: Schema class
    
    Returns:
        Dictionary mapping field names to type strings
    """
    field_types = {}
    for field_name, field_info in schema.model_fields.items():
        field_types[field_name] = str(field_info.annotation)
    return field_types