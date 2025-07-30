"""
Custom validation functions.
"""
import re
from typing import Optional
from datetime import datetime, date


def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if valid email format
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        bool: True if valid phone format
    """
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    # Check if it's between 10-15 digits (international format)
    return 10 <= len(digits_only) <= 15


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, None


def validate_date_range(start_date: date, end_date: date) -> bool:
    """
    Validate that end date is after start date.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        bool: True if valid date range
    """
    return end_date >= start_date


def validate_age(birth_date: date) -> bool:
    """
    Validate that birth date is not in the future.
    
    Args:
        birth_date: Birth date to validate
        
    Returns:
        bool: True if valid birth date
    """
    return birth_date <= date.today()


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize string input by removing dangerous characters.
    
    Args:
        text: Text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        str: Sanitized text
    """
    # Remove HTML tags and dangerous characters
    sanitized = re.sub(r'<[^>]*>', '', text)
    sanitized = re.sub(r'[<>"\']', '', sanitized)
    
    if max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()