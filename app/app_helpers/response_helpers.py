"""
Enhanced response formatting helper functions with version-aware support.

This module provides comprehensive response formatting utilities that work across all API versions,
including version-specific formatting, error handling, and specialized response types.
"""
from typing import Any, Dict, Optional, List, Union, Callable
from datetime import datetime
from enum import Enum
import uuid


class ResponseFormat(str, Enum):
    """Response format types for different API versions."""
    STANDARD = "standard"  # Default format
    MINIMAL = "minimal"    # Minimal response format
    DETAILED = "detailed"  # Detailed response format
    V1_LEGACY = "v1_legacy"  # Legacy V1 format
    V2_ENHANCED = "v2_enhanced"  # Enhanced V2 format


def success_response(
    data: Any,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    api_version: Optional[str] = None,
    response_format: ResponseFormat = ResponseFormat.STANDARD
) -> Dict[str, Any]:
    """
    Create a version-aware standardized success response.
    
    Args:
        data: Response data
        message: Optional success message
        meta: Optional metadata
        api_version: API version for version-specific formatting
        response_format: Response format type
        
    Returns:
        Dict: Formatted success response
    """
    # Base response structure
    base_meta = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": str(uuid.uuid4()),
    }
    
    # Add API version to metadata if provided
    if api_version:
        base_meta["api_version"] = api_version
    
    # Merge with provided metadata
    final_meta = {**base_meta, **(meta or {})}
    
    # Format response based on version and format type
    if response_format == ResponseFormat.MINIMAL:
        response = {"data": data}
        if message:
            response["message"] = message
        return response
    
    elif response_format == ResponseFormat.V1_LEGACY:
        # Legacy V1 format - simpler structure
        response = {
            "success": True,
            "data": data,
            "timestamp": final_meta["timestamp"]
        }
        if message:
            response["message"] = message
        return response
    
    elif response_format == ResponseFormat.V2_ENHANCED:
        # Enhanced V2 format with additional metadata
        response = {
            "success": True,
            "data": data,
            "meta": {
                **final_meta,
                "response_format": "v2_enhanced",
                "data_type": type(data).__name__ if data is not None else "null"
            }
        }
        if message:
            response["message"] = message
        return response
    
    else:  # STANDARD or DETAILED
        response = {
            "success": True,
            "data": data,
            "meta": final_meta
        }
        
        if message:
            response["message"] = message
        
        # Add detailed information for DETAILED format
        if response_format == ResponseFormat.DETAILED:
            response["meta"]["data_count"] = len(data) if isinstance(data, (list, dict)) else 1
            response["meta"]["response_size"] = len(str(data)) if data is not None else 0
            
        return response


def error_response(
    message: str,
    error_code: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 400,
    api_version: Optional[str] = None,
    response_format: ResponseFormat = ResponseFormat.STANDARD
) -> Dict[str, Any]:
    """
    Create a version-aware standardized error response.
    
    Args:
        message: Error message
        error_code: Error code identifier
        details: Optional error details
        status_code: HTTP status code
        api_version: API version for version-specific formatting
        response_format: Response format type
        
    Returns:
        Dict: Formatted error response
    """
    base_error = {
        "code": error_code,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": str(uuid.uuid4())
    }
    
    if details:
        base_error["details"] = details
    
    # Format error response based on version and format type
    if response_format == ResponseFormat.MINIMAL:
        return {
            "error": message,
            "code": error_code
        }
    
    elif response_format == ResponseFormat.V1_LEGACY:
        # Legacy V1 format - simpler error structure
        return {
            "success": False,
            "error": message,
            "error_code": error_code,
            "timestamp": base_error["timestamp"]
        }
    
    elif response_format == ResponseFormat.V2_ENHANCED:
        # Enhanced V2 format with additional error context
        error_response_data = {
            "success": False,
            "error": {
                **base_error,
                "severity": "error",
                "category": _categorize_error(status_code),
                "recoverable": _is_recoverable_error(status_code)
            },
            "meta": {
                "status_code": status_code,
                "api_version": api_version or "v2",
                "error_format": "v2_enhanced"
            }
        }
        return error_response_data
    
    else:  # STANDARD or DETAILED
        error_response_data = {
            "success": False,
            "error": base_error,
            "meta": {
                "status_code": status_code
            }
        }
        
        if api_version:
            error_response_data["meta"]["api_version"] = api_version
        
        # Add detailed error information for DETAILED format
        if response_format == ResponseFormat.DETAILED:
            error_response_data["error"]["severity"] = _get_error_severity(status_code)
            error_response_data["error"]["category"] = _categorize_error(status_code)
            error_response_data["meta"]["error_context"] = {
                "user_facing": status_code < 500,
                "retry_recommended": status_code in [429, 502, 503, 504]
            }
        
        return error_response_data


def _categorize_error(status_code: int) -> str:
    """Categorize error based on HTTP status code."""
    if 400 <= status_code < 500:
        return "client_error"
    elif 500 <= status_code < 600:
        return "server_error"
    else:
        return "unknown"


def _get_error_severity(status_code: int) -> str:
    """Get error severity based on HTTP status code."""
    if status_code in [400, 401, 403, 404, 422]:
        return "warning"
    elif status_code in [429, 502, 503, 504]:
        return "error"
    elif status_code >= 500:
        return "critical"
    else:
        return "info"


def _is_recoverable_error(status_code: int) -> bool:
    """Determine if error is recoverable."""
    return status_code in [429, 502, 503, 504]


def paginated_response(
    data: List[Any],
    total: int,
    page: int,
    size: int,
    message: Optional[str] = None,
    api_version: Optional[str] = None,
    response_format: ResponseFormat = ResponseFormat.STANDARD,
    additional_meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a version-aware standardized paginated response.
    
    Args:
        data: List of items for current page
        total: Total number of items
        page: Current page number (1-based)
        size: Items per page
        message: Optional message
        api_version: API version for version-specific formatting
        response_format: Response format type
        additional_meta: Additional metadata to include
        
    Returns:
        Dict: Formatted paginated response
    """
    total_pages = (total + size - 1) // size  # Ceiling division
    
    # Base pagination metadata
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
    
    # Add version-specific pagination metadata
    if response_format == ResponseFormat.V2_ENHANCED:
        pagination_meta["pagination"].update({
            "first_page": 1,
            "last_page": total_pages,
            "next_page": page + 1 if page < total_pages else None,
            "previous_page": page - 1 if page > 1 else None,
            "items_on_page": len(data),
            "offset": (page - 1) * size
        })
    
    # Merge with additional metadata
    final_meta = {**pagination_meta, **(additional_meta or {})}
    
    return success_response(
        data=data,
        message=message,
        meta=final_meta,
        api_version=api_version,
        response_format=response_format
    )


def created_response(
    data: Any,
    message: str = "Resource created successfully",
    api_version: Optional[str] = None,
    response_format: ResponseFormat = ResponseFormat.STANDARD,
    resource_id: Optional[str] = None,
    resource_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a version-aware standardized response for resource creation.
    
    Args:
        data: Created resource data
        message: Success message
        api_version: API version for version-specific formatting
        response_format: Response format type
        resource_id: ID of the created resource
        resource_type: Type of the created resource
        
    Returns:
        Dict: Formatted creation response
    """
    meta = {"status_code": 201}
    
    # Add resource metadata for enhanced formats
    if response_format in [ResponseFormat.V2_ENHANCED, ResponseFormat.DETAILED]:
        if resource_id:
            meta["resource_id"] = resource_id
        if resource_type:
            meta["resource_type"] = resource_type
        meta["operation"] = "create"
    
    return success_response(
        data=data,
        message=message,
        meta=meta,
        api_version=api_version,
        response_format=response_format
    )


def updated_response(
    data: Any,
    message: str = "Resource updated successfully",
    api_version: Optional[str] = None,
    response_format: ResponseFormat = ResponseFormat.STANDARD,
    resource_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    updated_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a version-aware standardized response for resource updates.
    
    Args:
        data: Updated resource data
        message: Success message
        api_version: API version for version-specific formatting
        response_format: Response format type
        resource_id: ID of the updated resource
        resource_type: Type of the updated resource
        updated_fields: List of fields that were updated
        
    Returns:
        Dict: Formatted update response
    """
    meta = {"status_code": 200}
    
    # Add resource metadata for enhanced formats
    if response_format in [ResponseFormat.V2_ENHANCED, ResponseFormat.DETAILED]:
        if resource_id:
            meta["resource_id"] = resource_id
        if resource_type:
            meta["resource_type"] = resource_type
        if updated_fields:
            meta["updated_fields"] = updated_fields
        meta["operation"] = "update"
    
    return success_response(
        data=data,
        message=message,
        meta=meta,
        api_version=api_version,
        response_format=response_format
    )


def deleted_response(
    message: str = "Resource deleted successfully",
    api_version: Optional[str] = None,
    response_format: ResponseFormat = ResponseFormat.STANDARD,
    resource_id: Optional[str] = None,
    resource_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a version-aware standardized response for resource deletion.
    
    Args:
        message: Success message
        api_version: API version for version-specific formatting
        response_format: Response format type
        resource_id: ID of the deleted resource
        resource_type: Type of the deleted resource
        
    Returns:
        Dict: Formatted deletion response
    """
    meta = {"status_code": 204}
    
    # Add resource metadata for enhanced formats
    if response_format in [ResponseFormat.V2_ENHANCED, ResponseFormat.DETAILED]:
        if resource_id:
            meta["resource_id"] = resource_id
        if resource_type:
            meta["resource_type"] = resource_type
        meta["operation"] = "delete"
    
    return success_response(
        data=None,
        message=message,
        meta=meta,
        api_version=api_version,
        response_format=response_format
    )

# Specialized response helpers

def validation_error_response(
    errors: List[Dict[str, Any]],
    message: str = "Validation failed",
    api_version: Optional[str] = None,
    response_format: ResponseFormat = ResponseFormat.STANDARD
) -> Dict[str, Any]:
    """
    Create a standardized validation error response.
    
    Args:
        errors: List of validation errors
        message: Error message
        api_version: API version for version-specific formatting
        response_format: Response format type
        
    Returns:
        Dict: Formatted validation error response
    """
    error_details = {"validation_errors": errors}
    
    if response_format == ResponseFormat.V2_ENHANCED:
        error_details["error_count"] = len(errors)
        error_details["fields_with_errors"] = list(set(error.get("field", "unknown") for error in errors))
    
    return error_response(
        message=message,
        error_code="VALIDATION_ERROR",
        details=error_details,
        status_code=422,
        api_version=api_version,
        response_format=response_format
    )


def not_found_response(
    resource_type: str = "Resource",
    resource_id: Optional[str] = None,
    api_version: Optional[str] = None,
    response_format: ResponseFormat = ResponseFormat.STANDARD
) -> Dict[str, Any]:
    """
    Create a standardized not found error response.
    
    Args:
        resource_type: Type of resource that was not found
        resource_id: ID of the resource that was not found
        api_version: API version for version-specific formatting
        response_format: Response format type
        
    Returns:
        Dict: Formatted not found error response
    """
    if resource_id:
        message = f"{resource_type} with ID '{resource_id}' not found"
        details = {"resource_type": resource_type, "resource_id": resource_id}
    else:
        message = f"{resource_type} not found"
        details = {"resource_type": resource_type}
    
    return error_response(
        message=message,
        error_code="RESOURCE_NOT_FOUND",
        details=details,
        status_code=404,
        api_version=api_version,
        response_format=response_format
    )


def unauthorized_response(
    message: str = "Authentication required",
    api_version: Optional[str] = None,
    response_format: ResponseFormat = ResponseFormat.STANDARD
) -> Dict[str, Any]:
    """
    Create a standardized unauthorized error response.
    
    Args:
        message: Error message
        api_version: API version for version-specific formatting
        response_format: Response format type
        
    Returns:
        Dict: Formatted unauthorized error response
    """
    return error_response(
        message=message,
        error_code="UNAUTHORIZED",
        status_code=401,
        api_version=api_version,
        response_format=response_format
    )


def forbidden_response(
    message: str = "Access denied",
    required_permission: Optional[str] = None,
    api_version: Optional[str] = None,
    response_format: ResponseFormat = ResponseFormat.STANDARD
) -> Dict[str, Any]:
    """
    Create a standardized forbidden error response.
    
    Args:
        message: Error message
        required_permission: Permission that was required
        api_version: API version for version-specific formatting
        response_format: Response format type
        
    Returns:
        Dict: Formatted forbidden error response
    """
    details = {}
    if required_permission:
        details["required_permission"] = required_permission
    
    return error_response(
        message=message,
        error_code="FORBIDDEN",
        details=details if details else None,
        status_code=403,
        api_version=api_version,
        response_format=response_format
    )


def conflict_response(
    message: str = "Resource conflict",
    conflict_type: Optional[str] = None,
    api_version: Optional[str] = None,
    response_format: ResponseFormat = ResponseFormat.STANDARD
) -> Dict[str, Any]:
    """
    Create a standardized conflict error response.
    
    Args:
        message: Error message
        conflict_type: Type of conflict that occurred
        api_version: API version for version-specific formatting
        response_format: Response format type
        
    Returns:
        Dict: Formatted conflict error response
    """
    details = {}
    if conflict_type:
        details["conflict_type"] = conflict_type
    
    return error_response(
        message=message,
        error_code="RESOURCE_CONFLICT",
        details=details if details else None,
        status_code=409,
        api_version=api_version,
        response_format=response_format
    )


def rate_limit_response(
    message: str = "Rate limit exceeded",
    retry_after: Optional[int] = None,
    api_version: Optional[str] = None,
    response_format: ResponseFormat = ResponseFormat.STANDARD
) -> Dict[str, Any]:
    """
    Create a standardized rate limit error response.
    
    Args:
        message: Error message
        retry_after: Seconds to wait before retrying
        api_version: API version for version-specific formatting
        response_format: Response format type
        
    Returns:
        Dict: Formatted rate limit error response
    """
    details = {}
    if retry_after:
        details["retry_after"] = retry_after
    
    return error_response(
        message=message,
        error_code="RATE_LIMIT_EXCEEDED",
        details=details if details else None,
        status_code=429,
        api_version=api_version,
        response_format=response_format
    )


# Version-specific response formatters

def get_response_format_for_version(api_version: Optional[str]) -> ResponseFormat:
    """
    Get the appropriate response format for an API version.
    
    Args:
        api_version: API version string
        
    Returns:
        ResponseFormat: Appropriate response format
    """
    if api_version == "v1":
        return ResponseFormat.V1_LEGACY
    elif api_version == "v2":
        return ResponseFormat.V2_ENHANCED
    else:
        return ResponseFormat.STANDARD


def format_response_for_version(
    response_data: Dict[str, Any],
    api_version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format an existing response for a specific API version.
    
    Args:
        response_data: Response data to format
        api_version: Target API version
        
    Returns:
        Dict: Formatted response
    """
    response_format = get_response_format_for_version(api_version)
    
    # If it's already a success response, reformat it
    if response_data.get("success") is True:
        return success_response(
            data=response_data.get("data"),
            message=response_data.get("message"),
            meta=response_data.get("meta", {}),
            api_version=api_version,
            response_format=response_format
        )
    
    # If it's an error response, reformat it
    elif response_data.get("success") is False:
        error_info = response_data.get("error", {})
        return error_response(
            message=error_info.get("message", "An error occurred"),
            error_code=error_info.get("code", "UNKNOWN_ERROR"),
            details=error_info.get("details"),
            status_code=response_data.get("meta", {}).get("status_code", 500),
            api_version=api_version,
            response_format=response_format
        )
    
    # If it's raw data, wrap it in a success response
    else:
        return success_response(
            data=response_data,
            api_version=api_version,
            response_format=response_format
        )


# Utility functions for response transformation

def transform_data_for_version(
    data: Any,
    api_version: Optional[str] = None,
    transformation_rules: Optional[Dict[str, Callable]] = None
) -> Any:
    """
    Transform response data based on API version-specific rules.
    
    Args:
        data: Data to transform
        api_version: API version
        transformation_rules: Version-specific transformation rules
        
    Returns:
        Any: Transformed data
    """
    if not transformation_rules or not api_version:
        return data
    
    transformer = transformation_rules.get(api_version)
    if transformer and callable(transformer):
        return transformer(data)
    
    return data


def add_version_specific_metadata(
    meta: Dict[str, Any],
    api_version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add version-specific metadata to response metadata.
    
    Args:
        meta: Base metadata
        api_version: API version
        
    Returns:
        Dict: Enhanced metadata
    """
    enhanced_meta = meta.copy()
    
    if api_version == "v1":
        # V1 specific metadata
        enhanced_meta["legacy_format"] = True
        enhanced_meta["deprecation_notice"] = "API v1 is deprecated. Please migrate to v2."
    
    elif api_version == "v2":
        # V2 specific metadata
        enhanced_meta["enhanced_format"] = True
        enhanced_meta["features"] = ["pagination", "filtering", "sorting", "field_selection"]
    
    return enhanced_meta