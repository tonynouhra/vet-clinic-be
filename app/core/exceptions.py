"""
Custom exception classes for the application.
"""
from typing import Any, Dict, Optional


class VetClinicException(Exception):
    """Base exception class for the application."""
    
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(VetClinicException):
    """Raised when validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details)


class AuthenticationError(VetClinicException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTHENTICATION_ERROR")


class AuthorizationError(VetClinicException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, "AUTHORIZATION_ERROR")


class NotFoundError(VetClinicException):
    """Raised when a resource is not found."""
    
    def __init__(self, message: str, resource: str = "Resource"):
        super().__init__(message, "NOT_FOUND", {"resource": resource})


class ConflictError(VetClinicException):
    """Raised when there's a conflict with existing data."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFLICT_ERROR", details)


class DatabaseError(VetClinicException):
    """Raised when database operations fail."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATABASE_ERROR", details)