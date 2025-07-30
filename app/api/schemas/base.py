"""
Base schema patterns and utilities for API versioning.

Provides common schema patterns, validation utilities, and base classes
that can be used across different API versions.
"""

from typing import Optional, Any, Dict
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
    class ResponseModel(BaseSchema):
        success: bool = Field(True, description="Operation success flag")
        data: data_model = Field(description="Response data")
        version: str = Field(version, description="API version")
    
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
    
    class ListResponseModel(BaseSchema):
        success: bool = Field(True, description="Operation success flag")
        data: List[data_model] = Field(description="List of items")
        pagination: PaginationResponse = Field(description="Pagination metadata")
        version: str = Field(version, description="API version")
    
    ListResponseModel.__name__ = f"{data_model.__name__}ListResponse"
    return ListResponseModel