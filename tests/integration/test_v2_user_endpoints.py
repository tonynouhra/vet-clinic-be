"""
Integration tests for V2 User endpoints.

Tests complete controller-service flow for V2 user endpoints.
Tests enhanced V2 features like role information, profile updates, statistics, and batch operations.
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
def admin_user():
    """Admin user for testing."""
    return User(
        id=uuid.uuid4(),
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        bio="System administrator",
        is_active=True,
        is_verified=True,
        clerk_id="admin_clerk_123",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def regular_user():
    """Regular user for testing with V2 fields."""
    return User(
        id=uuid.uuid4(),
        email="user@example.com",
        first_name="Regular",
        last_name="User",
        bio="Pet owner and veterinary client",
        profile_image_url="https://example.com/profile.jpg",
        is_active=True,
        is_verified=True,
        clerk_id="user_clerk_123",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_user_data_v2():
    """Sample V2 user data for creation."""
    return {
        "email": "newuser@example.com",
        "first_name": "New",
        "last_name": "User",
        "phone_number": "1234567890",
        "bio": "New user biography",
        "profile_image_url": "https://example.com/newuser.jpg",
        "department": "cardiology",
        "role": "pet_owner",
        "preferences": {
            "theme": "dark",
            "notifications": True,
            "language": "en"
        }
    }


class TestV2UserEndpointsListUsers:
    """Test V2 user list endpoint with enhanced features."""
    
    @pytest.mark.asyncio
    async def test_list_users_success_with_enhanced_features(self, async_client, admin_user, regular_user):
        """Test successful user listing with V2 enhanced features."""
        # Mock dependencies
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.list_users') as mock_list_users:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: admin_user
                    mock_list_users.return_value = ([regular_user], 1)
                    
                    # Make request with V2 features
                    response = await async_client.get(
                        "/api/v2/users/?include_roles=true&include_relationships=true&department=cardiology"
                    )
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["version"] == "v2"
                    assert len(data["data"]) == 1
                    
                    # Verify controller was called with V2 parameters
                    mock_list_users.assert_called_once()
                    call_kwargs = mock_list_users.call_args[1]
                    assert call_kwargs["include_roles"] is True
                    assert call_kwargs["include_relationships"] is True
                    assert call_kwargs["department"] == "cardiology"
    
    @pytest.mark.asyncio
    async def test_list_users_enhanced_filtering(self, async_client, admin_user, regular_user):
        """Test V2 enhanced filtering capabilities."""
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.list_users') as mock_list_users:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: admin_user
                    mock_list_users.return_value = ([regular_user], 1)
                    
                    # Make request with V2 filters
                    response = await async_client.get(
                        "/api/v2/users/?search=regular&role=pet_owner&department=cardiology&include_roles=true"
                    )
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["version"] == "v2"
                    
                    # Verify V2-specific parameters were passed
                    call_kwargs = mock_list_users.call_args[1]
                    assert call_kwargs["department"] == "cardiology"
                    assert call_kwargs["include_roles"] is True


class TestV2UserEndpointsCreateUser:
    """Test V2 user creation endpoint with enhanced fields."""
    
    @pytest.mark.asyncio
    async def test_create_user_success_with_v2_fields(self, async_client, admin_user, sample_user_data_v2):
        """Test successful user creation with V2 enhanced fields."""
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.create_user') as mock_create_user:
                    # Create expected user response with V2 fields
                    created_user = User(
                        id=uuid.uuid4(),
                        email=sample_user_data_v2["email"],
                        first_name=sample_user_data_v2["first_name"],
                        last_name=sample_user_data_v2["last_name"],
                        phone_number=sample_user_data_v2["phone_number"],
                        bio=sample_user_data_v2["bio"],
                        profile_image_url=sample_user_data_v2["profile_image_url"],
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
                    response = await async_client.post("/api/v2/users/", json=sample_user_data_v2)
                    
                    # Assertions
                    assert response.status_code == 201
                    data = response.json()
                    assert data["success"] is True
                    assert data["version"] == "v2"
                    assert data["data"]["email"] == sample_user_data_v2["email"]
                    assert data["data"]["bio"] == sample_user_data_v2["bio"]
                    assert data["data"]["profile_image_url"] == sample_user_data_v2["profile_image_url"]
                    
                    # Verify controller was called with V2 fields
                    mock_create_user.assert_called_once()
                    call_args = mock_create_user.call_args[1]
                    assert "bio" in call_args
                    assert "department" in call_args
                    assert "preferences" in call_args


class TestV2UserEndpointsGetUser:
    """Test V2 get user endpoint with enhanced information."""
    
    @pytest.mark.asyncio
    async def test_get_user_success_with_v2_features(self, async_client, regular_user):
        """Test successful user retrieval with V2 enhanced information."""
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.get_current_user') as mock_get_current_user:
                with patch('app.users.controller.UserController.get_user_by_id') as mock_get_user:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_get_current_user.return_value = regular_user
                    mock_get_user.return_value = regular_user
                    
                    # Make request with V2 parameters
                    response = await async_client.get(
                        f"/api/v2/users/{regular_user.id}?include_roles=true&include_relationships=true"
                    )
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["version"] == "v2"
                    assert data["data"]["id"] == str(regular_user.id)
                    assert data["data"]["bio"] == regular_user.bio
                    assert data["data"]["profile_image_url"] == regular_user.profile_image_url
                    
                    # Verify controller was called with V2 parameters
                    mock_get_user.assert_called_once()
                    call_kwargs = mock_get_user.call_args[1]
                    assert call_kwargs["include_roles"] is True
                    assert call_kwargs["include_relationships"] is True


class TestV2UserEndpointsUpdateUser:
    """Test V2 user update endpoint with enhanced fields."""
    
    @pytest.mark.asyncio
    async def test_update_user_success_with_v2_fields(self, async_client, regular_user):
        """Test successful user update with V2 enhanced fields."""
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "bio": "Updated biography",
            "department": "neurology",
            "preferences": {
                "theme": "light",
                "notifications": False
            }
        }
        
        updated_user = User(**{
            **regular_user.__dict__,
            "first_name": "Updated",
            "last_name": "Name",
            "bio": "Updated biography"
        })
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.get_current_user') as mock_get_current_user:
                with patch('app.users.controller.UserController.update_user') as mock_update_user:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_get_current_user.return_value = regular_user
                    mock_update_user.return_value = updated_user
                    
                    # Make request
                    response = await async_client.put(f"/api/v2/users/{regular_user.id}", json=update_data)
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["version"] == "v2"
                    assert data["data"]["first_name"] == "Updated"
                    assert data["data"]["bio"] == "Updated biography"
                    
                    # Verify controller was called with V2 fields
                    mock_update_user.assert_called_once()
                    call_kwargs = mock_update_user.call_args[1]
                    assert "bio" in call_kwargs
                    assert "department" in call_kwargs
                    assert "preferences" in call_kwargs


class TestV2UserEndpointsProfileUpdate:
    """Test V2 specific profile update endpoint."""
    
    @pytest.mark.asyncio
    async def test_update_user_profile_success(self, async_client, regular_user):
        """Test successful profile update using V2 specific endpoint."""
        profile_data = {
            "bio": "Updated profile biography",
            "profile_image_url": "https://example.com/updated-profile.jpg",
            "preferences": {
                "theme": "dark",
                "language": "es",
                "notifications": True
            }
        }
        
        updated_user = User(**{
            **regular_user.__dict__,
            "bio": "Updated profile biography",
            "profile_image_url": "https://example.com/updated-profile.jpg"
        })
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.get_current_user') as mock_get_current_user:
                with patch('app.users.controller.UserController.update_user') as mock_update_user:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_get_current_user.return_value = regular_user
                    mock_update_user.return_value = updated_user
                    
                    # Make request to V2-specific profile endpoint
                    response = await async_client.patch(
                        f"/api/v2/users/{regular_user.id}/profile",
                        json=profile_data
                    )
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["version"] == "v2"
                    assert data["data"]["bio"] == "Updated profile biography"
                    assert data["data"]["profile_image_url"] == "https://example.com/updated-profile.jpg"
    
    @pytest.mark.asyncio
    async def test_update_user_profile_unauthorized(self, async_client, regular_user):
        """Test unauthorized profile update (can only update own profile)."""
        other_user_id = uuid.uuid4()
        profile_data = {"bio": "Hacker bio"}
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.get_current_user') as mock_get_current_user:
                # Setup mocks
                mock_get_db.return_value = AsyncMock()
                mock_get_current_user.return_value = regular_user
                
                # Make request
                response = await async_client.patch(
                    f"/api/v2/users/{other_user_id}/profile",
                    json=profile_data
                )
                
                # Assertions
                assert response.status_code == 403


class TestV2UserEndpointsRoleManagement:
    """Test V2 enhanced role management endpoints."""
    
    @pytest.mark.asyncio
    async def test_assign_role_with_v2_metadata(self, async_client, regular_user):
        """Test role assignment with V2 enhanced metadata."""
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
        
        role_data = {
            "role": "veterinarian",
            "department": "cardiology",
            "notes": "Specialized in cardiac procedures"
        }
        
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
                        f"/api/v2/users/{regular_user.id}/roles",
                        json=role_data
                    )
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert "assigned successfully" in data["message"]
                    assert data["user_id"] == str(regular_user.id)
                    assert data["affected_roles"] == [UserRole.VETERINARIAN]
                    assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_assign_multiple_roles_batch(self, async_client, regular_user):
        """Test V2 batch role assignment endpoint."""
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
        
        batch_role_data = {
            "roles": [
                {
                    "role": "veterinarian",
                    "department": "cardiology",
                    "notes": "Cardiac specialist"
                },
                {
                    "role": "clinic_admin",
                    "department": "administration",
                    "notes": "Administrative duties"
                }
            ]
        }
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.assign_role') as mock_assign_role:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: system_admin
                    mock_assign_role.return_value = None  # Called multiple times
                    
                    # Make request to V2 batch endpoint
                    response = await async_client.post(
                        f"/api/v2/users/{regular_user.id}/roles/batch",
                        json=batch_role_data
                    )
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert "2 roles" in data["message"]
                    assert len(data["affected_roles"]) == 2
                    assert UserRole.VETERINARIAN in data["affected_roles"]
                    assert UserRole.CLINIC_ADMIN in data["affected_roles"]
                    
                    # Verify assign_role was called twice
                    assert mock_assign_role.call_count == 2


class TestV2UserEndpointsStatistics:
    """Test V2 user statistics endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_user_stats_success(self, async_client, regular_user):
        """Test successful user statistics retrieval."""
        # Mock user with relationships for stats calculation
        user_with_relationships = User(**{
            **regular_user.__dict__,
            "pets": [{"id": 1}, {"id": 2}],  # Mock pets
            "appointments": [{"id": 1}, {"id": 2}, {"id": 3}]  # Mock appointments
        })
        user_with_relationships.pets = [{"id": 1}, {"id": 2}]
        user_with_relationships.appointments = [{"id": 1}, {"id": 2}, {"id": 3}]
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.get_current_user') as mock_get_current_user:
                with patch('app.users.controller.UserController.get_user_by_id') as mock_get_user:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_get_current_user.return_value = regular_user
                    mock_get_user.return_value = user_with_relationships
                    
                    # Make request to V2 stats endpoint
                    response = await async_client.get(f"/api/v2/users/{regular_user.id}/stats")
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["version"] == "v2"
                    assert "total_pets" in data["data"]
                    assert "total_appointments" in data["data"]
                    assert "account_age_days" in data["data"]
                    assert "registration_date" in data["data"]
    
    @pytest.mark.asyncio
    async def test_get_user_stats_unauthorized(self, async_client, regular_user):
        """Test unauthorized access to user stats."""
        other_user_id = uuid.uuid4()
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.get_current_user') as mock_get_current_user:
                # Mock user trying to access another user's stats
                regular_user.is_clinic_admin = lambda: False
                
                # Setup mocks
                mock_get_db.return_value = AsyncMock()
                mock_get_current_user.return_value = regular_user
                
                # Make request
                response = await async_client.get(f"/api/v2/users/{other_user_id}/stats")
                
                # Assertions
                assert response.status_code == 403


class TestV2UserEndpointsBatchOperations:
    """Test V2 batch operation endpoints."""
    
    @pytest.mark.asyncio
    async def test_batch_create_users_success(self, async_client):
        """Test successful batch user creation."""
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
        
        batch_data = {
            "users": [
                {
                    "email": "user1@example.com",
                    "first_name": "User",
                    "last_name": "One",
                    "bio": "First batch user"
                },
                {
                    "email": "user2@example.com",
                    "first_name": "User",
                    "last_name": "Two",
                    "bio": "Second batch user"
                }
            ],
            "default_role": "pet_owner",
            "send_invitations": True
        }
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.create_user') as mock_create_user:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: system_admin
                    
                    # Mock successful user creation
                    created_users = [
                        User(id=uuid.uuid4(), email="user1@example.com", first_name="User", last_name="One"),
                        User(id=uuid.uuid4(), email="user2@example.com", first_name="User", last_name="Two")
                    ]
                    mock_create_user.side_effect = created_users
                    
                    # Make request to V2 batch endpoint
                    response = await async_client.post("/api/v2/users/batch", json=batch_data)
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["total_requested"] == 2
                    assert data["successful"] == 2
                    assert data["failed"] == 0
                    assert len(data["processed_ids"]) == 2
                    assert len(data["errors"]) == 0
                    
                    # Verify create_user was called twice
                    assert mock_create_user.call_count == 2
    
    @pytest.mark.asyncio
    async def test_batch_create_users_partial_failure(self, async_client):
        """Test batch user creation with partial failures."""
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
        
        batch_data = {
            "users": [
                {
                    "email": "user1@example.com",
                    "first_name": "User",
                    "last_name": "One"
                },
                {
                    "email": "invalid-email",  # This will fail
                    "first_name": "User",
                    "last_name": "Two"
                }
            ],
            "default_role": "pet_owner"
        }
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.create_user') as mock_create_user:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: system_admin
                    
                    # Mock first success, second failure
                    created_user = User(id=uuid.uuid4(), email="user1@example.com", first_name="User", last_name="One")
                    mock_create_user.side_effect = [
                        created_user,
                        Exception("Invalid email format")
                    ]
                    
                    # Make request
                    response = await async_client.post("/api/v2/users/batch", json=batch_data)
                    
                    # Assertions
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is False  # Overall failure due to partial failure
                    assert data["total_requested"] == 2
                    assert data["successful"] == 1
                    assert data["failed"] == 1
                    assert len(data["processed_ids"]) == 1
                    assert len(data["errors"]) == 1
                    assert data["errors"][0]["index"] == 1
                    assert data["errors"][0]["email"] == "invalid-email"