"""
Schema validation utilities for API versioning.

Contains custom validators and validation patterns that can be used
across different API versions to ensure data consistency and integrity.
"""

import re
from typing import Any, Dict, List, Optional
from pydantic import validator, Field
from datetime import datetime


def validate_email(email: str) -> str:
    """Validate email format."""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        raise ValueError('Invalid email format')
    return email.lower()


def validate_phone(phone: str) -> str:
    """Validate phone number format."""
    # Remove all non-digit characters
    cleaned_phone = re.sub(r'\D', '', phone)
    
    # Check if it's a valid length (10-15 digits)
    if len(cleaned_phone) < 10 or len(cleaned_phone) > 15:
        raise ValueError('Phone number must be between 10-15 digits')
    
    return cleaned_phone


def validate_password_strength(password: str) -> str:
    """Validate password strength."""
    if len(password) < 8:
        raise ValueError('Password must be at least 8 characters long')
    
    if not re.search(r'[A-Z]', password):
        raise ValueError('Password must contain at least one uppercase letter')
    
    if not re.search(r'[a-z]', password):
        raise ValueError('Password must contain at least one lowercase letter')
    
    if not re.search(r'\d', password):
        raise ValueError('Password must contain at least one number')
    
    return password


def validate_positive_integer(value: int) -> int:
    """Validate that a value is a positive integer."""
    if value <= 0:
        raise ValueError('Value must be a positive integer')
    return value


def validate_non_empty_string(value: str) -> str:
    """Validate that a string is not empty or just whitespace."""
    if not value or not value.strip():
        raise ValueError('String cannot be empty or contain only whitespace')
    return value.strip()


def validate_date_not_in_past(value: datetime) -> datetime:
    """Validate that a datetime is not in the past."""
    if value < datetime.now():
        raise ValueError('Date cannot be in the past')
    return value


def validate_date_not_in_future(value: datetime) -> datetime:
    """Validate that a datetime is not in the future."""
    if value > datetime.now():
        raise ValueError('Date cannot be in the future')
    return value


class SchemaValidationMixin:
    """Mixin class providing common validation methods for schemas."""
    
    @validator('*', pre=True)
    def strip_strings(cls, v):
        """Strip whitespace from string fields."""
        if isinstance(v, str):
            return v.strip()
        return v
    
    @classmethod
    def validate_required_fields(cls, values: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """Validate that required fields are present and not empty."""
        for field in required_fields:
            if field not in values or values[field] is None:
                raise ValueError(f'{field} is required')
            if isinstance(values[field], str) and not values[field].strip():
                raise ValueError(f'{field} cannot be empty')
        return values
    
    @classmethod
    def validate_conditional_fields(cls, values: Dict[str, Any], conditions: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Validate conditional fields based on other field values.
        
        Args:
            values: Field values dictionary
            conditions: Dict mapping condition fields to required fields when condition is true
        """
        for condition_field, required_fields in conditions.items():
            if values.get(condition_field):
                for field in required_fields:
                    if field not in values or values[field] is None:
                        raise ValueError(f'{field} is required when {condition_field} is provided')
        return values


# Common field patterns that can be reused across versions
def email_field(description: str = "Email address", **kwargs):
    """Create a validated email field."""
    return Field(description=description, **kwargs)


def phone_field(description: str = "Phone number", **kwargs):
    """Create a validated phone field."""
    return Field(description=description, **kwargs)


def password_field(description: str = "Password", **kwargs):
    """Create a validated password field."""
    return Field(description=description, min_length=8, **kwargs)


def positive_int_field(description: str = "Positive integer", **kwargs):
    """Create a positive integer field."""
    return Field(description=description, gt=0, **kwargs)


def non_empty_string_field(description: str = "Non-empty string", **kwargs):
    """Create a non-empty string field."""
    return Field(description=description, min_length=1, **kwargs)