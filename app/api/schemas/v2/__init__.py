"""
V2 API Schemas - Version-specific request/response models.

This module contains all Pydantic schemas for API version 2.
These schemas define the structure of requests and responses for V2 endpoints,
including enhanced features, additional fields, and improved validation
not available in V1.
"""

from typing import Type, Any, Dict, Optional
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
API_VERSION = "v2"

# V2-specific base classes
class V2BaseSchema(BaseSchema, VersionedSchemaMixin):
    """Base schema for all V2 API models with enhanced features."""
    
    class Config:
        # V2 specific configuration - more flexible than V1
        extra = "ignore"  # V2 allows extra fields for forward compatibility
        validate_assignment = True
        str_strip_whitespace = True
        use_enum_values = True


class V2ResponseMixin(BaseSchema):
    """Enhanced mixin for V2 response formatting with metadata support."""
    
    version: str = API_VERSION
    
    @classmethod
    def create_success_response(
        cls, 
        data: Any, 
        message: str = "Success",
        metadata: Optional[Dict] = None
    ):
        """Create a standardized V2 success response with metadata."""
        response = {
            "success": True,
            "message": message,
            "data": data,
            "version": API_VERSION
        }
        if metadata:
            response["metadata"] = metadata
        return response
    
    @classmethod
    def create_error_response(
        cls, 
        message: str, 
        error_code: str = None,
        details: Optional[Dict] = None
    ):
        """Create a standardized V2 error response with details."""
        response = {
            "success": False,
            "message": message,
            "version": API_VERSION
        }
        if error_code:
            response["error_code"] = error_code
        if details:
            response["details"] = details
        return response


class V2PaginatedResponse(V2ResponseMixin):
    """V2 enhanced paginated response structure with additional metadata."""
    
    @classmethod
    def create_paginated_response(
        cls, 
        data: list, 
        total: int, 
        page: int, 
        per_page: int,
        filters: Optional[Dict] = None,
        sort: Optional[Dict] = None
    ):
        """Create a V2 paginated response with enhanced metadata."""
        response = {
            "success": True,
            "data": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
                "has_next": page * per_page < total,
                "has_prev": page > 1
            },
            "version": API_VERSION
        }
        
        # Add query metadata
        query_info = {}
        if filters:
            query_info["filters"] = filters
        if sort:
            query_info["sort"] = sort
        if query_info:
            response["query"] = query_info
            
        return response


class V2MetadataMixin(BaseSchema):
    """Mixin for V2 schemas that support metadata fields."""
    
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[list] = None
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to the schema instance."""
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value
    
    def add_tag(self, tag: str):
        """Add a tag to the schema instance."""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)


class V2AuditMixin(TimestampMixin):
    """Enhanced audit mixin for V2 with additional tracking fields."""
    
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    version_number: Optional[int] = None
    
    def set_audit_info(self, user_id: str, is_create: bool = False):
        """Set audit information for the schema."""
        if is_create:
            self.created_by = user_id
        else:
            self.updated_by = user_id


# Helper functions for creating V2 response models
def create_v2_response(data_model: Type) -> Type:
    """Create a V2 response model wrapper with enhanced features."""
    return create_response_model(data_model, API_VERSION)


def create_v2_list_response(data_model: Type) -> Type:
    """Create a V2 list response model wrapper with enhanced pagination."""
    return create_list_response_model(data_model, API_VERSION)


# Enhanced schema validation utilities for V2
def validate_v2_schema(data: dict, schema_class: Type) -> dict:
    """Validate data against V2 schema with V2-specific enhancements."""
    try:
        validated = schema_class(**data)
        return validated.model_dump(exclude_unset=True, exclude_none=True)
    except Exception as e:
        raise ValueError(f"V2 schema validation failed: {str(e)}") from e


def validate_v2_with_fallback(data: dict, v2_schema: Type, v1_schema: Type) -> dict:
    """Validate V2 schema with V1 fallback for backward compatibility."""
    try:
        return validate_v2_schema(data, v2_schema)
    except ValueError:
        # Try V1 schema as fallback
        try:
            v1_data = validate_v1_schema(data, v1_schema)
            # Migrate V1 to V2 format
            return V2EvolutionMixin.migrate_from_v1(v1_data)
        except Exception as e:
            raise ValueError(f"Schema validation failed for both V2 and V1: {str(e)}") from e


# V2 Schema evolution patterns
class V2EvolutionMixin(SchemaEvolutionMixin):
    """V2-specific schema evolution utilities."""
    
    @classmethod
    def get_v2_enhanced_fields(cls) -> list:
        """Get fields that are enhanced/new in V2."""
        return ["metadata", "tags", "preferences", "settings"]
    
    @classmethod
    def migrate_from_v1(cls, v1_data: dict) -> dict:
        """Migrate V1 data to V2 format with enhancements."""
        v2_data = v1_data.copy()
        
        # Add V2-specific enhancements
        if "metadata" not in v2_data:
            v2_data["metadata"] = {"migrated_from": "v1"}
        if "tags" not in v2_data:
            v2_data["tags"] = []
        if "preferences" not in v2_data:
            v2_data["preferences"] = {}
        if "settings" not in v2_data:
            v2_data["settings"] = {}
            
        return v2_data
    
    @classmethod
    def get_backward_compatible_fields(cls) -> list:
        """Get fields that are backward compatible with V1."""
        return ["id", "created_at", "updated_at", "name", "email", "phone_number"]
    
    @classmethod
    def strip_v2_enhancements(cls, v2_data: dict) -> dict:
        """Strip V2-specific fields for V1 compatibility."""
        v1_compatible = v2_data.copy()
        v2_only_fields = cls.get_v2_enhanced_fields()
        
        for field in v2_only_fields:
            v1_compatible.pop(field, None)
            
        return v1_compatible


# Import validation utilities from V1 for compatibility
from ..v1 import validate_v1_schema

# Export all base components
__all__ = [
    # Base classes
    "BaseSchema",
    "V2BaseSchema",
    "V2ResponseMixin",
    "V2PaginatedResponse",
    "V2MetadataMixin",
    "V2AuditMixin",
    "TimestampMixin",
    "IDMixin",
    "PaginationRequest",
    "PaginationResponse",
    "SuccessResponse",
    "ErrorResponse",
    
    # Helper functions
    "create_v2_response",
    "create_v2_list_response",
    "validate_v2_schema",
    "validate_v2_with_fallback",
    
    # Evolution utilities
    "V2EvolutionMixin",
    "VersionedSchemaMixin",
    "SchemaEvolutionMixin",
    
    # Constants
    "API_VERSION"
]