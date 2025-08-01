"""
Common helper functions and utilities used across the application.
"""
# Enhanced auth helpers
from .auth_helpers import (
    get_current_user, 
    verify_permissions, 
    require_role,
    get_user_context,
    require_permission,
    require_any_permission,
    create_version_aware_auth_dependency,
    UserContext,
    Permission
)

# Enhanced validation helpers
from .validation_helpers import (
    validate_uuid, 
    validate_email, 
    validate_phone, 
    validate_pagination_params,
    validate_date_range,
    validate_sort_params,
    validate_decimal,
    validate_string_length,
    validate_enum_value,
    BusinessRuleValidator,
    ValidationError,
    create_version_aware_validator
)

# Enhanced response helpers
from .response_helpers import (
    success_response, 
    error_response, 
    paginated_response,
    created_response,
    updated_response,
    deleted_response,
    validation_error_response,
    not_found_response,
    unauthorized_response,
    forbidden_response,
    ResponseFormat,
    get_response_format_for_version
)

# Operation helpers
from .operation_helpers import (
    log_operation,
    ActivityTracker,
    DataTransformer,
    BusinessOperationHelper,
    OperationType,
    AuditLevel,
    generate_operation_id,
    create_operation_context
)

# Legacy imports for backward compatibility
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
    # Enhanced auth helpers
    "get_current_user",
    "verify_permissions", 
    "require_role",
    "get_user_context",
    "require_permission",
    "require_any_permission",
    "create_version_aware_auth_dependency",
    "UserContext",
    "Permission",
    
    # Enhanced validation helpers
    "validate_uuid",
    "validate_email",
    "validate_phone",
    "validate_pagination_params",
    "validate_date_range",
    "validate_sort_params",
    "validate_decimal",
    "validate_string_length",
    "validate_enum_value",
    "BusinessRuleValidator",
    "ValidationError",
    "create_version_aware_validator",
    
    # Enhanced response helpers
    "success_response",
    "error_response",
    "paginated_response",
    "created_response",
    "updated_response",
    "deleted_response",
    "validation_error_response",
    "not_found_response",
    "unauthorized_response",
    "forbidden_response",
    "ResponseFormat",
    "get_response_format_for_version",
    
    # Operation helpers
    "log_operation",
    "ActivityTracker",
    "DataTransformer",
    "BusinessOperationHelper",
    "OperationType",
    "AuditLevel",
    "generate_operation_id",
    "create_operation_context",
    
    # Legacy helpers (backward compatibility)
    "get_pagination_params",
    "create_pagination_meta",
    "handle_database_error",
    "handle_validation_error",
    "get_controller",
    "get_service",
    "inject_controller_and_service",
    "create_versioned_dependency",
    "with_transaction",
]