"""
Pagination helper functions.
"""
from typing import Tuple, Dict, Any
from fastapi import HTTPException, status


def get_pagination_params(page: int = 1, size: int = 20) -> Tuple[int, int]:
    """
    Get and validate pagination parameters.
    
    Args:
        page: Page number (1-based)
        size: Items per page
        
    Returns:
        Tuple[int, int]: Validated (page, size) parameters
        
    Raises:
        HTTPException: If parameters are invalid
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be greater than 0"
        )
    
    if size < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be greater than 0"
        )
    
    if size > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size cannot exceed 100 items"
        )
    
    return page, size


def create_pagination_meta(
    page: int,
    size: int,
    total: int
) -> Dict[str, Any]:
    """
    Create pagination metadata.
    
    Args:
        page: Current page number
        size: Items per page
        total: Total number of items
        
    Returns:
        Dict[str, Any]: Pagination metadata
    """
    total_pages = (total + size - 1) // size  # Ceiling division
    
    return {
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    }