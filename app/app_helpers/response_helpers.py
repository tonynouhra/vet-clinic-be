"""
Response formatting helper functions.
"""
from typing import Any, Dict, Optional
from datetime import datetime
import uuid


def success_response(
    data: Any,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized success response.
    
    Args:
        data: Response data
        message: Optional success message
        meta: Optional metadata
        
    Returns:
        Dict: Formatted success response
    """
    response = {
        "success": True,
        "data": data,
        "meta": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": str(uuid.uuid4()),
            **(meta or {})
        }
    }
    
    if message:
        response["message"] = message
        
    return response


def error_response(
    message: str,
    error_code: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 400
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        message: Error message
        error_code: Error code identifier
        details: Optional error details
        status_code: HTTP status code
        
    Returns:
        Dict: Formatted error response
    """
    return {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "details": details,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": str(uuid.uuid4())
        },
        "meta": {
            "status_code": status_code
        }
    }


def paginated_response(
    data: list,
    total: int,
    page: int,
    size: int,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized paginated response.
    
    Args:
        data: List of items for current page
        total: Total number of items
        page: Current page number (1-based)
        size: Items per page
        message: Optional message
        
    Returns:
        Dict: Formatted paginated response
    """
    total_pages = (total + size - 1) // size  # Ceiling division
    
    pagination_meta = {
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    }
    
    return success_response(
        data=data,
        message=message,
        meta=pagination_meta
    )


def created_response(
    data: Any,
    message: str = "Resource created successfully"
) -> Dict[str, Any]:
    """
    Create a standardized response for resource creation.
    
    Args:
        data: Created resource data
        message: Success message
        
    Returns:
        Dict: Formatted creation response
    """
    return success_response(
        data=data,
        message=message,
        meta={"status_code": 201}
    )


def updated_response(
    data: Any,
    message: str = "Resource updated successfully"
) -> Dict[str, Any]:
    """
    Create a standardized response for resource updates.
    
    Args:
        data: Updated resource data
        message: Success message
        
    Returns:
        Dict: Formatted update response
    """
    return success_response(
        data=data,
        message=message,
        meta={"status_code": 200}
    )


def deleted_response(
    message: str = "Resource deleted successfully"
) -> Dict[str, Any]:
    """
    Create a standardized response for resource deletion.
    
    Args:
        message: Success message
        
    Returns:
        Dict: Formatted deletion response
    """
    return success_response(
        data=None,
        message=message,
        meta={"status_code": 204}
    )