"""
Custom exception classes and error handling for the Veterinary Clinic Backend.
Provides consistent error responses across all API versions.
"""

from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


class VetClinicException(Exception):
    """Base exception for veterinary clinic application."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(VetClinicException):
    """Data validation errors."""
    
    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        if value is not None:
            error_details["value"] = str(value)
            
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=error_details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class AuthenticationError(VetClinicException):
    """Authentication and authorization errors."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(VetClinicException):
    """Authorization and permission errors."""
    
    def __init__(
        self,
        message: str = "Access denied",
        required_role: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if required_role:
            error_details["required_role"] = required_role
            
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=error_details,
            status_code=status.HTTP_403_FORBIDDEN
        )


class NotFoundError(VetClinicException):
    """Resource not found errors."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        if resource_id:
            error_details["resource_id"] = resource_id
            
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            details=error_details,
            status_code=status.HTTP_404_NOT_FOUND
        )


class BusinessLogicError(VetClinicException):
    """Business rule violations."""
    
    def __init__(
        self,
        message: str = "Business rule violation",
        rule: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if rule:
            error_details["rule"] = rule
            
        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            details=error_details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class ConflictError(VetClinicException):
    """Resource conflict errors."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        conflicting_resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if conflicting_resource:
            error_details["conflicting_resource"] = conflicting_resource
            
        super().__init__(
            message=message,
            error_code="CONFLICT_ERROR",
            details=error_details,
            status_code=status.HTTP_409_CONFLICT
        )


class RateLimitError(VetClinicException):
    """Rate limiting errors."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if retry_after:
            error_details["retry_after"] = retry_after
            
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            details=error_details,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class ExternalServiceError(VetClinicException):
    """External service integration errors."""
    
    def __init__(
        self,
        message: str = "External service error",
        service_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if service_name:
            error_details["service_name"] = service_name
            
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=error_details,
            status_code=status.HTTP_502_BAD_GATEWAY
        )


def create_http_exception(
    exception: VetClinicException,
    request_id: Optional[str] = None
) -> HTTPException:
    """
    Convert VetClinicException to FastAPI HTTPException.
    
    Args:
        exception: The VetClinicException to convert
        request_id: Optional request ID for tracking
        
    Returns:
        HTTPException: FastAPI compatible exception
    """
    error_detail = {
        "error": {
            "code": exception.error_code,
            "message": exception.message,
            "details": exception.details,
        }
    }
    
    if request_id:
        error_detail["error"]["request_id"] = request_id
    
    return HTTPException(
        status_code=exception.status_code,
        detail=error_detail
    )


def handle_database_error(error: Exception) -> VetClinicException:
    """
    Convert database errors to appropriate VetClinicException.
    
    Args:
        error: The database error to handle
        
    Returns:
        VetClinicException: Appropriate exception for the error
    """
    error_str = str(error).lower()
    
    # Handle common database errors
    if "unique constraint" in error_str or "duplicate key" in error_str:
        return ConflictError(
            message="Resource already exists",
            details={"database_error": str(error)}
        )
    elif "foreign key constraint" in error_str:
        return ValidationError(
            message="Invalid reference to related resource",
            details={"database_error": str(error)}
        )
    elif "not null constraint" in error_str:
        return ValidationError(
            message="Required field is missing",
            details={"database_error": str(error)}
        )
    elif "check constraint" in error_str:
        return ValidationError(
            message="Data validation failed",
            details={"database_error": str(error)}
        )
    else:
        # Generic database error
        logger.error(f"Unhandled database error: {error}")
        return VetClinicException(
            message="Database operation failed",
            error_code="DATABASE_ERROR",
            details={"database_error": str(error)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def handle_validation_error(error: Exception) -> ValidationError:
    """
    Convert Pydantic validation errors to ValidationError.
    
    Args:
        error: The validation error to handle
        
    Returns:
        ValidationError: Formatted validation error
    """
    if hasattr(error, 'errors'):
        # Pydantic validation error
        errors = error.errors()
        if errors:
            first_error = errors[0]
            field = ".".join(str(loc) for loc in first_error.get('loc', []))
            message = first_error.get('msg', 'Validation failed')
            
            return ValidationError(
                message=message,
                field=field,
                details={"validation_errors": errors}
            )
    
    return ValidationError(
        message=str(error),
        details={"validation_error": str(error)}
    )