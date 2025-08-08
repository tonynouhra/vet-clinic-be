"""
Authentication package for the Veterinary Clinic Backend.
Provides version-agnostic authentication controllers and services.
"""

from .controller import AuthController
from .services import AuthService

__all__ = ["AuthController", "AuthService"]