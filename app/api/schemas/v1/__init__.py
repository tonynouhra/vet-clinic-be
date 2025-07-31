
"""
V1 API Schemas - Version-specific request/response models.

This module contains all Pydantic schemas for API version 1.
These schemas define the structure of requests and responses for V1 endpoints.
V1 represents the basic/legacy API contract with essential fields only.
"""

from typing import Type, Any
from pydantic import ConfigDict
from ..base import (
    BaseSchema,
    TimestampMixin,
    IDMixin,
    PaginationRequest,
    PaginationResponse,
    SuccessResponse,
    ErrorResponse,
    create_response_model,
    create_list_response_model,
    VersionedSchemaMixin,
    SchemaEvolutionMixin
)

# Version identifier for this schema package
API_VERSION = "v1"

# V1-specific base classes
class V1BaseSchema(BaseSchema, VersionedSchemaMixin):
    """Base schema for all V1 API models with version-specific features."""

    model_config = ConfigDict(
        # V1 specific configuration - explicit field whitelisting
        extra = "ignore",  # Ignore extra fields not defined in schema (explicit whitelisting)
        validate_assignment = True,
        str_strip_whitespace = True,
        from_attributes = True
    )


class V1ResponseMixin(BaseSchema):
    """Mixin for V1 response formatting."""
    
    version: str = API_VERSION
    
    @classmethod
    def create_success_response(cls, data: Any, message: str = "Success"):
        """Create a standardized V1 success response."""
        return {
            "success": True,
            "message": message,
            "data": data,
            "version": API_VERSION
        }
    
    @classmethod
    def create_error_response(cls, message: str, error_code: str = None):
        """Create a standardized V1 error response."""
        return {
            "success": False,
            "message": message,
            "error_code": error_code,
            "version": API_VERSION
        }


class V1PaginatedResponse(V1ResponseMixin):
    """V1 paginated response structure."""
    
    @classmethod
    def create_paginated_response(cls, data: list, total: int, page: int, per_page: int):
        """Create a V1 paginated response."""
        return {
            "success": True,
            "data": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            },
            "version": API_VERSION
        }


# Helper functions for creating V1 response models
def create_v1_response(data_model: Type) -> Type:
    """Create a V1 response model wrapper."""
    return create_response_model(data_model, API_VERSION)


def create_v1_list_response(data_model: Type) -> Type:
    """Create a V1 list response model wrapper."""
    return create_list_response_model(data_model, API_VERSION)


# Schema validation utilities for V1
def validate_v1_schema(data: dict, schema_class: Type) -> dict:
    """Validate data against V1 schema with V1-specific rules."""
    try:
        validated = schema_class(**data)
        return validated.model_dump(exclude_unset=True)
    except Exception as e:
        raise ValueError(f"V1 schema validation failed: {str(e)}") from e


# V1 Schema evolution patterns
class V1EvolutionMixin(SchemaEvolutionMixin):
    """V1-specific schema evolution utilities."""
    
    @classmethod
    def get_v1_core_fields(cls) -> list:
        """Get core fields that should be present in all V1 schemas."""
        return ["id", "created_at", "updated_at"]
    
    @classmethod
    def migrate_to_v2(cls, data: dict) -> dict:
        """Migrate V1 data to V2 format."""
        # V1 to V2 migration logic - add default values for new V2 fields
        v2_data = data.copy()
        
        # Add V2-specific defaults if they don't exist
        if "preferences" not in v2_data:
            v2_data["preferences"] = {}
        if "metadata" not in v2_data:
            v2_data["metadata"] = {}
            
        return v2_data


# Export all base components
__all__ = [
    # Base classes
    "BaseSchema",
    "V1BaseSchema",
    "V1ResponseMixin",
    "V1PaginatedResponse",
    "TimestampMixin",
    "IDMixin",
    "PaginationRequest",
    "PaginationResponse",
    "SuccessResponse",
    "ErrorResponse",
    
    # Helper functions
    "create_v1_response",
    "create_v1_list_response",
    "validate_v1_schema",
    
    # Evolution utilities
    "V1EvolutionMixin",
    "VersionedSchemaMixin",
    "SchemaEvolutionMixin",
    
    # Constants
    "API_VERSION"
]