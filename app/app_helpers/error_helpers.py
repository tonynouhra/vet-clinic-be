"""
Error handling helper functions.
"""
from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError


def handle_database_error(error: Exception) -> HTTPException:
    """
    Handle database-related errors and convert to appropriate HTTP exceptions.
    
    Args:
        error: Database error exception
        
    Returns:
        HTTPException: Appropriate HTTP exception
    """
    if isinstance(error, IntegrityError):
        # Handle constraint violations
        if "unique constraint" in str(error).lower():
            return HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Resource already exists with these values"
            )
        elif "foreign key constraint" in str(error).lower():
            return HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Referenced resource does not exist"
            )
        else:
            return HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Database constraint violation"
            )
    
    elif isinstance(error, SQLAlchemyError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed"
        )
    
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


def handle_validation_error(error: ValidationError) -> HTTPException:
    """
    Handle Pydantic validation errors and convert to HTTP exceptions.
    
    Args:
        error: Pydantic validation error
        
    Returns:
        HTTPException: HTTP exception with validation details
    """
    error_details = []
    
    for err in error.errors():
        field_path = " -> ".join(str(loc) for loc in err["loc"])
        error_details.append({
            "field": field_path,
            "message": err["msg"],
            "type": err["type"]
        })
    
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "message": "Validation failed",
            "errors": error_details
        }
    )