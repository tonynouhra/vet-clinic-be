"""
Common validation helpers for use across all API versions.
Provides reusable validation functions for common data types and business rules.
"""

import re
import uuid
from typing import Tuple, Optional, Any, List, Dict
from datetime import datetime, date
from email_validator import validate_email as email_validate, EmailNotValidError

from app.core.exceptions import ValidationError


def validate_pagination_params(page: int, size: int, max_size: int = 100) -> Tuple[int, int]:
    """
    Validate and normalize pagination parameters.
    
    Args:
        page: Page number (1-based)
        size: Page size
        max_size: Maximum allowed page size
        
    Returns:
        Tuple[int, int]: Validated (page, size) tuple
        
    Raises:
        ValidationError: If parameters are invalid
    """
    if page < 1:
        raise ValidationError(
            message="Page number must be greater than 0",
            field="page",
            value=page
        )
    
    if size < 1:
        raise ValidationError(
            message="Page size must be greater than 0",
            field="size",
            value=size
        )
    
    if size > max_size:
        raise ValidationError(
            message=f"Page size cannot exceed {max_size}",
            field="size",
            value=size,
            details={"max_size": max_size}
        )
    
    return page, size


def validate_uuid(value: str, field_name: str = "id") -> str:
    """
    Validate UUID string format.
    
    Args:
        value: UUID string to validate
        field_name: Name of the field being validated
        
    Returns:
        str: Validated UUID string
        
    Raises:
        ValidationError: If UUID format is invalid
    """
    if not value:
        raise ValidationError(
            message=f"{field_name} is required",
            field=field_name,
            value=value
        )
    
    try:
        uuid.UUID(value)
        return value
    except ValueError:
        raise ValidationError(
            message=f"Invalid {field_name} format",
            field=field_name,
            value=value,
            details={"expected_format": "UUID"}
        )


def validate_email(email: str, field_name: str = "email") -> str:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        field_name: Name of the field being validated
        
    Returns:
        str: Validated and normalized email address
        
    Raises:
        ValidationError: If email format is invalid
    """
    if not email:
        raise ValidationError(
            message=f"{field_name} is required",
            field=field_name,
            value=email
        )
    
    try:
        # Use email-validator library for comprehensive validation
        valid_email = email_validate(email)
        return valid_email.email.lower()  # Normalize to lowercase
    except EmailNotValidError as e:
        raise ValidationError(
            message=f"Invalid {field_name} format",
            field=field_name,
            value=email,
            details={"validation_error": str(e)}
        )


def validate_phone_number(phone: str, field_name: str = "phone_number") -> str:
    """
    Validate phone number format (basic validation).
    
    Args:
        phone: Phone number to validate
        field_name: Name of the field being validated
        
    Returns:
        str: Validated phone number
        
    Raises:
        ValidationError: If phone number format is invalid
    """
    if not phone:
        return phone  # Allow empty phone numbers
    
    # Remove common formatting characters
    cleaned_phone = re.sub(r'[\s\-\(\)\+]', '', phone)
    
    # Basic validation: 10-15 digits
    if not re.match(r'^\d{10,15}$', cleaned_phone):
        raise ValidationError(
            message=f"Invalid {field_name} format",
            field=field_name,
            value=phone,
            details={"expected_format": "10-15 digits"}
        )
    
    return phone  # Return original format


def validate_date_range(
    start_date: Optional[date],
    end_date: Optional[date],
    field_prefix: str = "date"
) -> Tuple[Optional[date], Optional[date]]:
    """
    Validate date range (start_date <= end_date).
    
    Args:
        start_date: Start date
        end_date: End date
        field_prefix: Prefix for field names in error messages
        
    Returns:
        Tuple[Optional[date], Optional[date]]: Validated date range
        
    Raises:
        ValidationError: If date range is invalid
    """
    if start_date and end_date and start_date > end_date:
        raise ValidationError(
            message=f"{field_prefix}_start cannot be after {field_prefix}_end",
            field=f"{field_prefix}_range",
            details={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )
    
    return start_date, end_date


def validate_datetime_range(
    start_datetime: Optional[datetime],
    end_datetime: Optional[datetime],
    field_prefix: str = "datetime"
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Validate datetime range (start_datetime <= end_datetime).
    
    Args:
        start_datetime: Start datetime
        end_datetime: End datetime
        field_prefix: Prefix for field names in error messages
        
    Returns:
        Tuple[Optional[datetime], Optional[datetime]]: Validated datetime range
        
    Raises:
        ValidationError: If datetime range is invalid
    """
    if start_datetime and end_datetime and start_datetime > end_datetime:
        raise ValidationError(
            message=f"{field_prefix}_start cannot be after {field_prefix}_end",
            field=f"{field_prefix}_range",
            details={
                "start_datetime": start_datetime.isoformat(),
                "end_datetime": end_datetime.isoformat()
            }
        )
    
    return start_datetime, end_datetime


def validate_string_length(
    value: str,
    field_name: str,
    min_length: int = 0,
    max_length: Optional[int] = None,
    required: bool = True
) -> str:
    """
    Validate string length constraints.
    
    Args:
        value: String value to validate
        field_name: Name of the field being validated
        min_length: Minimum required length
        max_length: Maximum allowed length
        required: Whether the field is required
        
    Returns:
        str: Validated string value
        
    Raises:
        ValidationError: If string length constraints are violated
    """
    if not value:
        if required:
            raise ValidationError(
                message=f"{field_name} is required",
                field=field_name,
                value=value
            )
        return value
    
    if len(value) < min_length:
        raise ValidationError(
            message=f"{field_name} must be at least {min_length} characters long",
            field=field_name,
            value=value,
            details={"min_length": min_length, "actual_length": len(value)}
        )
    
    if max_length and len(value) > max_length:
        raise ValidationError(
            message=f"{field_name} cannot exceed {max_length} characters",
            field=field_name,
            value=value,
            details={"max_length": max_length, "actual_length": len(value)}
        )
    
    return value


def validate_enum_value(
    value: Any,
    enum_class: type,
    field_name: str,
    required: bool = True
) -> Any:
    """
    Validate enum value.
    
    Args:
        value: Value to validate
        enum_class: Enum class to validate against
        field_name: Name of the field being validated
        required: Whether the field is required
        
    Returns:
        Any: Validated enum value
        
    Raises:
        ValidationError: If enum value is invalid
    """
    if not value:
        if required:
            raise ValidationError(
                message=f"{field_name} is required",
                field=field_name,
                value=value
            )
        return value
    
    try:
        if hasattr(enum_class, '__members__'):
            # Python Enum
            if value not in enum_class.__members__.values():
                valid_values = list(enum_class.__members__.keys())
                raise ValidationError(
                    message=f"Invalid {field_name} value",
                    field=field_name,
                    value=value,
                    details={"valid_values": valid_values}
                )
        else:
            # Custom validation
            if value not in enum_class:
                raise ValidationError(
                    message=f"Invalid {field_name} value",
                    field=field_name,
                    value=value,
                    details={"valid_values": list(enum_class)}
                )
        
        return value
    except (AttributeError, TypeError):
        raise ValidationError(
            message=f"Invalid {field_name} value",
            field=field_name,
            value=value
        )


def validate_positive_number(
    value: float,
    field_name: str,
    allow_zero: bool = False
) -> float:
    """
    Validate positive number.
    
    Args:
        value: Number to validate
        field_name: Name of the field being validated
        allow_zero: Whether zero is allowed
        
    Returns:
        float: Validated number
        
    Raises:
        ValidationError: If number is not positive
    """
    if value is None:
        raise ValidationError(
            message=f"{field_name} is required",
            field=field_name,
            value=value
        )
    
    if allow_zero and value < 0:
        raise ValidationError(
            message=f"{field_name} must be zero or positive",
            field=field_name,
            value=value
        )
    elif not allow_zero and value <= 0:
        raise ValidationError(
            message=f"{field_name} must be positive",
            field=field_name,
            value=value
        )
    
    return value


def validate_list_items(
    items: List[Any],
    field_name: str,
    min_items: int = 0,
    max_items: Optional[int] = None,
    unique: bool = False
) -> List[Any]:
    """
    Validate list constraints.
    
    Args:
        items: List to validate
        field_name: Name of the field being validated
        min_items: Minimum number of items required
        max_items: Maximum number of items allowed
        unique: Whether items must be unique
        
    Returns:
        List[Any]: Validated list
        
    Raises:
        ValidationError: If list constraints are violated
    """
    if not items:
        items = []
    
    if len(items) < min_items:
        raise ValidationError(
            message=f"{field_name} must contain at least {min_items} items",
            field=field_name,
            value=items,
            details={"min_items": min_items, "actual_items": len(items)}
        )
    
    if max_items and len(items) > max_items:
        raise ValidationError(
            message=f"{field_name} cannot contain more than {max_items} items",
            field=field_name,
            value=items,
            details={"max_items": max_items, "actual_items": len(items)}
        )
    
    if unique and len(items) != len(set(items)):
        raise ValidationError(
            message=f"{field_name} items must be unique",
            field=field_name,
            value=items
        )
    
    return items