"""
App helpers package for shared utilities across all API versions.
Provides authentication, response formatting, validation, and dependency injection utilities.
"""

from .auth_helpers import get_current_user, require_role, verify_token
from .response_helpers import (
    success_response,
    created_response,
    paginated_response,
    error_response
)
from .validation_helpers import (
    validate_pagination_params,
    validate_uuid,
    validate_email,
    validate_phone_number
)
from .dependency_helpers import get_controller, get_service

__all__ = [
    # Auth helpers
    "get_current_user",
    "require_role", 
    "verify_token",
    
    # Response helpers
    "success_response",
    "created_response",
    "paginated_response",
    "error_response",
    
    # Validation helpers
    "validate_pagination_params",
    "validate_uuid",
    "validate_email",
    "validate_phone_number",
    
    # Dependency helpers
    "get_controller",
    "get_service",
]