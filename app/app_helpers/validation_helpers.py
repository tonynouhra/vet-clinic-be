"""
Enhanced validation helper functions with business rule validation and cross-field validation.

This module provides comprehensive validation utilities that work across all API versions,
including field validation, business rule validation, and cross-field validation helpers.
"""
import re
import uuid
from typing import Optional, List, Dict, Any, Union, Callable, Type, Tuple
from datetime import datetime, date, time
from decimal import Decimal, InvalidOperation
from enum import Enum
from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError as PydanticValidationError


class ValidationError(Exception):
    """Custom validation error for business rules."""
    
    def __init__(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)


class BusinessRuleValidator:
    """Base class for business rule validators."""
    
    def __init__(self, error_message: str, error_code: Optional[str] = None):
        self.error_message = error_message
        self.error_code = error_code
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        """Override this method in subclasses."""
        raise NotImplementedError
    
    def __call__(self, value: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        if not self.validate(value, context):
            raise ValidationError(self.error_message, code=self.error_code)
        return value


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
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}: must be a valid UUID"
        ) from exc


def validate_email(email: str) -> str:
    """
    Enhanced email validation with comprehensive format checking.
    
    Args:
        email: Email string to validate
        
    Returns:
        str: Validated and normalized email
        
    Raises:
        HTTPException: If email format is invalid
    """
    if not email or not isinstance(email, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required and must be a string"
        )
    
    # Comprehensive email pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # Additional checks
    if len(email) > 254:  # RFC 5321 limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is too long (maximum 254 characters)"
        )
    
    if not re.match(email_pattern, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    
    # Check for consecutive dots
    if '..' in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email cannot contain consecutive dots"
        )
    
    return email.lower().strip()


def validate_phone(phone: str) -> str:
    """
    Enhanced phone number validation and formatting.
    
    Args:
        phone: Phone number string to validate
        
    Returns:
        str: Validated and formatted phone number
        
    Raises:
        HTTPException: If phone format is invalid
    """
    if not phone or not isinstance(phone, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is required and must be a string"
        )
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's a valid US phone number (10 digits)
    if len(digits_only) == 10:
        return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
    if len(digits_only) == 11 and digits_only[0] == '1':
        # Handle +1 country code
        return f"+1 ({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:]}"
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid phone number format. Must be 10 digits (US) or 11 digits with country code"
    )


def validate_pagination_params(page: int, size: int, max_size: int = 100) -> Tuple[int, int]:
    """
    Enhanced pagination parameter validation.
    
    Args:
        page: Page number (1-based)
        size: Items per page
        max_size: Maximum allowed page size
        
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
    
    if size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Page size cannot exceed {max_size} items"
        )
    
    return page, size


def validate_date_range(
    start_date: Optional[str], 
    end_date: Optional[str],
    allow_same_date: bool = True
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Enhanced date range validation.
    
    Args:
        start_date: Start date string (ISO format)
        end_date: End date string (ISO format)
        allow_same_date: Whether to allow start_date == end_date
        
    Returns:
        tuple: Validated datetime objects
        
    Raises:
        HTTPException: If date format is invalid or range is invalid
    """
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"
            ) from exc
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"
            ) from exc
    
    if start_dt and end_dt:
        if not allow_same_date and start_dt >= end_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be before end_date"
            )
        elif allow_same_date and start_dt > end_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be after end_date"
            )
    
    return start_dt, end_dt


def validate_sort_params(sort_by: Optional[str], allowed_fields: List[str]) -> Optional[str]:
    """
    Enhanced sort parameter validation.
    
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


def validate_decimal(
    value: Union[str, int, float, Decimal], 
    field_name: str = "value",
    min_value: Optional[Decimal] = None,
    max_value: Optional[Decimal] = None,
    max_decimal_places: Optional[int] = None
) -> Decimal:
    """
    Validate and convert value to Decimal with constraints.
    
    Args:
        value: Value to convert to Decimal
        field_name: Field name for error messages
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        max_decimal_places: Maximum decimal places allowed
        
    Returns:
        Decimal: Validated decimal value
        
    Raises:
        HTTPException: If value is invalid
    """
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}: must be a valid number"
        ) from exc
    
    if min_value is not None and decimal_value < min_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be at least {min_value}"
        )
    
    if max_value is not None and decimal_value > max_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} cannot exceed {max_value}"
        )
    
    if max_decimal_places is not None:
        # Check decimal places
        sign, digits, exponent = decimal_value.as_tuple()
        if exponent < -max_decimal_places:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot have more than {max_decimal_places} decimal places"
            )
    
    return decimal_value


def validate_string_length(
    value: str,
    field_name: str = "field",
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    allow_empty: bool = True
) -> str:
    """
    Validate string length constraints.
    
    Args:
        value: String value to validate
        field_name: Field name for error messages
        min_length: Minimum length required
        max_length: Maximum length allowed
        allow_empty: Whether to allow empty strings
        
    Returns:
        str: Validated string
        
    Raises:
        HTTPException: If string length is invalid
    """
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a string"
        )
    
    if not allow_empty and len(value.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} cannot be empty"
        )
    
    if min_length is not None and len(value) < min_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be at least {min_length} characters long"
        )
    
    if max_length is not None and len(value) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} cannot exceed {max_length} characters"
        )
    
    return value


def validate_enum_value(value: Any, enum_class: Type[Enum], field_name: str = "field") -> Enum:
    """
    Validate that a value is a valid enum member.
    
    Args:
        value: Value to validate
        enum_class: Enum class to validate against
        field_name: Field name for error messages
        
    Returns:
        Enum: Validated enum value
        
    Raises:
        HTTPException: If value is not a valid enum member
    """
    try:
        if isinstance(value, str):
            return enum_class(value)
        elif isinstance(value, enum_class):
            return value
        else:
            # Try to convert to string first
            return enum_class(str(value))
    except ValueError as exc:
        valid_values = [member.value for member in enum_class]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}. Valid values: {', '.join(valid_values)}"
        ) from exc


# Business Rule Validators

class UniqueEmailValidator(BusinessRuleValidator):
    """Validator to check email uniqueness."""
    
    def __init__(self, db_session, exclude_user_id: Optional[str] = None):
        super().__init__("Email address is already registered", "EMAIL_ALREADY_EXISTS")
        self.db_session = db_session
        self.exclude_user_id = exclude_user_id
    
    async def validate(self, email: str, context: Optional[Dict[str, Any]] = None) -> bool:
        from app.models import User
        from sqlalchemy import select
        
        query = select(User).where(User.email == email.lower())
        if self.exclude_user_id:
            query = query.where(User.id != self.exclude_user_id)
        
        result = await self.db_session.execute(query)
        existing_user = result.scalar_one_or_none()
        return existing_user is None


class AppointmentTimeValidator(BusinessRuleValidator):
    """Validator for appointment scheduling business rules."""
    
    def __init__(self):
        super().__init__("Invalid appointment time", "INVALID_APPOINTMENT_TIME")
    
    def validate(self, appointment_time: datetime, context: Optional[Dict[str, Any]] = None) -> bool:
        # Business rule: Appointments must be in the future
        if appointment_time <= datetime.utcnow():
            self.error_message = "Appointment time must be in the future"
            return False
        
        # Business rule: Appointments must be during business hours (9 AM - 5 PM)
        if appointment_time.hour < 9 or appointment_time.hour >= 17:
            self.error_message = "Appointments must be scheduled between 9 AM and 5 PM"
            return False
        
        # Business rule: No appointments on weekends
        if appointment_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            self.error_message = "Appointments cannot be scheduled on weekends"
            return False
        
        return True


class PetAgeValidator(BusinessRuleValidator):
    """Validator for pet age business rules."""
    
    def __init__(self):
        super().__init__("Invalid pet age", "INVALID_PET_AGE")
    
    def validate(self, birth_date: date, context: Optional[Dict[str, Any]] = None) -> bool:
        today = date.today()
        
        # Pet cannot be born in the future
        if birth_date > today:
            self.error_message = "Pet birth date cannot be in the future"
            return False
        
        # Pet cannot be older than 50 years (reasonable maximum)
        max_age_years = 50
        if (today - birth_date).days > (max_age_years * 365):
            self.error_message = f"Pet cannot be older than {max_age_years} years"
            return False
        
        return True


# Cross-field validation helpers

def validate_password_confirmation(password: str, password_confirmation: str) -> bool:
    """
    Validate that password and confirmation match.
    
    Args:
        password: Original password
        password_confirmation: Password confirmation
        
    Returns:
        bool: True if passwords match
        
    Raises:
        HTTPException: If passwords don't match
    """
    if password != password_confirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password and password confirmation do not match"
        )
    return True


def validate_date_order(
    start_date: datetime, 
    end_date: datetime, 
    start_field: str = "start_date",
    end_field: str = "end_date"
) -> bool:
    """
    Validate that start date is before end date.
    
    Args:
        start_date: Start datetime
        end_date: End datetime
        start_field: Name of start field for error messages
        end_field: Name of end field for error messages
        
    Returns:
        bool: True if order is valid
        
    Raises:
        HTTPException: If date order is invalid
    """
    if start_date >= end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{start_field} must be before {end_field}"
        )
    return True


def validate_conditional_required(
    value: Any,
    condition_field: str,
    condition_value: Any,
    field_name: str,
    context: Dict[str, Any]
) -> bool:
    """
    Validate that a field is required when a condition is met.
    
    Args:
        value: Value to validate
        condition_field: Field name that determines if this field is required
        condition_value: Value that makes this field required
        field_name: Name of the field being validated
        context: Dictionary containing all field values
        
    Returns:
        bool: True if validation passes
        
    Raises:
        HTTPException: If required field is missing
    """
    if context.get(condition_field) == condition_value and not value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is required when {condition_field} is {condition_value}"
        )
    return True


# Utility functions for version-aware validation

def validate_schema_version_compatibility(
    data: Dict[str, Any], 
    schema_class: Type[BaseModel],
    api_version: str
) -> BaseModel:
    """
    Validate data against a schema with version-aware error handling.
    
    Args:
        data: Data to validate
        schema_class: Pydantic schema class
        api_version: API version for context
        
    Returns:
        BaseModel: Validated schema instance
        
    Raises:
        HTTPException: If validation fails
    """
    try:
        return schema_class(**data)
    except PydanticValidationError as exc:
        # Format validation errors for the specific API version
        error_details = []
        for error in exc.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            error_details.append({
                "field": field_path,
                "message": error["msg"],
                "type": error["type"]
            })
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Validation failed for API version {api_version}",
                "errors": error_details
            }
        ) from exc


def create_version_aware_validator(
    v1_validator: Callable,
    v2_validator: Callable,
    default_validator: Optional[Callable] = None
) -> Callable:
    """
    Create a validator that behaves differently based on API version.
    
    Args:
        v1_validator: Validator function for API v1
        v2_validator: Validator function for API v2
        default_validator: Default validator for unknown versions
        
    Returns:
        Callable: Version-aware validator function
    """
    def version_aware_validator(value: Any, api_version: Optional[str] = None) -> Any:
        if api_version == "v1":
            return v1_validator(value)
        elif api_version == "v2":
            return v2_validator(value)
        elif default_validator:
            return default_validator(value)
        else:
            # Use v2 as default for forward compatibility
            return v2_validator(value)
    
    return version_aware_validator