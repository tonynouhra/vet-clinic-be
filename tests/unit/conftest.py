"""
Unit test fixtures for authentication tests.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.controller import AuthController
from app.models.user import User, UserRole


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_auth_service():
    """Mock authentication service."""
    return AsyncMock()


@pytest.fixture
def auth_controller(mock_db_session):
    """Create auth controller instance."""
    return AuthController(mock_db_session)


@pytest.fixture
def sample_user():
    """Sample user object."""
    user = Mock(spec=User)
    user.id = "user_123"
    user.email = "test@gmail.com"
    user.first_name = "John"
    user.last_name = "Doe"
    user.phone_number = "+1234567890"
    user.role = UserRole.PET_OWNER
    user.clerk_id = "temp_12345"
    user.is_active = True
    user.is_verified = False
    user.last_login = None
    user.created_at = datetime.utcnow()
    return user


@pytest.fixture
def valid_registration_data():
    """Valid registration data."""
    return {
        "email": "test@gmail.com",
        "password": "securepassword123",
        "confirm_password": "securepassword123",
        "first_name": "John",
        "last_name": "Doe",
        "phone_number": "+1234567890",
        "role": UserRole.PET_OWNER
    }


@pytest.fixture
def valid_login_data():
    """Valid login data."""
    return {
        "email": "test@gmail.com",
        "password": "securepassword123"
    }


@pytest.fixture
def auth_service(mock_db_session):
    """Create auth service instance."""
    from app.auth.services import AuthService
    return AuthService(mock_db_session)


@pytest.fixture
def mock_session_service():
    """Mock session service."""
    return AsyncMock()