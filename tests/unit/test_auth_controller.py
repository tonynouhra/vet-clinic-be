"""
Unit tests for authentication controller.
Tests user registration, login, logout, and session management functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.controller import AuthController
from app.models.user import User, UserRole
from app.core.exceptions import (
    ValidationError,
    ConflictError,
    BusinessLogicError,
    AuthenticationError
)


class TestAuthController:
    """Test authentication controller functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_auth_service(self):
        """Mock authentication service."""
        return AsyncMock()

    @pytest.fixture
    def auth_controller(self, mock_db_session):
        """Create auth controller instance."""
        return AuthController(mock_db_session)

    @pytest.fixture
    def sample_user(self):
        """Sample user object."""
        user = Mock(spec=User)
        user.id = "user_123"
        user.email = "test@example.com"
        user.first_name = "John"
        user.last_name = "Doe"
        user.phone_number = "+1234567890"
        user.role = UserRole.PET_OWNER
        user.is_active = True
        user.is_verified = False
        user.last_login = None
        user.created_at = datetime.utcnow()
        return user

    @pytest.fixture
    def valid_registration_data(self):
        """Valid registration data."""
        return {
            "email": "test@example.com",
            "password": "securepassword123",
            "confirm_password": "securepassword123",
            "first_name": "John",
            "last_name": "Doe",
            "phone_number": "+1234567890",
            "role": UserRole.PET_OWNER
        }

    @pytest.fixture
    def valid_login_data(self):
        """Valid login data."""
        return {
            "email": "test@example.com",
            "password": "securepassword123"
        }


class TestUserRegistration:
    """Test user registration functionality."""

    @pytest.mark.asyncio
    async def test_register_user_success(
        self, auth_controller, mock_auth_service, valid_registration_data, sample_user
    ):
        """Test successful user registration."""
        # Mock service methods
        auth_controller.service = mock_auth_service
        mock_auth_service.get_user_by_email.return_value = None
        mock_auth_service.create_user.return_value = sample_user

        result = await auth_controller.register_user(
            registration_data=valid_registration_data,
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0"
        )

        assert result["user"] == sample_user
        assert result["message"] == "User registered successfully"
        assert result["verification_required"] is True
        mock_auth_service.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_missing_required_fields(self, auth_controller):
        """Test registration with missing required fields."""
        incomplete_data = {
            "email": "test@example.com",
            "password": "securepassword123"
            # Missing first_name, last_name, confirm_password
        }

        with pytest.raises(ValidationError, match="Email, password, first_name, and last_name are required"):
            await auth_controller.register_user(registration_data=incomplete_data)

    @pytest.mark.asyncio
    async def test_register_user_invalid_email(self, auth_controller):
        """Test registration with invalid email."""
        invalid_data = {
            "email": "invalid-email",
            "password": "securepassword123",
            "confirm_password": "securepassword123",
            "first_name": "John",
            "last_name": "Doe"
        }

        with pytest.raises(ValidationError):
            await auth_controller.register_user(registration_data=invalid_data)

    @pytest.mark.asyncio
    async def test_register_user_password_mismatch(self, auth_controller):
        """Test registration with password mismatch."""
        mismatch_data = {
            "email": "test@example.com",
            "password": "securepassword123",
            "confirm_password": "differentpassword",
            "first_name": "John",
            "last_name": "Doe"
        }

        with pytest.raises(ValidationError, match="Passwords do not match"):
            await auth_controller.register_user(registration_data=mismatch_data)

    @pytest.mark.asyncio
    async def test_register_user_weak_password(self, auth_controller):
        """Test registration with weak password."""
        weak_password_data = {
            "email": "test@example.com",
            "password": "weak",
            "confirm_password": "weak",
            "first_name": "John",
            "last_name": "Doe"
        }

        with pytest.raises(ValidationError, match="Password must be at least 8 characters long"):
            await auth_controller.register_user(registration_data=weak_password_data)

    @pytest.mark.asyncio
    async def test_register_user_existing_email(
        self, auth_controller, mock_auth_service, valid_registration_data, sample_user
    ):
        """Test registration with existing email."""
        auth_controller.service = mock_auth_service
        mock_auth_service.get_user_by_email.return_value = sample_user

        with pytest.raises(ConflictError, match="User with this email already exists"):
            await auth_controller.register_user(registration_data=valid_registration_data)


class TestUserLogin:
    """Test user login functionality."""

    @pytest.mark.asyncio
    async def test_login_user_success(
        self, auth_controller, mock_auth_service, valid_login_data, sample_user
    ):
        """Test successful user login."""
        auth_controller.service = mock_auth_service
        
        # Mock successful authentication
        auth_result = {
            "success": True,
            "user": sample_user,
            "session": {
                "session_id": "session_123",
                "access_token": "jwt_token_123",
                "expires_in": 3600,
                "refresh_token": None
            }
        }
        mock_auth_service.authenticate_user.return_value = auth_result

        with patch("app.auth.controller.get_user_permissions") as mock_get_permissions:
            mock_get_permissions.return_value = ["pets:read", "pets:write"]
            
            result = await auth_controller.login_user(
                login_data=valid_login_data,
                ip_address="192.168.1.1",
                user_agent="TestAgent/1.0"
            )

        assert result["user"]["id"] == sample_user.id
        assert result["user"]["email"] == sample_user.email
        assert result["token"]["access_token"] == "jwt_token_123"
        assert result["permissions"] == ["pets:read", "pets:write"]
        assert result["session_id"] == "session_123"

    @pytest.mark.asyncio
    async def test_login_user_missing_credentials(self, auth_controller):
        """Test login with missing credentials."""
        incomplete_data = {
            "email": "test@example.com"
            # Missing password
        }

        with pytest.raises(ValidationError, match="Email and password are required"):
            await auth_controller.login_user(login_data=incomplete_data)

    @pytest.mark.asyncio
    async def test_login_user_invalid_credentials(
        self, auth_controller, mock_auth_service, valid_login_data
    ):
        """Test login with invalid credentials."""
        auth_controller.service = mock_auth_service
        
        # Mock failed authentication
        auth_result = {
            "success": False,
            "message": "Invalid email or password"
        }
        mock_auth_service.authenticate_user.return_value = auth_result

        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await auth_controller.login_user(login_data=valid_login_data)

    @pytest.mark.asyncio
    async def test_login_user_invalid_email_format(self, auth_controller):
        """Test login with invalid email format."""
        invalid_data = {
            "email": "invalid-email",
            "password": "securepassword123"
        }

        with pytest.raises(ValidationError):
            await auth_controller.login_user(login_data=invalid_data)


class TestUserLogout:
    """Test user logout functionality."""

    @pytest.mark.asyncio
    async def test_logout_user_single_session(self, auth_controller, mock_auth_service):
        """Test logout from single session."""
        auth_controller.service = mock_auth_service
        mock_auth_service.logout_session.return_value = True

        logout_data = {
            "session_id": "session_123",
            "logout_all_sessions": False
        }

        result = await auth_controller.logout_user(
            logout_data=logout_data,
            current_user_id="user_123"
        )

        assert result["success"] is True
        assert "Logged out successfully" in result["message"]
        mock_auth_service.logout_session.assert_called_once_with("session_123")

    @pytest.mark.asyncio
    async def test_logout_user_all_sessions(self, auth_controller, mock_auth_service):
        """Test logout from all sessions."""
        auth_controller.service = mock_auth_service
        mock_auth_service.logout_all_sessions.return_value = 3

        logout_data = {
            "session_id": "session_123",
            "logout_all_sessions": True
        }

        result = await auth_controller.logout_user(
            logout_data=logout_data,
            current_user_id="user_123"
        )

        assert result["success"] is True
        assert "Logged out from 3 sessions" in result["message"]
        mock_auth_service.logout_all_sessions.assert_called_once_with(
            user_id="user_123",
            exclude_session="session_123"
        )

    @pytest.mark.asyncio
    async def test_logout_user_missing_session_id(self, auth_controller):
        """Test logout without session ID."""
        logout_data = {
            "logout_all_sessions": False
        }

        with pytest.raises(ValidationError, match="Session ID is required for logout"):
            await auth_controller.logout_user(
                logout_data=logout_data,
                current_user_id="user_123"
            )


class TestPasswordManagement:
    """Test password change and reset functionality."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, auth_controller, mock_auth_service):
        """Test successful password change."""
        auth_controller.service = mock_auth_service
        mock_auth_service.change_password.return_value = {
            "success": True,
            "message": "Password changed successfully"
        }

        password_data = {
            "current_password": "oldpassword123",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123"
        }

        result = await auth_controller.change_password(
            password_data=password_data,
            current_user_id="user_123"
        )

        assert result["success"] is True
        assert result["message"] == "Password changed successfully"
        mock_auth_service.change_password.assert_called_once_with(
            user_id="user_123",
            current_password="oldpassword123",
            new_password="newpassword123"
        )

    @pytest.mark.asyncio
    async def test_change_password_missing_fields(self, auth_controller):
        """Test password change with missing fields."""
        incomplete_data = {
            "current_password": "oldpassword123",
            "new_password": "newpassword123"
            # Missing confirm_password
        }

        with pytest.raises(ValidationError, match="Current password, new password, and confirmation are required"):
            await auth_controller.change_password(
                password_data=incomplete_data,
                current_user_id="user_123"
            )

    @pytest.mark.asyncio
    async def test_change_password_mismatch(self, auth_controller):
        """Test password change with password mismatch."""
        mismatch_data = {
            "current_password": "oldpassword123",
            "new_password": "newpassword123",
            "confirm_password": "differentpassword"
        }

        with pytest.raises(ValidationError, match="New passwords do not match"):
            await auth_controller.change_password(
                password_data=mismatch_data,
                current_user_id="user_123"
            )

    @pytest.mark.asyncio
    async def test_change_password_weak_password(self, auth_controller):
        """Test password change with weak new password."""
        weak_password_data = {
            "current_password": "oldpassword123",
            "new_password": "weak",
            "confirm_password": "weak"
        }

        with pytest.raises(ValidationError, match="New password must be at least 8 characters long"):
            await auth_controller.change_password(
                password_data=weak_password_data,
                current_user_id="user_123"
            )

    @pytest.mark.asyncio
    async def test_change_password_incorrect_current(self, auth_controller, mock_auth_service):
        """Test password change with incorrect current password."""
        auth_controller.service = mock_auth_service
        mock_auth_service.change_password.return_value = {
            "success": False,
            "message": "Current password is incorrect"
        }

        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123"
        }

        with pytest.raises(AuthenticationError, match="Current password is incorrect"):
            await auth_controller.change_password(
                password_data=password_data,
                current_user_id="user_123"
            )


class TestSessionManagement:
    """Test session management functionality."""

    @pytest.mark.asyncio
    async def test_get_user_sessions(self, auth_controller, mock_auth_service):
        """Test getting user sessions."""
        auth_controller.service = mock_auth_service
        
        mock_sessions = [
            {
                "session_id": "session_1",
                "created_at": "2024-01-01T10:00:00Z",
                "last_activity": "2024-01-01T11:00:00Z",
                "ip_address": "192.168.1.1",
                "user_agent": "TestAgent/1.0",
                "is_active": True
            },
            {
                "session_id": "session_2",
                "created_at": "2024-01-01T09:00:00Z",
                "last_activity": "2024-01-01T10:30:00Z",
                "ip_address": "192.168.1.2",
                "user_agent": "TestAgent/2.0",
                "is_active": True
            }
        ]
        mock_auth_service.get_user_sessions.return_value = mock_sessions

        result = await auth_controller.get_user_sessions(user_id="user_123")

        assert result["sessions"] == mock_sessions
        assert result["total"] == 2
        mock_auth_service.get_user_sessions.assert_called_once_with("user_123")

    @pytest.mark.asyncio
    async def test_refresh_token_not_implemented(self, auth_controller, mock_auth_service):
        """Test token refresh (not implemented yet)."""
        auth_controller.service = mock_auth_service
        mock_auth_service.refresh_access_token.return_value = {
            "success": False,
            "message": "Refresh tokens not implemented yet"
        }

        refresh_data = {
            "refresh_token": "refresh_token_123"
        }

        with pytest.raises(AuthenticationError, match="Refresh tokens not implemented yet"):
            await auth_controller.refresh_token(refresh_data=refresh_data)


class TestPermissionManagement:
    """Test permission checking functionality."""

    @pytest.mark.asyncio
    async def test_check_permission_has_permission(self, auth_controller):
        """Test permission check when user has permission."""
        with patch("app.auth.controller.get_user_permissions") as mock_get_permissions:
            mock_get_permissions.return_value = ["pets:read", "pets:write", "users:read"]
            
            result = await auth_controller.check_permission(
                permission="pets:read",
                user_role="veterinarian"
            )

        assert result["permission"] == "pets:read"
        assert result["has_permission"] is True
        assert result["reason"] is None

    @pytest.mark.asyncio
    async def test_check_permission_no_permission(self, auth_controller):
        """Test permission check when user lacks permission."""
        with patch("app.auth.controller.get_user_permissions") as mock_get_permissions:
            mock_get_permissions.return_value = ["pets:read"]
            
            result = await auth_controller.check_permission(
                permission="users:delete",
                user_role="pet_owner"
            )

        assert result["permission"] == "users:delete"
        assert result["has_permission"] is False
        assert "does not have permission" in result["reason"]

    @pytest.mark.asyncio
    async def test_check_permission_admin_has_all(self, auth_controller):
        """Test permission check for admin user (has all permissions)."""
        with patch("app.auth.controller.get_user_permissions") as mock_get_permissions:
            mock_get_permissions.return_value = ["*"]
            
            result = await auth_controller.check_permission(
                permission="any:permission",
                user_role="admin"
            )

        assert result["permission"] == "any:permission"
        assert result["has_permission"] is True
        assert result["reason"] is None

    @pytest.mark.asyncio
    async def test_get_role_permissions_valid_role(self, auth_controller):
        """Test getting permissions for valid role."""
        with patch("app.auth.controller.get_user_permissions") as mock_get_permissions:
            mock_get_permissions.return_value = ["pets:read", "pets:write"]
            
            result = await auth_controller.get_role_permissions(role="veterinarian")

        assert result["role"] == "veterinarian"
        assert result["permissions"] == ["pets:read", "pets:write"]

    @pytest.mark.asyncio
    async def test_get_role_permissions_invalid_role(self, auth_controller):
        """Test getting permissions for invalid role."""
        with pytest.raises(ValidationError, match="Invalid role: invalid_role"):
            await auth_controller.get_role_permissions(role="invalid_role")


class TestPasswordReset:
    """Test password reset functionality."""

    @pytest.mark.asyncio
    async def test_request_password_reset_success(self, auth_controller, mock_auth_service):
        """Test successful password reset request."""
        auth_controller.service = mock_auth_service
        mock_auth_service.request_password_reset.return_value = {
            "success": True,
            "message": "Password reset instructions sent"
        }

        reset_data = {
            "email": "test@example.com"
        }

        result = await auth_controller.request_password_reset(reset_data=reset_data)

        assert result["success"] is True
        assert "Password reset instructions sent" in result["message"]
        mock_auth_service.request_password_reset.assert_called_once_with("test@example.com")

    @pytest.mark.asyncio
    async def test_request_password_reset_missing_email(self, auth_controller):
        """Test password reset request without email."""
        reset_data = {}

        with pytest.raises(ValidationError, match="Email is required"):
            await auth_controller.request_password_reset(reset_data=reset_data)

    @pytest.mark.asyncio
    async def test_confirm_password_reset_not_implemented(self, auth_controller, mock_auth_service):
        """Test password reset confirmation (not implemented yet)."""
        auth_controller.service = mock_auth_service
        mock_auth_service.confirm_password_reset.return_value = {
            "success": False,
            "message": "Password reset not fully implemented yet"
        }

        reset_data = {
            "token": "reset_token_123",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123"
        }

        with pytest.raises(AuthenticationError, match="Password reset not fully implemented yet"):
            await auth_controller.confirm_password_reset(reset_data=reset_data)