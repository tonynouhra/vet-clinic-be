"""
Custom exception classes and error handling utilities for the application.

This module provides a comprehensive exception hierarchy and utilities for
consistent error handling across all API versions.
"""
from typing import Any, Dict, Optional, List
from fastapi import HTTPException, status
from datetime import datetime
import uuid


class VetClinicException(Exception):
    """Base exception class for the application."""
    
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(VetClinicException):
    """Raised when validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details)


class AuthenticationError(VetClinicException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTHENTICATION_ERROR")


class AuthorizationError(VetClinicException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, "AUTHORIZATION_ERROR")


class NotFoundError(VetClinicException):
    """Raised when a resource is not found."""
    
    def __init__(self, message: str, resource: str = "Resource"):
        super().__init__(message, "NOT_FOUND", {"resource": resource})


class ConflictError(VetClinicException):
    """Raised when there's a conflict with existing data."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFLICT_ERROR", details)


class BusinessLogicError(VetClinicException):
    """Raised when business logic validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "BUSINESS_LOGIC_ERROR", details)


class DatabaseError(VetClinicException):
    """Raised when database operations fail."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATABASE_ERROR", details)


class ExternalServiceError(VetClinicException):
    """Raised when external service calls fail."""
    
    def __init__(self, message: str, service: str, details: Optional[Dict[str, Any]] = None):
        enhanced_details = {"service": service}
        if details:
            enhanced_details.update(details)
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", enhanced_details)


class RateLimitError(VetClinicException):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(message, "RATE_LIMIT_ERROR", details)


# Error handling utilities for consistent responses across API versions

def create_error_response(
    exception: VetClinicException,
    version: str = "v1",
    include_details: bool = True
) -> Dict[str, Any]:
    """
    Create a standardized error response from a VetClinicException.
    
    This utility ensures consistent error formatting across all API versions
    while allowing version-specific customizations.
    
    Args:
        exception: The VetClinicException to format
        version: API version (affects response format)
        include_details: Whether to include detailed error information
        
    Returns:
        Dict: Formatted error response
    """
    base_response = {
        "success": False,
        "error": {
            "code": exception.code,
            "message": exception.message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": str(uuid.uuid4())
        }
    }
    
    # Include details if requested and available
    if include_details and exception.details:
        base_response["error"]["details"] = exception.details
    
    # Version-specific formatting
    if version == "v2":
        # V2 might include additional metadata
        base_response["meta"] = {
            "api_version": version,
            "error_type": exception.__class__.__name__
        }
    
    return base_response


def exception_to_http_exception(exception: VetClinicException) -> HTTPException:
    """
    Convert a VetClinicException to an appropriate HTTPException.
    
    This utility maps custom exceptions to appropriate HTTP status codes
    for consistent API responses.
    
    Args:
        exception: The VetClinicException to convert
        
    Returns:
        HTTPException: FastAPI HTTPException with appropriate status code
    """
    status_code_mapping = {
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "AUTHENTICATION_ERROR": status.HTTP_401_UNAUTHORIZED,
        "AUTHORIZATION_ERROR": status.HTTP_403_FORBIDDEN,
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "CONFLICT_ERROR": status.HTTP_409_CONFLICT,
        "BUSINESS_LOGIC_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "EXTERNAL_SERVICE_ERROR": status.HTTP_502_BAD_GATEWAY,
        "RATE_LIMIT_ERROR": status.HTTP_429_TOO_MANY_REQUESTS,
        "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    
    status_code = status_code_mapping.get(exception.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Create error detail
    detail = {
        "code": exception.code,
        "message": exception.message,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": str(uuid.uuid4())
    }
    
    if exception.details:
        detail["details"] = exception.details
    
    return HTTPException(status_code=status_code, detail=detail)


def handle_service_exceptions(func):
    """
    Decorator to handle service layer exceptions and convert them to HTTP exceptions.
    
    This decorator can be applied to controller methods to automatically
    convert service exceptions to appropriate HTTP responses.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function that handles exceptions
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except VetClinicException as e:
            raise exception_to_http_exception(e)
        except Exception as e:
            # Handle unexpected exceptions
            internal_error = VetClinicException(
                message="An unexpected error occurred",
                code="INTERNAL_ERROR",
                details={"original_error": str(e)}
            )
            raise exception_to_http_exception(internal_error)
    
    return wrapper


class ErrorContext:
    """
    Context manager for enhanced error handling with additional context.
    
    This can be used to add contextual information to exceptions
    that occur within a specific operation.
    """
    
    def __init__(self, operation: str, resource: Optional[str] = None):
        self.operation = operation
        self.resource = resource
        self.context = {}
    
    def add_context(self, key: str, value: Any) -> None:
        """Add contextual information."""
        self.context[key] = value
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, VetClinicException):
            # Enhance the exception with context
            exc_val.details.update({
                "operation": self.operation,
                "resource": self.resource,
                **self.context
            })
        return False  # Don't suppress the exception


# Utility functions for common error scenarios

def raise_not_found(resource_type: str, identifier: str) -> None:
    """Raise a standardized not found error."""
    raise NotFoundError(
        message=f"{resource_type} not found",
        resource=resource_type
    )


def raise_validation_error(field: str, message: str, value: Any = None) -> None:
    """Raise a standardized validation error."""
    details = {"field": field}
    if value is not None:
        details["value"] = value
    
    raise ValidationError(
        message=f"Validation failed for {field}: {message}",
        details=details
    )


def raise_business_logic_error(rule: str, message: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Raise a standardized business logic error."""
    details = {"rule": rule}
    if context:
        details.update(context)
    
    raise BusinessLogicError(
        message=message,
        details=details
    )


def raise_conflict_error(resource_type: str, field: str, value: Any) -> None:
    """Raise a standardized conflict error."""
    raise ConflictError(
        message=f"{resource_type} already exists with {field}: {value}",
        details={
            "resource_type": resource_type,
            "conflicting_field": field,
            "conflicting_value": value
        }
    )