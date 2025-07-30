"""
Common helper functions and utilities used across the application.
"""
from .auth_helpers import get_current_user, verify_permissions, require_role
from .validation_helpers import validate_uuid, validate_email, validate_phone
from .response_helpers import success_response, error_response, paginated_response
from .pagination_helpers import get_pagination_params, create_pagination_meta
from .error_helpers import handle_database_error, handle_validation_error
from .dependency_helpers import (
    get_controller, 
    get_service, 
    inject_controller_and_service,
    create_versioned_dependency,
    with_transaction
)

__all__ = [
    # Auth helpers
    "get_current_user",
    "verify_permissions", 
    "require_role",
    
    # Validation helpers
    "validate_uuid",
    "validate_email",
    "validate_phone",
    
    # Response helpers
    "success_response",
    "error_response",
    "paginated_response",
    
    # Pagination helpers
    "get_pagination_params",
    "create_pagination_meta",
    
    # Error helpers
    "handle_database_error",
    "handle_validation_error",
    
    # Dependency helpers
    "get_controller",
    "get_service",
    "inject_controller_and_service",
    "create_versioned_dependency",
    "with_transaction",
]