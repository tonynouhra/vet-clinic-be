"""
Version-agnostic User resource package.
Contains controller and service for user management across all API versions.
"""

from .controller import UserController
from .services import UserService

__all__ = [
    "UserController",
    "UserService",
]