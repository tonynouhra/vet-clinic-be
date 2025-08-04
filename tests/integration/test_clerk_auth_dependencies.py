"""
Integration tests for Clerk authentication dependencies.
Tests the complete authentication flow including token validation, user synchronization,
and role-based access control.
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.api.deps import (
    verify_clerk_token,
    sync_clerk_user,
    get_current_user,
    get_current_active_user,
    require_role,
    require_any_role,
    require_permission,
    require_staff_role,
    require_admin_role,
    require_veterinarian_role,
    get_optional_user
)
from app.models.user import User, UserRole
from app.schemas.clerk_schemas import ClerkUser, ClerkEmailAddress
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.schemas.clerk_schemas import ClerkUserSyncResponse


class TestClerkTokenVerification:
    """Test Clerk JWT token verification integration."""

    @pytest.fixture
    def mock_clerk_service(self):
        """Mock Clerk service for testing."""
        service = AsyncMock()
        return service

    @pytest.fixture
    def valid_token_data(self):
        """Valid token data from Clerk."""
        return {
            "clerk_id": "user_clerk_123",
            "user_id": "user_123",
            "email": "test@vetclinic.com",
            "role": "veterinarian",
            "permissions": ["pets:read", "pets:write"],
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "session_id": "session_456"
        }

    @pytest.fixture
    def mock_credentials(self):
        """Mock HTTP authorization credentials."""
        return HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_jwt_token_from_clerk"
        )

    @pytest.mark.asyncio
    async def test_verify_clerk_token_success(
        self, mock_clerk_service, valid_token_data, mock_credentials
    ):
        """Test successful Clerk token verification."""
        mock_clerk_service.verify_jwt_token.return_value = valid_token_data

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service):
            result = await verify_clerk_token(mock_credentials)

        assert result == valid_token_data
        mock_clerk_service.verify_jwt_token.assert_called_once_with("valid_jwt_token_from_clerk")

    @pytest.mark.asyncio
    async def test_verify_clerk_token_authentication_error(
        self, mock_clerk_service, mock_credentials
    ):
        """Test token verification with authentication error."""
        mock_clerk_service.verify_jwt_token.side_effect = AuthenticationError("Invalid token")

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service):
            with pytest.raises(HTTPException) as exc_info:
                await verify_clerk_token(mock_credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_verify_clerk_token_generic_error(
        self, mock_clerk_service, mock_credentials
    ):
        """Test token verification with generic error."""
        mock_clerk_service.verify_jwt_token.side_effect = Exception("Service unavailable")

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service):
            with pytest.raises(HTTPException) as exc_info:
                await verify_clerk_token(mock_credentials)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)


class TestUserSynchronization:
    """Test user synchronization with Clerk data."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_clerk_service(self):
        """Mock Clerk service."""
        return AsyncMock()

    @pytest.fixture
    def mock_user_sync_service(self):
        """Mock user synchronization service."""
        return AsyncMock()

    @pytest.fixture
    def sample_clerk_user(self):
        """Sample Clerk user data."""
        return ClerkUser(
            id="user_clerk_123",
            email_addresses=[
                ClerkEmailAddress(id="email_123", email_address="test@vetclinic.com")
            ],
            first_name="Dr. John",
            last_name="Smith",
            public_metadata={"role": "veterinarian"},
            private_metadata={"preferences": {"notifications": True}},
            created_at=1640995200000,
            updated_at=1640995200000
        )

    @pytest.fixture
    def sample_local_user(self):
        """Sample local user object."""
        user = Mock(spec=User)
        user.id = "user_123"
        user.clerk_id = "user_clerk_123"
        user.email = "test@vetclinic.com"
        user.first_name = "Dr. John"
        user.last_name = "Smith"
        user.role = UserRole.VETERINARIAN
        user.is_active = True
        return user

    @pytest.mark.asyncio
    async def test_sync_clerk_user_success(
        self,
        mock_db_session,
        mock_clerk_service,
        mock_user_sync_service,
        sample_clerk_user,
        sample_local_user
    ):
        """Test successful user synchronization."""
        token_data = {"clerk_id": "user_clerk_123"}
        
        # Mock service responses
        mock_clerk_service.get_user_by_clerk_id.return_value = sample_clerk_user
        mock_user_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
            success=True,
            action="updated",
            message="User synchronized successfully"
        )
        mock_user_sync_service.get_user_by_clerk_id.return_value = sample_local_user

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService", return_value=mock_user_sync_service):
            
            result = await sync_clerk_user(token_data, mock_db_session)

        assert result == sample_local_user
        mock_clerk_service.get_user_by_clerk_id.assert_called_once_with("user_clerk_123")
        mock_user_sync_service.sync_user_data.assert_called_once()
        mock_user_sync_service.get_user_by_clerk_id.assert_called_once_with("user_clerk_123")

    @pytest.mark.asyncio
    async def test_sync_clerk_user_sync_failure(
        self,
        mock_db_session,
        mock_clerk_service,
        mock_user_sync_service,
        sample_clerk_user
    ):
        """Test user synchronization failure."""
        token_data = {"clerk_id": "user_clerk_123"}
        
        mock_clerk_service.get_user_by_clerk_id.return_value = sample_clerk_user
        mock_user_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
            success=False,
            action="failed",
            message="Database error"
        )

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService", return_value=mock_user_sync_service):
            
            with pytest.raises(HTTPException) as exc_info:
                await sync_clerk_user(token_data, mock_db_session)

        assert exc_info.value.status_code == 500
        assert "User synchronization failed: Database error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_sync_clerk_user_not_found_after_sync(
        self,
        mock_db_session,
        mock_clerk_service,
        mock_user_sync_service,
        sample_clerk_user
    ):
        """Test user not found after synchronization."""
        token_data = {"clerk_id": "user_clerk_123"}
        
        mock_clerk_service.get_user_by_clerk_id.return_value = sample_clerk_user
        mock_user_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
            success=True,
            action="updated",
            message="User synchronized successfully"
        )
        mock_user_sync_service.get_user_by_clerk_id.return_value = None

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService", return_value=mock_user_sync_service):
            
            with pytest.raises(HTTPException) as exc_info:
                await sync_clerk_user(token_data, mock_db_session)

        assert exc_info.value.status_code == 500
        assert "User not found after synchronization" in str(exc_info.value.detail)


class TestCurrentUserDependencies:
    """Test current user dependency functions."""

    @pytest.fixture
    def active_user(self):
        """Active user mock."""
        user = Mock(spec=User)
        user.is_active = True
        user.role = UserRole.VETERINARIAN
        return user

    @pytest.fixture
    def inactive_user(self):
        """Inactive user mock."""
        user = Mock(spec=User)
        user.is_active = False
        user.role = UserRole.PET_OWNER
        return user

    @pytest.mark.asyncio
    async def test_get_current_user_active(self, active_user):
        """Test getting current active user."""
        result = await get_current_user(active_user)
        assert result == active_user

    @pytest.mark.asyncio
    async def test_get_current_user_inactive(self, inactive_user):
        """Test getting current inactive user raises exception."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(inactive_user)

        assert exc_info.value.status_code == 401
        assert "User account is inactive" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_active_user_success(self, active_user):
        """Test getting current active user successfully."""
        result = await get_current_active_user(active_user)
        assert result == active_user

    @pytest.mark.asyncio
    async def test_get_current_active_user_inactive(self, inactive_user):
        """Test getting current active user with inactive user."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(inactive_user)

        assert exc_info.value.status_code == 400
        assert "Inactive user" in str(exc_info.value.detail)


class TestRoleBasedAccessControl:
    """Test role-based access control dependencies."""

    @pytest.fixture
    def admin_user(self):
        """Admin user mock."""
        user = Mock(spec=User)
        user.role = UserRole.ADMIN
        user.is_active = True
        return user

    @pytest.fixture
    def veterinarian_user(self):
        """Veterinarian user mock."""
        user = Mock(spec=User)
        user.role = UserRole.VETERINARIAN
        user.is_active = True
        return user

    @pytest.fixture
    def receptionist_user(self):
        """Receptionist user mock."""
        user = Mock(spec=User)
        user.role = UserRole.RECEPTIONIST
        user.is_active = True
        return user

    @pytest.fixture
    def pet_owner_user(self):
        """Pet owner user mock."""
        user = Mock(spec=User)
        user.role = UserRole.PET_OWNER
        user.is_active = True
        return user

    @pytest.mark.asyncio
    async def test_require_role_success(self, admin_user):
        """Test successful role requirement."""
        require_admin = require_role(UserRole.ADMIN)
        result = await require_admin(admin_user)
        assert result == admin_user

    @pytest.mark.asyncio
    async def test_require_role_failure(self, pet_owner_user):
        """Test failed role requirement."""
        require_admin = require_role(UserRole.ADMIN)
        
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(pet_owner_user)

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail)
        assert "Required role: admin" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_require_any_role_success(self, veterinarian_user):
        """Test successful any role requirement."""
        require_staff = require_any_role([UserRole.ADMIN, UserRole.VETERINARIAN, UserRole.RECEPTIONIST])
        result = await require_staff(veterinarian_user)
        assert result == veterinarian_user

    @pytest.mark.asyncio
    async def test_require_any_role_failure(self, pet_owner_user):
        """Test failed any role requirement."""
        require_staff = require_any_role([UserRole.ADMIN, UserRole.VETERINARIAN, UserRole.RECEPTIONIST])
        
        with pytest.raises(HTTPException) as exc_info:
            await require_staff(pet_owner_user)

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_require_staff_role_admin(self, admin_user):
        """Test staff role requirement with admin user."""
        staff_dependency = require_staff_role()
        result = await staff_dependency(admin_user)
        assert result == admin_user

    @pytest.mark.asyncio
    async def test_require_staff_role_veterinarian(self, veterinarian_user):
        """Test staff role requirement with veterinarian user."""
        staff_dependency = require_staff_role()
        result = await staff_dependency(veterinarian_user)
        assert result == veterinarian_user

    @pytest.mark.asyncio
    async def test_require_staff_role_receptionist(self, receptionist_user):
        """Test staff role requirement with receptionist user."""
        staff_dependency = require_staff_role()
        result = await staff_dependency(receptionist_user)
        assert result == receptionist_user

    @pytest.mark.asyncio
    async def test_require_staff_role_failure(self, pet_owner_user):
        """Test staff role requirement failure with pet owner."""
        staff_dependency = require_staff_role()
        
        with pytest.raises(HTTPException) as exc_info:
            await staff_dependency(pet_owner_user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_admin_role_success(self, admin_user):
        """Test admin role requirement success."""
        admin_dependency = require_admin_role()
        result = await admin_dependency(admin_user)
        assert result == admin_user

    @pytest.mark.asyncio
    async def test_require_admin_role_failure(self, veterinarian_user):
        """Test admin role requirement failure."""
        admin_dependency = require_admin_role()
        
        with pytest.raises(HTTPException) as exc_info:
            await admin_dependency(veterinarian_user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_veterinarian_role_success(self, veterinarian_user):
        """Test veterinarian role requirement success."""
        vet_dependency = require_veterinarian_role()
        result = await vet_dependency(veterinarian_user)
        assert result == veterinarian_user

    @pytest.mark.asyncio
    async def test_require_veterinarian_role_failure(self, receptionist_user):
        """Test veterinarian role requirement failure."""
        vet_dependency = require_veterinarian_role()
        
        with pytest.raises(HTTPException) as exc_info:
            await vet_dependency(receptionist_user)

        assert exc_info.value.status_code == 403


class TestPermissionBasedAccessControl:
    """Test permission-based access control."""

    @pytest.fixture
    def user_with_permissions(self):
        """User with specific permissions."""
        user = Mock(spec=User)
        user.is_active = True
        user.has_permission = Mock(return_value=True)
        return user

    @pytest.fixture
    def user_without_permissions(self):
        """User without specific permissions."""
        user = Mock(spec=User)
        user.is_active = True
        user.has_permission = Mock(return_value=False)
        return user

    @pytest.mark.asyncio
    async def test_require_permission_success(self, user_with_permissions):
        """Test successful permission requirement."""
        require_pets_read = require_permission("pets:read")
        result = await require_pets_read(user_with_permissions)
        assert result == user_with_permissions
        user_with_permissions.has_permission.assert_called_once_with("pets:read")

    @pytest.mark.asyncio
    async def test_require_permission_failure(self, user_without_permissions):
        """Test failed permission requirement."""
        require_pets_write = require_permission("pets:write")
        
        with pytest.raises(HTTPException) as exc_info:
            await require_pets_write(user_without_permissions)

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail)
        assert "Required permission: pets:write" in str(exc_info.value.detail)
        user_without_permissions.has_permission.assert_called_once_with("pets:write")


class TestOptionalUserDependency:
    """Test optional user authentication dependency."""

    @pytest.fixture
    def mock_clerk_service(self):
        """Mock Clerk service."""
        return AsyncMock()

    @pytest.fixture
    def mock_user_sync_service(self):
        """Mock user sync service."""
        return AsyncMock()

    @pytest.fixture
    def valid_credentials(self):
        """Valid HTTP authorization credentials."""
        return HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )

    @pytest.fixture
    def sample_user(self):
        """Sample user object."""
        user = Mock(spec=User)
        user.is_active = True
        user.clerk_id = "user_clerk_123"
        return user

    @pytest.mark.asyncio
    async def test_get_optional_user_with_valid_token(
        self,
        valid_credentials,
        mock_clerk_service,
        mock_user_sync_service,
        sample_user
    ):
        """Test optional user with valid token."""
        token_data = {"clerk_id": "user_clerk_123"}
        clerk_user = Mock()
        
        mock_clerk_service.verify_jwt_token.return_value = token_data
        mock_clerk_service.get_user_by_clerk_id.return_value = clerk_user
        mock_user_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
            success=True,
            action="updated",
            message="Success"
        )
        mock_user_sync_service.get_user_by_clerk_id.return_value = sample_user

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService", return_value=mock_user_sync_service):
            
            result = await get_optional_user(valid_credentials, AsyncMock())

        assert result == sample_user

    @pytest.mark.asyncio
    async def test_get_optional_user_with_no_credentials(self):
        """Test optional user with no credentials."""
        result = await get_optional_user(None, AsyncMock())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_with_invalid_token(self, mock_clerk_service):
        """Test optional user with invalid token."""
        invalid_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid_token"
        )
        
        mock_clerk_service.verify_jwt_token.side_effect = Exception("Invalid token")

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service):
            result = await get_optional_user(invalid_credentials, AsyncMock())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_with_inactive_user(
        self,
        valid_credentials,
        mock_clerk_service,
        mock_user_sync_service
    ):
        """Test optional user with inactive user."""
        token_data = {"clerk_id": "user_clerk_123"}
        clerk_user = Mock()
        inactive_user = Mock(spec=User)
        inactive_user.is_active = False
        
        mock_clerk_service.verify_jwt_token.return_value = token_data
        mock_clerk_service.get_user_by_clerk_id.return_value = clerk_user
        mock_user_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
            success=True,
            action="updated",
            message="Success"
        )
        mock_user_sync_service.get_user_by_clerk_id.return_value = inactive_user

        with patch("app.api.deps.get_clerk_service", return_value=mock_clerk_service), \
             patch("app.api.deps.UserSyncService", return_value=mock_user_sync_service):
            
            result = await get_optional_user(valid_credentials, AsyncMock())

        assert result is None


class TestEndToEndAuthenticationFlow:
    """Test complete end-to-end authentication flow."""

    @pytest.fixture
    def test_app(self):
        """Test FastAPI application with authentication."""
        app = FastAPI()

        @app.get("/protected")
        async def protected_endpoint(
            current_user: User = Depends(get_current_user)
        ):
            return {"user_id": current_user.id, "role": current_user.role.value}

        @app.get("/admin-only")
        async def admin_endpoint(
            current_user: User = Depends(require_admin_role())
        ):
            return {"message": "Admin access granted"}

        @app.get("/staff-only")
        async def staff_endpoint(
            current_user: User = Depends(require_staff_role())
        ):
            return {"message": "Staff access granted"}

        @app.get("/optional-auth")
        async def optional_auth_endpoint(
            current_user: User = Depends(get_optional_user)
        ):
            if current_user:
                return {"authenticated": True, "user_id": current_user.id}
            else:
                return {"authenticated": False}

        return app

    def test_protected_endpoint_without_token(self, test_app):
        """Test protected endpoint without authentication token."""
        client = TestClient(test_app)
        response = client.get("/protected")
        assert response.status_code == 403

    def test_protected_endpoint_with_invalid_token(self, test_app):
        """Test protected endpoint with invalid token."""
        client = TestClient(test_app)
        headers = {"Authorization": "Bearer invalid_token"}
        
        with patch("app.api.deps.get_clerk_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.verify_jwt_token.side_effect = AuthenticationError("Invalid token")
            mock_get_service.return_value = mock_service
            
            response = client.get("/protected", headers=headers)
            assert response.status_code == 401

    def test_optional_auth_endpoint_without_token(self, test_app):
        """Test optional auth endpoint without token."""
        client = TestClient(test_app)
        response = client.get("/optional-auth")
        assert response.status_code == 200
        assert response.json() == {"authenticated": False}

    @patch("app.api.deps.get_clerk_service")
    @patch("app.api.deps.UserSyncService")
    def test_complete_authentication_flow(
        self, mock_sync_service_class, mock_get_service, test_app
    ):
        """Test complete authentication flow with valid token."""
        # Setup mocks
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        
        mock_sync_service = AsyncMock()
        mock_sync_service_class.return_value = mock_sync_service
        
        # Mock token verification
        token_data = {"clerk_id": "user_clerk_123"}
        mock_service.verify_jwt_token.return_value = token_data
        
        # Mock user data
        clerk_user = Mock()
        mock_service.get_user_by_clerk_id.return_value = clerk_user
        
        # Mock sync response
        mock_sync_service.sync_user_data.return_value = ClerkUserSyncResponse(
            success=True,
            action="updated",
            message="Success"
        )
        
        # Mock local user
        local_user = Mock(spec=User)
        local_user.id = "user_123"
        local_user.clerk_id = "user_clerk_123"
        local_user.role = UserRole.VETERINARIAN
        local_user.is_active = True
        mock_sync_service.get_user_by_clerk_id.return_value = local_user
        
        # Test request
        client = TestClient(test_app)
        headers = {"Authorization": "Bearer valid_token"}
        response = client.get("/protected", headers=headers)
        
        assert response.status_code == 200
        assert response.json() == {"user_id": "user_123", "role": "veterinarian"}