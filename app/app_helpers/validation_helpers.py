"""
Common validation helper functions.
"""
import re
import uuid
from typing import Optional
from fastapi import HTTPException, status


def validate_uuid(uuid_string: str, field_name: str = "id") -> uuid.UUID:
    """
    Validate and convert string to UUID.
    
    Args:
        uuid_string: String to validate as UUID
        field_name: Name of the field for error messages
        
    Returns:
        uuid.UUID: Validated UUID object
        
    Raises:
        HTTPException: If UUID is invalid
    """
    try:
        return uuid.UUID(uuid_string)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}: must be a valid UUID"
        )


def validate_email(email: str) -> str:
    """
    Validate email format.
    
    Args:
        email: Email string to validate
        
    Returns:
        str: Validated email
        
    Raises:
        HTTPException: If email format is invalid
    """
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    
    return email.lower()


def validate_phone(phone: str) -> str:
    """
    Validate and format phone number.
    
    Args:
        phone: Phone number string to validate
        
    Returns:
        str: Validated and formatted phone number
        
    Raises:
        HTTPException: If phone format is invalid
    """
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's a valid US phone number (10 digits)
    if len(digits_only) == 10:
        return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
    elif len(digits_only) == 11 and digits_only[0] == '1':
        # Handle +1 country code
        return f"+1 ({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:]}"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format. Must be 10 digits (US) or 11 digits with country code"
        )


def validate_pagination_params(page: int, size: int) -> tuple[int, int]:
    """
    Validate pagination parameters.
    
    Args:
        page: Page number (1-based)
        size: Items per page
        
    Returns:
        tuple: Validated (page, size) parameters
        
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


def validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Validate date range parameters.
    
    Args:
        start_date: Start date string (ISO format)
        end_date: End date string (ISO format)
        
    Returns:
        tuple: Validated date range
        
    Raises:
        HTTPException: If date format is invalid or range is invalid
    """
    from datetime import datetime
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"
            )
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"
            )
    
    if start_date and end_date:
        if start_dt >= end_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be before end_date"
            )
    
    return start_date, end_date


def validate_sort_params(sort_by: Optional[str], allowed_fields: list[str]) -> Optional[str]:
    """
    Validate sort parameters.
    
    Args:
        sort_by: Field to sort by (with optional - prefix for descending)
        allowed_fields: List of allowed sort fields
        
    Returns:
        Optional[str]: Validated sort parameter
        
    Raises:
        HTTPException: If sort field is not allowed
    """
    if not sort_by:
        return None
    
    # Handle descending sort (prefix with -)
    field = sort_by.lstrip('-')
    
    if field not in allowed_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort field. Allowed fields: {', '.join(allowed_fields)}"
        )
    
    return sort_by