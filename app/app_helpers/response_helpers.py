"""
Response formatting helpers for consistent API responses across all versions.
Provides standardized response formats for success, error, and paginated responses.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import uuid


def success_response(
    data: Any = None,
    message: str = "Operation successful",
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized success response.
    
    Args:
        data: Response data payload
        message: Success message
        meta: Additional metadata
        
    Returns:
        Dict: Standardized success response
        
    Example:
        {
            "success": true,
            "message": "User retrieved successfully",
            "data": {...},
            "meta": {...},
            "timestamp": "2024-01-15T10:30:00Z"
        }
    """
    response = {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    if meta:
        response["meta"] = meta
    
    return response


def created_response(
    data: Any = None,
    message: str = "Resource created successfully",
    resource_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized created response (HTTP 201).
    
    Args:
        data: Created resource data
        message: Success message
        resource_id: ID of the created resource
        meta: Additional metadata
        
    Returns:
        Dict: Standardized created response
    """
    response_meta = meta or {}
    if resource_id:
        response_meta["resource_id"] = resource_id
    
    return success_response(
        data=data,
        message=message,
        meta=response_meta
    )


def paginated_response(
    data: List[Any],
    total: int,
    page: int,
    size: int,
    message: str = "Data retrieved successfully",
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized paginated response.
    
    Args:
        data: List of items for current page
        total: Total number of items
        page: Current page number
        size: Page size
        message: Success message
        meta: Additional metadata
        
    Returns:
        Dict: Standardized paginated response
        
    Example:
        {
            "success": true,
            "message": "Users retrieved successfully",
            "data": [...],
            "pagination": {
                "total": 100,
                "page": 1,
                "size": 20,
                "pages": 5,
                "has_next": true,
                "has_prev": false
            },
            "timestamp": "2024-01-15T10:30:00Z"
        }
    """
    pages = (total + size - 1) // size  # Ceiling division
    has_next = page < pages
    has_prev = page > 1
    
    pagination_meta = {
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "has_next": has_next,
        "has_prev": has_prev
    }
    
    response_meta = meta or {}
    response_meta["pagination"] = pagination_meta
    
    return success_response(
        data=data,
        message=message,
        meta=response_meta
    )


def error_response(
    message: str = "An error occurred",
    error_code: str = "INTERNAL_ERROR",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        message: Error message
        error_code: Standardized error code
        details: Additional error details
        request_id: Request ID for tracking
        
    Returns:
        Dict: Standardized error response
        
    Example:
        {
            "success": false,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input data",
                "details": {...},
                "request_id": "req_123456789"
            },
            "timestamp": "2024-01-15T10:30:00Z"
        }
    """
    error_data = {
        "code": error_code,
        "message": message
    }
    
    if details:
        error_data["details"] = details
    
    if request_id:
        error_data["request_id"] = request_id
    
    return {
        "success": False,
        "error": error_data,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def validation_error_response(
    message: str = "Validation failed",
    field_errors: Optional[List[Dict[str, Any]]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized validation error response.
    
    Args:
        message: Validation error message
        field_errors: List of field-specific errors
        request_id: Request ID for tracking
        
    Returns:
        Dict: Standardized validation error response
    """
    details = {}
    if field_errors:
        details["field_errors"] = field_errors
    
    return error_response(
        message=message,
        error_code="VALIDATION_ERROR",
        details=details,
        request_id=request_id
    )


def not_found_response(
    resource_type: str = "Resource",
    resource_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized not found error response.
    
    Args:
        resource_type: Type of resource that was not found
        resource_id: ID of the resource that was not found
        request_id: Request ID for tracking
        
    Returns:
        Dict: Standardized not found error response
    """
    message = f"{resource_type} not found"
    details = {"resource_type": resource_type}
    
    if resource_id:
        details["resource_id"] = resource_id
        message = f"{resource_type} with ID '{resource_id}' not found"
    
    return error_response(
        message=message,
        error_code="NOT_FOUND",
        details=details,
        request_id=request_id
    )


def unauthorized_response(
    message: str = "Authentication required",
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized unauthorized error response.
    
    Args:
        message: Unauthorized error message
        request_id: Request ID for tracking
        
    Returns:
        Dict: Standardized unauthorized error response
    """
    return error_response(
        message=message,
        error_code="AUTHENTICATION_ERROR",
        request_id=request_id
    )


def forbidden_response(
    message: str = "Access denied",
    required_role: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized forbidden error response.
    
    Args:
        message: Forbidden error message
        required_role: Required role for access
        request_id: Request ID for tracking
        
    Returns:
        Dict: Standardized forbidden error response
    """
    details = {}
    if required_role:
        details["required_role"] = required_role
    
    return error_response(
        message=message,
        error_code="AUTHORIZATION_ERROR",
        details=details,
        request_id=request_id
    )


def generate_request_id() -> str:
    """
    Generate a unique request ID for tracking.
    
    Returns:
        str: Unique request ID
    """
    return f"req_{uuid.uuid4().hex[:12]}"