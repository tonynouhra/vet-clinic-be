"""
Integration tests for V1 User endpoints.

Tests complete controller-service flow for V1 user endpoints.
Tests authentication, authorization, and error scenarios.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.models.user import User, UserRole
from app.core.database import get_db
from app.app_helpers.auth_helpers import get_current_user, require_role


# Test fixtures
@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Async test client for FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def admin_user():
    """Admin user for testing."""
    return User(
        id=uuid.uuid4(),
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        is_active=True,
        is_verified=True,
        clerk_id="admin_clerk_123",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def regular_user():
    """Regular user for testing."""
    return User(
        id=uuid.uuid4(),
        email="user@example.com",
        first_name="Regular",
        last_name="User",
        is_active=True,
        is_verified=True,
        clerk_id="user_clerk_123",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_user_data():
    """Sample user data for creation."""
    return {
        "email": "newuser@example.com",
        "first_name": "New",
        "last_name": "User",
        "phone_number": "1234567890",
        "role": "pet_owner"
    }


class TestV1UserEndpointsListUsers:
    """Test V1 user list endpoint."""
    
    @pytest.mark.asyncio
    async def test_list_users_success(self, async_client, admin_user, regular_user):
        """Test successful user listing with admin privileges."""
        # Mock dependencies
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.list_users') as mock_list_users:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: admin_user
                    mock_list_users.return_value = ([regular_user], 1)
                    
                    # Make request
                    response = await async_client.get("/api/v1/users/")
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["version"] == "v1"
                    assert len(data["data"]) == 1
                    assert data["pagination"]["total"] == 1
                    assert data["data"][0]["email"] == regular_user.email
    
    @pytest.mark.asyncio
    async def test_list_users_unauthorized(self, async_client, regular_user):
        """Test user listing without admin privileges."""
        # Mock dependencies to simulate non-admin user
        with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
            # Setup mock to raise HTTPException for unauthorized access
            from fastapi import HTTPException
            mock_require_role.side_effect = HTTPException(status_code=403, detail="Insufficient permissions")
            
            # Make request
            response = await async_client.get("/api/v1/users/")
            
            # Assertions
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_list_users_with_pagination(self, async_client, admin_user, regular_user):
        """Test user listing with pagination parameters."""
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.list_users') as mock_list_users:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: admin_user
                    mock_list_users.return_value = ([regular_user], 10)
                    
                    # Make request with pagination
                    response = await async_client.get("/api/v1/users/?page=2&per_page=5")
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["pagination"]["page"] == 2
                    assert data["pagination"]["per_page"] == 5
                    assert data["pagination"]["total"] == 10
    
    @pytest.mark.asyncio
    async def test_list_users_with_filters(self, async_client, admin_user, regular_user):
        """Test user listing with search and role filters."""
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.list_users') as mock_list_users:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: admin_user
                    mock_list_users.return_value = ([regular_user], 1)
                    
                    # Make request with filters
                    response = await async_client.get(
                        "/api/v1/users/?search=regular&role=pet_owner&is_active=true"
                    )
                    
                    # Assertions
                    assert response.status_code == 200
                    # Verify controller was called with correct parameters
                    mock_list_users.assert_called_once()
                    call_kwargs = mock_list_users.call_args[1]
                    assert call_kwargs["search"] == "regular"
                    assert call_kwargs["role"] == UserRole.PET_OWNER
                    assert call_kwargs["is_active"] is True
                    assert call_kwargs["include_roles"] is False  # V1 doesn't include roles


class TestV1UserEndpointsCreateUser:
    """Test V1 user creation endpoint."""
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, async_client, admin_user, sample_user_data):
        """Test successful user creation with admin privileges."""
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.create_user') as mock_create_user:
                    # Create expected user response
                    created_user = User(
                        id=uuid.uuid4(),
                        email=sample_user_data["email"],
                        first_name=sample_user_data["first_name"],
                        last_name=sample_user_data["last_name"],
                        phone_number=sample_user_data["phone_number"],
                        is_active=True,
                        is_verified=False,
                        clerk_id="new_clerk_123",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: admin_user
                    mock_create_user.return_value = created_user
                    
                    # Make request
                    response = await async_client.post("/api/v1/users/", json=sample_user_data)
                    
                    # Assertions
                    assert response.status_code == 201
                    data = response.json()
                    assert data["success"] is True
                    assert data["version"] == "v1"
                    assert data["data"]["email"] == sample_user_data["email"]
                    assert data["data"]["first_name"] == sample_user_data["first_name"]
    
    @pytest.mark.asyncio
    async def test_create_user_validation_error(self, async_client, admin_user):
        """Test user creation with validation errors."""
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                # Setup mocks
                mock_get_db.return_value = AsyncMock()
                mock_require_role.return_value = lambda: admin_user
                
                # Make request with invalid data
                invalid_data = {
                    "email": "invalid-email",  # Invalid email format
                    "first_name": "Test",
                    "last_name": "User"
                }
                
                response = await async_client.post("/api/v1/users/", json=invalid_data)
                
                # Assertions
                assert response.status_code == 422  # Pydantic validation error
    
    @pytest.mark.asyncio
    async def test_create_user_unauthorized(self, async_client, regular_user):
        """Test user creation without admin privileges."""
        with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
            # Setup mock to raise HTTPException for unauthorized access
            from fastapi import HTTPException
            mock_require_role.side_effect = HTTPException(status_code=403, detail="Insufficient permissions")
            
            # Make request
            response = await async_client.post("/api/v1/users/", json={"email": "test@example.com"})
            
            # Assertions
            assert response.status_code == 403


class TestV1UserEndpointsGetUser:
    """Test V1 get user endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_user_success_own_profile(self, async_client, regular_user):
        """Test successful user retrieval of own profile."""
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.get_current_user') as mock_get_current_user:
                with patch('app.users.controller.UserController.get_user_by_id') as mock_get_user:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_get_current_user.return_value = regular_user
                    mock_get_user.return_value = regular_user
                    
                    # Make request
                    response = await async_client.get(f"/api/v1/users/{regular_user.id}")
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["version"] == "v1"
                    assert data["data"]["id"] == str(regular_user.id)
                    assert data["data"]["email"] == regular_user.email
    
    @pytest.mark.asyncio
    async def test_get_user_success_admin_access(self, async_client, admin_user, regular_user):
        """Test successful user retrieval by admin."""
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.get_current_user') as mock_get_current_user:
                with patch('app.users.controller.UserController.get_user_by_id') as mock_get_user:
                    # Mock admin accessing another user's profile
                    admin_user.is_clinic_admin = lambda: True
                    
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_get_current_user.return_value = admin_user
                    mock_get_user.return_value = regular_user
                    
                    # Make request
                    response = await async_client.get(f"/api/v1/users/{regular_user.id}")
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["data"]["id"] == str(regular_user.id)
    
    @pytest.mark.asyncio
    async def test_get_user_unauthorized_access(self, async_client, regular_user):
        """Test unauthorized user profile access."""
        other_user_id = uuid.uuid4()
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.get_current_user') as mock_get_current_user:
                # Mock user trying to access another user's profile
                regular_user.is_clinic_admin = lambda: False
                
                # Setup mocks
                mock_get_db.return_value = AsyncMock()
                mock_get_current_user.return_value = regular_user
                
                # Make request
                response = await async_client.get(f"/api/v1/users/{other_user_id}")
                
                # Assertions
                assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(self, async_client, admin_user):
        """Test user retrieval when user not found."""
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.get_current_user') as mock_get_current_user:
                with patch('app.users.controller.UserController.get_user_by_id') as mock_get_user:
                    from fastapi import HTTPException
                    
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_get_current_user.return_value = admin_user
                    mock_get_user.side_effect = HTTPException(status_code=404, detail="User not found")
                    
                    # Make request
                    response = await async_client.get(f"/api/v1/users/{uuid.uuid4()}")
                    
                    # Assertions
                    assert response.status_code == 404


class TestV1UserEndpointsUpdateUser:
    """Test V1 user update endpoint."""
    
    @pytest.mark.asyncio
    async def test_update_user_success_own_profile(self, async_client, regular_user):
        """Test successful user update of own profile."""
        update_data = {
            "first_name": "Updated",
            "last_name": "Name"
        }
        
        updated_user = User(**{
            **regular_user.__dict__,
            "first_name": "Updated",
            "last_name": "Name"
        })
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.get_current_user') as mock_get_current_user:
                with patch('app.users.controller.UserController.update_user') as mock_update_user:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_get_current_user.return_value = regular_user
                    mock_update_user.return_value = updated_user
                    
                    # Make request
                    response = await async_client.put(f"/api/v1/users/{regular_user.id}", json=update_data)
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["version"] == "v1"
                    assert data["data"]["first_name"] == "Updated"
                    assert data["data"]["last_name"] == "Name"
    
    @pytest.mark.asyncio
    async def test_update_user_unauthorized(self, async_client, regular_user):
        """Test unauthorized user update."""
        other_user_id = uuid.uuid4()
        update_data = {"first_name": "Hacker"}
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.get_current_user') as mock_get_current_user:
                # Mock user trying to update another user's profile
                regular_user.is_clinic_admin = lambda: False
                
                # Setup mocks
                mock_get_db.return_value = AsyncMock()
                mock_get_current_user.return_value = regular_user
                
                # Make request
                response = await async_client.put(f"/api/v1/users/{other_user_id}", json=update_data)
                
                # Assertions
                assert response.status_code == 403


class TestV1UserEndpointsDeleteUser:
    """Test V1 user deletion endpoint."""
    
    @pytest.mark.asyncio
    async def test_delete_user_success_system_admin(self, async_client):
        """Test successful user deletion by system admin."""
        system_admin = User(
            id=uuid.uuid4(),
            email="sysadmin@example.com",
            first_name="System",
            last_name="Admin",
            is_active=True,
            is_verified=True,
            clerk_id="sysadmin_clerk_123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        user_to_delete_id = uuid.uuid4()
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.delete_user') as mock_delete_user:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: system_admin
                    mock_delete_user.return_value = {"success": True, "message": "User deleted successfully"}
                    
                    # Make request
                    response = await async_client.delete(f"/api/v1/users/{user_to_delete_id}")
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["message"] == "User deleted successfully"
                    assert data["user_id"] == str(user_to_delete_id)
    
    @pytest.mark.asyncio
    async def test_delete_user_insufficient_permissions(self, async_client, admin_user):
        """Test user deletion with insufficient permissions (needs system admin)."""
        with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
            # Setup mock to raise HTTPException for insufficient permissions
            from fastapi import HTTPException
            mock_require_role.side_effect = HTTPException(status_code=403, detail="Insufficient permissions")
            
            # Make request
            response = await async_client.delete(f"/api/v1/users/{uuid.uuid4()}")
            
            # Assertions
            assert response.status_code == 403


class TestV1UserEndpointsActivation:
    """Test V1 user activation/deactivation endpoints."""
    
    @pytest.mark.asyncio
    async def test_activate_user_success(self, async_client, admin_user, regular_user):
        """Test successful user activation."""
        activated_user = User(**{
            **regular_user.__dict__,
            "is_active": True
        })
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.activate_user') as mock_activate_user:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: admin_user
                    mock_activate_user.return_value = activated_user
                    
                    # Make request
                    response = await async_client.post(f"/api/v1/users/{regular_user.id}/activate")
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["version"] == "v1"
                    assert data["data"]["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_deactivate_user_success(self, async_client, admin_user, regular_user):
        """Test successful user deactivation."""
        deactivated_user = User(**{
            **regular_user.__dict__,
            "is_active": False
        })
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.deactivate_user') as mock_deactivate_user:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: admin_user
                    mock_deactivate_user.return_value = deactivated_user
                    
                    # Make request
                    response = await async_client.post(f"/api/v1/users/{regular_user.id}/deactivate")
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["data"]["is_active"] is False


class TestV1UserEndpointsRoleManagement:
    """Test V1 user role management endpoints."""
    
    @pytest.mark.asyncio
    async def test_assign_role_success(self, async_client, regular_user):
        """Test successful role assignment."""
        system_admin = User(
            id=uuid.uuid4(),
            email="sysadmin@example.com",
            first_name="System",
            last_name="Admin",
            is_active=True,
            is_verified=True,
            clerk_id="sysadmin_clerk_123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        role_data = {"role": "veterinarian"}
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.assign_role') as mock_assign_role:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: system_admin
                    mock_assign_role.return_value = {
                        "success": True,
                        "message": "Role veterinarian assigned successfully"
                    }
                    
                    # Make request
                    response = await async_client.post(
                        f"/api/v1/users/{regular_user.id}/roles",
                        json=role_data
                    )
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert "assigned successfully" in data["message"]
                    assert data["user_id"] == str(regular_user.id)
    
    @pytest.mark.asyncio
    async def test_remove_role_success(self, async_client, regular_user):
        """Test successful role removal."""
        system_admin = User(
            id=uuid.uuid4(),
            email="sysadmin@example.com",
            first_name="System",
            last_name="Admin",
            is_active=True,
            is_verified=True,
            clerk_id="sysadmin_clerk_123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.remove_role') as mock_remove_role:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: system_admin
                    mock_remove_role.return_value = {
                        "success": True,
                        "message": "Role veterinarian removed successfully"
                    }
                    
                    # Make request
                    response = await async_client.delete(
                        f"/api/v1/users/{regular_user.id}/roles/veterinarian"
                    )
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert "removed successfully" in data["message"]
                    assert data["user_id"] == str(regular_user.id)