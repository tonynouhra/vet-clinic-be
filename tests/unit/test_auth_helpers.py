"""
Unit tests for authentication helpers.
Tests JWT token validation, user authentication, and role-based access control.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.security import HTTPAuthorizationCredentials
from datetime import datetime, timedelta

from app.app_helpers.auth_helpers import (
    verify_token,
    get_current_user,
    require_role,
    require_any_role,
    require_permission,
    is_owner_or_admin,
    create_access_token,
    get_optional_user,
    has_role_access,
    ROLE_HIERARCHY
)
from app.core.exceptions import AuthenticationError, AuthorizationError


class TestVerifyToken:
    """Test JWT token verification with Clerk integration."""

    @pytest.fixture
    def mock_credentials(self):
        """Mock HTTP authorization credentials."""
        return HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_jwt_token"
        )

    @pytest.fixture
    def mock_clerk_service(self):
        """Mock Clerk service."""
        mock_service = AsyncMock()
        return mock_service

    @pytest.fixture
    def valid_token_data(self):
        """Valid token data from Clerk."""
        return {
            "user_id": "user_123",
            "clerk_id": "clerk_456",
            "email": "test@example.com",
            "role": "veterinarian",
            "permissions": ["pets:read", "pets:write"],
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "session_id": "session_789"
        }

    @pytest.mark.asyncio
    async def test_verify_token_success(self, mock_credentials, mock_clerk_service, valid_token_data):
        """Test successful token verification."""
        mock_clerk_service.verify_jwt_token.return_value = valid_token_data
        
        with patch("app.app_helpers.auth_helpers.get_clerk_service", return_value=mock_clerk_service):
            result = await verify_token(mock_credentials)
        
        assert result["user_id"] == "user_123"
        assert result["clerk_id"] == "clerk_456"
        assert result["email"] == "test@example.com"
        assert result["role"] == "veterinarian"
        assert result["permissions"] == ["pets:read", "pets:write"]
        assert result["session_id"] == "session_789"
        mock_clerk_service.verify_jwt_token.assert_called_once_with("valid_jwt_token")

    @pytest.mark.asyncio
    async def test_verify_token_invalid_token(self, mock_credentials, mock_clerk_service):
        """Test token verification with invalid token."""
        mock_clerk_service.verify_jwt_token.side_effect = AuthenticationError("Invalid token")
        
        with patch("app.app_helpers.auth_helpers.get_clerk_service", return_value=mock_clerk_service):
            with pytest.raises(AuthenticationError, match="Invalid token"):
                await verify_token(mock_credentials)

    @pytest.mark.asyncio
    async def test_verify_token_expired_token(self, mock_credentials, mock_clerk_service):
        """Test token verification with expired token."""
        mock_clerk_service.verify_jwt_token.side_effect = AuthenticationError("Token has expired")
        
        with patch("app.app_helpers.auth_helpers.get_clerk_service", return_value=mock_clerk_service):
            with pytest.raises(AuthenticationError, match="Token has expired"):
                await verify_token(mock_credentials)

    @pytest.mark.asyncio
    async def test_verify_token_clerk_service_error(self, mock_credentials, mock_clerk_service):
        """Test token verification when Clerk service fails."""
        mock_clerk_service.verify_jwt_token.side_effect = Exception("Service unavailable")
        
        with patch("app.app_helpers.auth_helpers.get_clerk_service", return_value=mock_clerk_service):
            with pytest.raises(AuthenticationError, match="Token verification failed"):
                await verify_token(mock_credentials)

    @pytest.mark.asyncio
    async def test_verify_token_missing_user_id(self, mock_credentials, mock_clerk_service):
        """Test token verification with missing user ID."""
        invalid_token_data = {
            "clerk_id": "clerk_456",
            "email": "test@example.com"
        }
        mock_clerk_service.verify_jwt_token.return_value = invalid_token_data
        
        with patch("app.app_helpers.auth_helpers.get_clerk_service", return_value=mock_clerk_service):
            result = await verify_token(mock_credentials)
            # Should still work as long as Clerk service returns the data
            assert result["user_id"] is None
            assert result["clerk_id"] == "clerk_456"
            assert result["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_verify_token_default_role(self, mock_credentials, mock_clerk_service):
        """Test token verification with default role assignment."""
        token_data_no_role = {
            "user_id": "user_123",
            "clerk_id": "clerk_456",
            "email": "test@example.com"
        }
        mock_clerk_service.verify_jwt_token.return_value = token_data_no_role
        
        with patch("app.app_helpers.auth_helpers.get_clerk_service", return_value=mock_clerk_service):
            result = await verify_token(mock_credentials)
        
        assert result["role"] == "pet_owner"  # Default role
        assert result["permissions"] == []  # Default permissions


class TestGetCurrentUser:
    """Test getting current user from token data."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """Test successful user retrieval."""
        token_data = {
            "user_id": "user_123",
            "email": "test@example.com",
            "role": "veterinarian"
        }
        
        result = await get_current_user(token_data)
        assert result == token_data


class TestRequireRole:
    """Test role-based access control."""

    @pytest.mark.asyncio
    async def test_require_role_success(self):
        """Test successful role requirement."""
        user_data = {"user_id": "user_123", "role": "admin"}
        require_admin = require_role("admin")
        
        result = await require_admin(user_data)
        assert result == user_data

    @pytest.mark.asyncio
    async def test_require_role_insufficient_permissions(self):
        """Test role requirement with insufficient permissions."""
        user_data = {"user_id": "user_123", "role": "pet_owner"}
        require_admin = require_role("admin")
        
        with pytest.raises(AuthorizationError) as exc_info:
            await require_admin(user_data)
        
        assert "Access denied" in str(exc_info.value)
        assert "Required role: admin" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_require_role_missing_role(self):
        """Test role requirement with missing role in user data."""
        user_data = {"user_id": "user_123"}
        require_admin = require_role("admin")
        
        with pytest.raises(AuthorizationError):
            await require_admin(user_data)


class TestRequireAnyRole:
    """Test multiple role access control."""

    @pytest.mark.asyncio
    async def test_require_any_role_success(self):
        """Test successful any role requirement."""
        user_data = {"user_id": "user_123", "role": "veterinarian"}
        require_staff = require_any_role(["admin", "veterinarian", "receptionist"])
        
        result = await require_staff(user_data)
        assert result == user_data

    @pytest.mark.asyncio
    async def test_require_any_role_insufficient_permissions(self):
        """Test any role requirement with insufficient permissions."""
        user_data = {"user_id": "user_123", "role": "pet_owner"}
        require_staff = require_any_role(["admin", "veterinarian", "receptionist"])
        
        with pytest.raises(AuthorizationError) as exc_info:
            await require_staff(user_data)
        
        assert "Access denied" in str(exc_info.value)
        assert "admin, veterinarian, receptionist" in str(exc_info.value)


class TestRequirePermission:
    """Test permission-based access control."""

    @pytest.mark.asyncio
    async def test_require_permission_success(self):
        """Test successful permission requirement."""
        user_data = {
            "user_id": "user_123",
            "permissions": ["pets:read", "pets:write", "users:read"]
        }
        require_pets_write = require_permission("pets:write")
        
        result = await require_pets_write(user_data)
        assert result == user_data

    @pytest.mark.asyncio
    async def test_require_permission_insufficient_permissions(self):
        """Test permission requirement with insufficient permissions."""
        user_data = {
            "user_id": "user_123",
            "permissions": ["pets:read"]
        }
        require_pets_write = require_permission("pets:write")
        
        with pytest.raises(AuthorizationError) as exc_info:
            await require_pets_write(user_data)
        
        assert "Access denied" in str(exc_info.value)
        assert "Required permission: pets:write" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_require_permission_missing_permissions(self):
        """Test permission requirement with missing permissions in user data."""
        user_data = {"user_id": "user_123"}
        require_pets_write = require_permission("pets:write")
        
        with pytest.raises(AuthorizationError):
            await require_pets_write(user_data)


class TestIsOwnerOrAdmin:
    """Test ownership and admin access control."""

    @pytest.mark.asyncio
    async def test_is_owner_or_admin_owner_access(self):
        """Test owner access to their own resource."""
        user_data = {"user_id": "user_123", "role": "pet_owner"}
        check_access = is_owner_or_admin("user_123")
        
        result = await check_access(user_data)
        assert result == user_data

    @pytest.mark.asyncio
    async def test_is_owner_or_admin_admin_access(self):
        """Test admin access to any resource."""
        user_data = {"user_id": "admin_456", "role": "admin"}
        check_access = is_owner_or_admin("user_123")
        
        result = await check_access(user_data)
        assert result == user_data

    @pytest.mark.asyncio
    async def test_is_owner_or_admin_denied_access(self):
        """Test denied access for non-owner, non-admin."""
        user_data = {"user_id": "user_789", "role": "pet_owner"}
        check_access = is_owner_or_admin("user_123")
        
        with pytest.raises(AuthorizationError) as exc_info:
            await check_access(user_data)
        
        assert "Access denied" in str(exc_info.value)
        assert "your own resources" in str(exc_info.value)


class TestCreateAccessToken:
    """Test JWT token creation for development/testing."""

    @patch("app.app_helpers.auth_helpers.settings")
    def test_create_access_token_basic(self, mock_settings):
        """Test basic token creation."""
        mock_settings.ENVIRONMENT = "development"
        mock_settings.JWT_SECRET_KEY = "test_secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_settings.CLERK_JWT_ISSUER = "https://test.clerk.dev"
        
        token = create_access_token(
            user_id="user_123",
            email="test@example.com",
            role="veterinarian"
        )
        
        assert isinstance(token, str)
        assert len(token) > 0

    @patch("app.app_helpers.auth_helpers.settings")
    def test_create_access_token_with_clerk_id(self, mock_settings):
        """Test token creation with Clerk ID."""
        mock_settings.ENVIRONMENT = "development"
        mock_settings.JWT_SECRET_KEY = "test_secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_settings.CLERK_JWT_ISSUER = "https://test.clerk.dev"
        
        token = create_access_token(
            user_id="user_123",
            email="test@example.com",
            role="veterinarian",
            clerk_id="clerk_456",
            permissions=["pets:read", "pets:write"]
        )
        
        assert isinstance(token, str)
        assert len(token) > 0

    @patch("app.app_helpers.auth_helpers.settings")
    @patch("app.app_helpers.auth_helpers.logger")
    def test_create_access_token_production_warning(self, mock_logger, mock_settings):
        """Test warning when creating token in production."""
        mock_settings.ENVIRONMENT = "production"
        mock_settings.JWT_SECRET_KEY = "test_secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_settings.CLERK_JWT_ISSUER = "https://test.clerk.dev"
        
        token = create_access_token(
            user_id="user_123",
            email="test@example.com"
        )
        
        assert isinstance(token, str)
        mock_logger.warning.assert_called_once()


class TestGetOptionalUser:
    """Test optional user authentication."""

    @pytest.mark.asyncio
    async def test_get_optional_user_with_valid_token(self):
        """Test optional user with valid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        with patch("app.app_helpers.auth_helpers.verify_token") as mock_verify:
            mock_verify.return_value = {"user_id": "user_123"}
            get_user = get_optional_user()
            
            result = await get_user(credentials)
            assert result == {"user_id": "user_123"}

    @pytest.mark.asyncio
    async def test_get_optional_user_with_no_token(self):
        """Test optional user with no token."""
        get_user = get_optional_user()
        result = await get_user(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_with_invalid_token(self):
        """Test optional user with invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid_token"
        )
        
        with patch("app.app_helpers.auth_helpers.verify_token") as mock_verify:
            mock_verify.side_effect = AuthenticationError("Invalid token")
            get_user = get_optional_user()
            
            result = await get_user(credentials)
            assert result is None


class TestRoleHierarchy:
    """Test role hierarchy and access control."""

    def test_has_role_access_admin(self):
        """Test admin role access."""
        assert has_role_access("admin", "admin") is True
        assert has_role_access("admin", "veterinarian") is True
        assert has_role_access("admin", "receptionist") is True
        assert has_role_access("admin", "pet_owner") is True

    def test_has_role_access_veterinarian(self):
        """Test veterinarian role access."""
        assert has_role_access("veterinarian", "admin") is False
        assert has_role_access("veterinarian", "veterinarian") is True
        assert has_role_access("veterinarian", "receptionist") is False
        assert has_role_access("veterinarian", "pet_owner") is True

    def test_has_role_access_receptionist(self):
        """Test receptionist role access."""
        assert has_role_access("receptionist", "admin") is False
        assert has_role_access("receptionist", "veterinarian") is False
        assert has_role_access("receptionist", "receptionist") is True
        assert has_role_access("receptionist", "pet_owner") is True

    def test_has_role_access_pet_owner(self):
        """Test pet owner role access."""
        assert has_role_access("pet_owner", "admin") is False
        assert has_role_access("pet_owner", "veterinarian") is False
        assert has_role_access("pet_owner", "receptionist") is False
        assert has_role_access("pet_owner", "pet_owner") is True

    def test_has_role_access_unknown_role(self):
        """Test unknown role access."""
        assert has_role_access("unknown", "admin") is False
        assert has_role_access("unknown", "pet_owner") is False

    def test_role_hierarchy_structure(self):
        """Test role hierarchy structure."""
        assert "admin" in ROLE_HIERARCHY
        assert "veterinarian" in ROLE_HIERARCHY
        assert "receptionist" in ROLE_HIERARCHY
        assert "pet_owner" in ROLE_HIERARCHY
        
        # Admin should have access to all roles
        assert len(ROLE_HIERARCHY["admin"]) == 4
        assert "admin" in ROLE_HIERARCHY["admin"]
        assert "veterinarian" in ROLE_HIERARCHY["admin"]
        assert "receptionist" in ROLE_HIERARCHY["admin"]
        assert "pet_owner" in ROLE_HIERARCHY["admin"]
        
        # Pet owner should only have access to pet_owner role
        assert len(ROLE_HIERARCHY["pet_owner"]) == 1
        assert "pet_owner" in ROLE_HIERARCHY["pet_owner"]