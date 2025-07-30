"""
V2 API Schemas - Version-specific request/response models.

This module contains all Pydantic schemas for API version 2.
These schemas define the structure of requests and responses for V2 endpoints,
including enhanced features and additional fields not available in V1.
"""

from ..base import (
    BaseSchema,
    TimestampMixin,
    IDMixin,
    PaginationRequest,
    PaginationResponse,
    SuccessResponse,
    ErrorResponse,
    create_response_model,
    create_list_response_model
)

# Version identifier for this schema package
API_VERSION = "v2"

# Helper functions for creating V2 response models
def create_v2_response(data_model: type):
    """Create a V2 response model."""
    return create_response_model(data_model, API_VERSION)

def create_v2_list_response(data_model: type):
    """Create a V2 list response model."""
    return create_list_response_model(data_model, API_VERSION)

# Import user schemas
from .users import *

__all__ = [
    "BaseSchema",
    "TimestampMixin", 
    "IDMixin",
    "PaginationRequest",
    "PaginationResponse",
    "SuccessResponse",
    "ErrorResponse",
    "create_v2_response",
    "create_v2_list_response",
    "API_VERSION"
]

# Add user schema exports
from .users import __all__ as user_schemas
__all__.extend(user_schemas)