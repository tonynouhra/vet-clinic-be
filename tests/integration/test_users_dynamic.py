"""
Dynamic User CRUD Tests - Version-Agnostic API Testing.

Tests user CRUD operations across all API versions using the dynamic testing framework.
Automatically adapts to version-specific features, fields, and behaviors.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from fastapi import status

from app.models.user import User, UserRole
from tests.dynamic.base_test import BaseVersionTest
from tests.dynamic.decorators import version_parametrize, feature_test
from tests.dynamic.data_factory import TestDataFactory
from tests.dynamic.fixtures import api_version, version_config, base_url


class TestUsersDynamic(BaseVersionTest):
    """Dynamic user CRUD tests across all API versions."""

    @pytest.fixture
    def test_data_factory(self):
        """Test data factory fixture."""
        return TestDataFactory()

    @pytest.fixture
    def admin_user(self):
        """Mock admin user for privileged operations."""
        return User(
            id=uuid.uuid4(),
            clerk_id="admin_clerk_123",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_verified=True
        )

    @pytest.fixture
    def regular_user(self):
        """Mock regular user for testing."""
        return User(
            id=uuid.uuid4(),
            clerk_id="user_clerk_123",
            email="user@example.com",
            first_name="Regular",
            last_name="User",
            is_active=True,
            is_verified=True
        )

    @pytest.fixture
    def system_admin(self):
        """Mock system admin user for highest privilege operations."""
        return User(
            id=uuid.uuid4(),
            clerk_id="sysadmin_clerk_123",
            email="sysadmin@example.com",
            first_name="System",
            last_name="Admin",
            is_active=True,
            is_verified=True
        )

    def create_mock_user(self, api_version: str, test_data_factory: TestDataFactory) -> User:
        """Create a mock user object with version-appropriate data."""
        user_data = test_data_factory.build_user_data(api_version)
        
        # Create base user object
        user = User(
            id=uuid.uuid4(),
            clerk_id="test_clerk_123",
            email=user_data["email"],
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            phone_number=user_data.get("phone_number"),
            is_active=True,
            is_verified=False
        )
        
        # Add version-specific fields
        if api_version == "v2":
            user.bio = user_data.get("bio", "Test user biography")
            user.profile_image_url = user_data.get("profile_image_url", "https://example.com/profile.jpg")
        
        return user

    # User Creation Tests
    @version_parametrize()
    async def test_create_user_success(self, api_version: str, async_client: AsyncClient,
                                     test_data_factory: TestDataFactory, admin_user):
        """Test successful user creation across all versions."""
        # Generate version-appropriate test data
        user_data = test_data_factory.build_user_data(api_version)
        mock_user = self.create_mock_user(api_version, test_data_factory)
        
        # Get endpoint URL for this version
        endpoint_url = self.get_endpoint_url(api_version, "users")
        
        with patch("app.users.controller.UserController.create_user", new_callable=AsyncMock) as mock_create_user, \
             patch("app.app_helpers.auth_helpers.require_role", return_value=lambda: admin_user), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            mock_create_user.return_value = mock_user
            
            response = await self.make_request("POST", endpoint_url, async_client, json=user_data)
            
            # Assert successful creation
            self.assert_status_code(response, 201, f"Creating user in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Validate version-specific response fields
            user_response = data["data"]
            self.validate_response_structure(user_response, api_version, "user", "response")
            
            # Verify required fields are present
            assert user_response["email"] == user_data["email"]
            assert user_response["first_name"] == user_data["first_name"]
            assert user_response["last_name"] == user_data["last_name"]
            
            # Verify version-specific fields
            if api_version == "v2":
                if "bio" in user_data:
                    assert "bio" in user_response or user_response.get("bio") is not None
                if "profile_image_url" in user_data:
                    assert "profile_image_url" in user_response
                if "address" in user_data:
                    assert "address" in user_response
                if "emergency_contact" in user_data:
                    assert "emergency_contact" in user_response
            else:
                # v1 should not have v2-specific fields
                assert "bio" not in user_response
                assert "profile_image_url" not in user_response
                assert "address" not in user_response
                assert "emergency_contact" not in user_response
            
            # Verify controller was called correctly
            mock_create_user.assert_called_once()

    @version_parametrize()
    async def test_create_user_validation_error(self, api_version: str, async_client: AsyncClient,
                                              admin_user):
        """Test user creation with validation errors across all versions."""
        endpoint_url = self.get_endpoint_url(api_version, "users")
        
        with patch("app.app_helpers.auth_helpers.require_role", return_value=lambda: admin_user), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            # Test with invalid email format
            invalid_data = {
                "email": "invalid-email",  # Invalid email format
                "first_name": "Test",
                "last_name": "User"
            }
            
            response = await self.make_request("POST", endpoint_url, async_client, json=invalid_data)
            
            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @version_parametrize()
    async def test_create_user_unauthorized(self, api_version: str, async_client: AsyncClient,
                                          test_data_factory: TestDataFactory, regular_user):
        """Test user creation without admin privileges across all versions."""
        user_data = test_data_factory.build_user_data(api_version)
        endpoint_url = self.get_endpoint_url(api_version, "users")
        
        with patch("app.app_helpers.auth_helpers.require_role") as mock_require_role:
            # Setup mock to raise HTTPException for unauthorized access
            from fastapi import HTTPException
            mock_require_role.side_effect = HTTPException(status_code=403, detail="Insufficient permissions")
            
            response = await self.make_request("POST", endpoint_url, async_client, json=user_data)
            
            # Should return forbidden status
            self.assert_status_code(response, 403, f"Unauthorized user creation in {api_version}")

    # User Retrieval Tests
    @version_parametrize()
    async def test_get_user_by_id_success_own_profile(self, api_version: str, async_client: AsyncClient,
                                                    test_data_factory: TestDataFactory, regular_user):
        """Test successful user retrieval of own profile across all versions."""
        endpoint_url = self.get_endpoint_url(api_version, "users", str(regular_user.id))
        
        with patch("app.users.controller.UserController.get_user_by_id", new_callable=AsyncMock) as mock_get_user, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=regular_user), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            mock_get_user.return_value = regular_user
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Assert successful retrieval
            self.assert_status_code(response, 200, f"Getting own user profile in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Validate version-specific response fields
            user_response = data["data"]
            self.validate_response_structure(user_response, api_version, "user", "response")
            self.validate_version_specific_fields(user_response, api_version, "user")
            
            # Verify user data
            assert user_response["id"] == str(regular_user.id)
            assert user_response["email"] == regular_user.email
            assert user_response["first_name"] == regular_user.first_name
            
            # Verify controller was called correctly
            mock_get_user.assert_called_once()

    @version_parametrize()
    async def test_get_user_by_id_success_admin_access(self, api_version: str, async_client: AsyncClient,
                                                     test_data_factory: TestDataFactory, admin_user, regular_user):
        """Test successful user retrieval by admin across all versions."""
        endpoint_url = self.get_endpoint_url(api_version, "users", str(regular_user.id))
        
        with patch("app.users.controller.UserController.get_user_by_id", new_callable=AsyncMock) as mock_get_user, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=admin_user), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            # Mock admin accessing another user's profile
            admin_user.is_clinic_admin = lambda: True
            mock_get_user.return_value = regular_user
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Assert successful retrieval
            self.assert_status_code(response, 200, f"Admin getting user profile in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert data["data"]["id"] == str(regular_user.id)

    @version_parametrize()
    async def test_get_user_unauthorized_access(self, api_version: str, async_client: AsyncClient,
                                              regular_user):
        """Test unauthorized user profile access across all versions."""
        other_user_id = uuid.uuid4()
        endpoint_url = self.get_endpoint_url(api_version, "users", str(other_user_id))
        
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=regular_user), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            # Mock user trying to access another user's profile
            regular_user.is_clinic_admin = lambda: False
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Should return forbidden status
            self.assert_status_code(response, 403, f"Unauthorized user access in {api_version}")

    @version_parametrize()
    async def test_get_user_not_found(self, api_version: str, async_client: AsyncClient, admin_user):
        """Test user retrieval when user not found across all versions."""
        non_existent_id = uuid.uuid4()
        endpoint_url = self.get_endpoint_url(api_version, "users", str(non_existent_id))
        
        with patch("app.users.controller.UserController.get_user_by_id", new_callable=AsyncMock) as mock_get_user, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=admin_user), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            from fastapi import HTTPException
            mock_get_user.side_effect = HTTPException(status_code=404, detail="User not found")
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Should return 404
            self.assert_status_code(response, 404, f"Getting non-existent user in {api_version}")

    # User Listing Tests
    @version_parametrize()
    async def test_list_users_success(self, api_version: str, async_client: AsyncClient,
                                    test_data_factory: TestDataFactory, admin_user, regular_user):
        """Test successful user listing across all versions."""
        endpoint_url = self.get_endpoint_url(api_version, "users")
        
        with patch("app.users.controller.UserController.list_users", new_callable=AsyncMock) as mock_list_users, \
             patch("app.app_helpers.auth_helpers.require_role", return_value=lambda: admin_user), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            mock_list_users.return_value = ([regular_user], 1)
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Assert successful listing
            self.assert_status_code(response, 200, f"Listing users in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Verify pagination data
            if isinstance(data["data"], list):
                # Some versions might return direct list
                assert len(data["data"]) == 1
            else:
                # Others might return paginated structure
                assert len(data["data"]) == 1
                assert data["pagination"]["total"] == 1
            
            # Verify controller was called with version-appropriate defaults
            mock_list_users.assert_called_once()
            call_kwargs = mock_list_users.call_args[1]
            
            if api_version == "v1":
                assert call_kwargs.get("include_roles", True) is False
            elif api_version == "v2":
                # v2 might have different defaults
                pass

    @version_parametrize()
    async def test_list_users_with_filters(self, api_version: str, async_client: AsyncClient,
                                         test_data_factory: TestDataFactory, admin_user, regular_user):
        """Test user listing with filters across all versions."""
        endpoint_url = self.get_endpoint_url(api_version, "users")
        
        with patch("app.users.controller.UserController.list_users", new_callable=AsyncMock) as mock_list_users, \
             patch("app.app_helpers.auth_helpers.require_role", return_value=lambda: admin_user), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            mock_list_users.return_value = ([regular_user], 1)
            
            # Test with common filters available in all versions
            query_params = "?search=regular&role=pet_owner&is_active=true&page=2&per_page=5"
            response = await self.make_request("GET", f"{endpoint_url}{query_params}", async_client)
            
            # Assert successful listing with filters
            self.assert_status_code(response, 200, f"Listing users with filters in {api_version}")
            
            # Verify controller was called with correct filters
            mock_list_users.assert_called_once()
            call_kwargs = mock_list_users.call_args[1]
            assert call_kwargs["search"] == "regular"
            assert call_kwargs["role"] == UserRole.PET_OWNER
            assert call_kwargs["is_active"] is True
            assert call_kwargs["page"] == 2
            assert call_kwargs["per_page"] == 5

    @version_parametrize()
    async def test_list_users_unauthorized(self, api_version: str, async_client: AsyncClient, regular_user):
        """Test user listing without admin privileges across all versions."""
        endpoint_url = self.get_endpoint_url(api_version, "users")
        
        with patch("app.app_helpers.auth_helpers.require_role") as mock_require_role:
            # Setup mock to raise HTTPException for unauthorized access
            from fastapi import HTTPException
            mock_require_role.side_effect = HTTPException(status_code=403, detail="Insufficient permissions")
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Should return forbidden status
            self.assert_status_code(response, 403, f"Unauthorized user listing in {api_version}")

    # User Update Tests
    @version_parametrize()
    async def test_update_user_success_own_profile(self, api_version: str, async_client: AsyncClient,
                                                 test_data_factory: TestDataFactory, regular_user):
        """Test successful user update of own profile across all versions."""
        endpoint_url = self.get_endpoint_url(api_version, "users", str(regular_user.id))
        
        # Generate version-appropriate update data
        update_data = test_data_factory.build_update_data(api_version, "user",
                                                        first_name="Updated",
                                                        last_name="Name")
        
        with patch("app.users.controller.UserController.update_user", new_callable=AsyncMock) as mock_update_user, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=regular_user), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            # Update mock user with new data
            updated_user = User(**{
                **regular_user.__dict__,
                "first_name": "Updated",
                "last_name": "Name"
            })
            mock_update_user.return_value = updated_user
            
            response = await self.make_request("PUT", endpoint_url, async_client, json=update_data)
            
            # Assert successful update
            self.assert_status_code(response, 200, f"Updating own user profile in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Validate updated user response
            user_response = data["data"]
            self.validate_response_structure(user_response, api_version, "user", "response")
            
            # Verify updated fields
            assert user_response["first_name"] == "Updated"
            assert user_response["last_name"] == "Name"
            
            # Verify controller was called correctly
            mock_update_user.assert_called_once()

    @version_parametrize()
    async def test_update_user_unauthorized(self, api_version: str, async_client: AsyncClient,
                                          test_data_factory: TestDataFactory, regular_user):
        """Test unauthorized user update across all versions."""
        other_user_id = uuid.uuid4()
        endpoint_url = self.get_endpoint_url(api_version, "users", str(other_user_id))
        
        update_data = test_data_factory.build_update_data(api_version, "user", first_name="Hacker")
        
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=regular_user), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            # Mock user trying to update another user's profile
            regular_user.is_clinic_admin = lambda: False
            
            response = await self.make_request("PUT", endpoint_url, async_client, json=update_data)
            
            # Should return forbidden status
            self.assert_status_code(response, 403, f"Unauthorized user update in {api_version}")

    # User Deletion Tests
    @version_parametrize()
    async def test_delete_user_success(self, api_version: str, async_client: AsyncClient,
                                     test_data_factory: TestDataFactory, system_admin):
        """Test successful user deletion across all versions."""
        user_to_delete_id = uuid.uuid4()
        endpoint_url = self.get_endpoint_url(api_version, "users", str(user_to_delete_id))
        
        with patch("app.users.controller.UserController.delete_user", new_callable=AsyncMock) as mock_delete_user, \
             patch("app.app_helpers.auth_helpers.require_role", return_value=lambda: system_admin), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            mock_delete_user.return_value = {"success": True, "message": "User deleted successfully"}
            
            response = await self.make_request("DELETE", endpoint_url, async_client)
            
            # Assert successful deletion
            self.assert_status_code(response, 200, f"Deleting user in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            if api_version == "v1":
                assert data["message"] == "User deleted successfully"
                assert data["user_id"] == str(user_to_delete_id)
            else:
                # v2 might have different response structure
                assert "message" in data or "data" in data
            
            # Verify controller was called correctly
            mock_delete_user.assert_called_once()

    @version_parametrize()
    async def test_delete_user_insufficient_permissions(self, api_version: str, async_client: AsyncClient,
                                                      admin_user):
        """Test user deletion with insufficient permissions across all versions."""
        user_to_delete_id = uuid.uuid4()
        endpoint_url = self.get_endpoint_url(api_version, "users", str(user_to_delete_id))
        
        with patch("app.app_helpers.auth_helpers.require_role") as mock_require_role:
            # Setup mock to raise HTTPException for insufficient permissions
            from fastapi import HTTPException
            mock_require_role.side_effect = HTTPException(status_code=403, detail="Insufficient permissions")
            
            response = await self.make_request("DELETE", endpoint_url, async_client)
            
            # Should return forbidden status
            self.assert_status_code(response, 403, f"Insufficient permissions for user deletion in {api_version}")

    # User Activation/Deactivation Tests
    @version_parametrize()
    async def test_activate_user_success(self, api_version: str, async_client: AsyncClient,
                                       test_data_factory: TestDataFactory, admin_user, regular_user):
        """Test successful user activation across all versions."""
        endpoint_url = self.get_endpoint_url(api_version, "users", str(regular_user.id)) + "/activate"
        
        with patch("app.users.controller.UserController.activate_user", new_callable=AsyncMock) as mock_activate_user, \
             patch("app.app_helpers.auth_helpers.require_role", return_value=lambda: admin_user), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            activated_user = User(**{
                **regular_user.__dict__,
                "is_active": True
            })
            mock_activate_user.return_value = activated_user
            
            response = await self.make_request("POST", endpoint_url, async_client)
            
            # Assert successful activation
            self.assert_status_code(response, 200, f"Activating user in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            assert data["data"]["is_active"] is True
            
            # Verify controller was called correctly
            mock_activate_user.assert_called_once()

    @version_parametrize()
    async def test_deactivate_user_success(self, api_version: str, async_client: AsyncClient,
                                         test_data_factory: TestDataFactory, admin_user, regular_user):
        """Test successful user deactivation across all versions."""
        endpoint_url = self.get_endpoint_url(api_version, "users", str(regular_user.id)) + "/deactivate"
        
        with patch("app.users.controller.UserController.deactivate_user", new_callable=AsyncMock) as mock_deactivate_user, \
             patch("app.app_helpers.auth_helpers.require_role", return_value=lambda: admin_user), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            deactivated_user = User(**{
                **regular_user.__dict__,
                "is_active": False
            })
            mock_deactivate_user.return_value = deactivated_user
            
            response = await self.make_request("POST", endpoint_url, async_client)
            
            # Assert successful deactivation
            self.assert_status_code(response, 200, f"Deactivating user in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["data"]["is_active"] is False
            
            # Verify controller was called correctly
            mock_deactivate_user.assert_called_once()

    # Role Management Tests
    @version_parametrize()
    async def test_assign_role_success(self, api_version: str, async_client: AsyncClient,
                                     test_data_factory: TestDataFactory, system_admin, regular_user):
        """Test successful role assignment across all versions."""
        endpoint_url = self.get_endpoint_url(api_version, "users", str(regular_user.id)) + "/roles"
        
        role_data = {"role": "veterinarian"}
        
        with patch("app.users.controller.UserController.assign_role", new_callable=AsyncMock) as mock_assign_role, \
             patch("app.app_helpers.auth_helpers.require_role", return_value=lambda: system_admin), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            mock_assign_role.return_value = {
                "success": True,
                "message": "Role veterinarian assigned successfully"
            }
            
            response = await self.make_request("POST", endpoint_url, async_client, json=role_data)
            
            # Assert successful role assignment
            self.assert_status_code(response, 200, f"Assigning role in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert "assigned successfully" in data["message"]
            assert data["user_id"] == str(regular_user.id)
            
            # Version-specific response fields
            if api_version == "v2":
                assert "affected_roles" in data
                assert "timestamp" in data
            
            # Verify controller was called correctly
            mock_assign_role.assert_called_once()

    @version_parametrize()
    async def test_remove_role_success(self, api_version: str, async_client: AsyncClient,
                                     test_data_factory: TestDataFactory, system_admin, regular_user):
        """Test successful role removal across all versions."""
        endpoint_url = self.get_endpoint_url(api_version, "users", str(regular_user.id)) + "/roles/veterinarian"
        
        with patch("app.users.controller.UserController.remove_role", new_callable=AsyncMock) as mock_remove_role, \
             patch("app.app_helpers.auth_helpers.require_role", return_value=lambda: system_admin), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            mock_remove_role.return_value = {
                "success": True,
                "message": "Role veterinarian removed successfully"
            }
            
            response = await self.make_request("DELETE", endpoint_url, async_client)
            
            # Assert successful role removal
            self.assert_status_code(response, 200, f"Removing role in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert "removed successfully" in data["message"]
            assert data["user_id"] == str(regular_user.id)
            
            # Verify controller was called correctly
            mock_remove_role.assert_called_once()

    # Version-Specific Feature Tests
    @feature_test("enhanced_filtering")
    async def test_list_users_with_enhanced_filters(self, api_version: str, async_client: AsyncClient,
                                                   test_data_factory: TestDataFactory, admin_user, regular_user):
        """Test user listing with enhanced filters (v2+ only)."""
        endpoint_url = self.get_endpoint_url(api_version, "users")
        
        with patch("app.users.controller.UserController.list_users", new_callable=AsyncMock) as mock_list_users, \
             patch("app.app_helpers.auth_helpers.require_role", return_value=lambda: admin_user), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            mock_list_users.return_value = ([regular_user], 1)
            
            # Test with enhanced filters only available in v2+
            query_params = "?include_roles=true&include_relationships=true&department=cardiology"
            response = await self.make_request("GET", f"{endpoint_url}{query_params}", async_client)
            
            # Assert successful listing with enhanced filters
            self.assert_status_code(response, 200, f"Listing users with enhanced filters in {api_version}")
            
            # Verify controller was called with enhanced parameters
            mock_list_users.assert_called_once()
            call_kwargs = mock_list_users.call_args[1]
            assert call_kwargs.get("include_roles") is True
            assert call_kwargs.get("include_relationships") is True
            assert call_kwargs.get("department") == "cardiology"

    @feature_test("statistics")
    async def test_get_user_statistics(self, api_version: str, async_client: AsyncClient,
                                     test_data_factory: TestDataFactory, regular_user):
        """Test user statistics endpoint (v2+ only)."""
        endpoint_url = self.get_endpoint_url(api_version, "users", str(regular_user.id)) + "/stats"
        
        with patch("app.users.controller.UserController.get_user_by_id", new_callable=AsyncMock) as mock_get_user, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=regular_user), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            # Mock user with relationships for stats calculation
            user_with_relationships = regular_user
            user_with_relationships.pets = [{"id": 1}, {"id": 2}]
            user_with_relationships.appointments = [{"id": 1}, {"id": 2}, {"id": 3}]
            mock_get_user.return_value = user_with_relationships
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Assert successful statistics retrieval
            self.assert_status_code(response, 200, f"Getting user statistics in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Verify statistics data
            stats_data = data["data"]
            assert "total_pets" in stats_data
            assert "total_appointments" in stats_data
            assert "account_age_days" in stats_data
            assert "registration_date" in stats_data

    @feature_test("batch_operations")
    async def test_batch_create_users(self, api_version: str, async_client: AsyncClient,
                                    test_data_factory: TestDataFactory, system_admin):
        """Test batch user creation (v2+ only)."""
        endpoint_url = self.get_endpoint_url(api_version, "users") + "/batch"
        
        batch_data = {
            "users": [
                {
                    "email": "user1@example.com",
                    "first_name": "User",
                    "last_name": "One"
                },
                {
                    "email": "user2@example.com",
                    "first_name": "User",
                    "last_name": "Two"
                }
            ],
            "default_role": "pet_owner",
            "send_invitations": True
        }
        
        with patch("app.users.controller.UserController.create_user", new_callable=AsyncMock) as mock_create_user, \
             patch("app.app_helpers.auth_helpers.require_role", return_value=lambda: system_admin), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            # Mock successful user creation
            created_users = [
                User(id=uuid.uuid4(), email="user1@example.com", first_name="User", last_name="One"),
                User(id=uuid.uuid4(), email="user2@example.com", first_name="User", last_name="Two")
            ]
            mock_create_user.side_effect = created_users
            
            response = await self.make_request("POST", endpoint_url, async_client, json=batch_data)
            
            # Assert successful batch creation
            self.assert_status_code(response, 200, f"Batch creating users in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["total_requested"] == 2
            assert data["successful"] == 2
            assert data["failed"] == 0
            assert len(data["processed_ids"]) == 2
            assert len(data["errors"]) == 0
            
            # Verify create_user was called twice
            assert mock_create_user.call_count == 2

    # Comprehensive CRUD Test
    @version_parametrize()
    async def test_complete_user_crud_workflow(self, api_version: str, async_client: AsyncClient,
                                             test_data_factory: TestDataFactory, admin_user, system_admin):
        """Test complete CRUD workflow for users across all versions."""
        # 1. Create user
        user_data = test_data_factory.build_user_data(api_version)
        mock_user = self.create_mock_user(api_version, test_data_factory)
        
        create_url = self.get_endpoint_url(api_version, "users")
        
        with patch("app.users.controller.UserController.create_user", new_callable=AsyncMock) as mock_create, \
             patch("app.users.controller.UserController.get_user_by_id", new_callable=AsyncMock) as mock_get, \
             patch("app.users.controller.UserController.update_user", new_callable=AsyncMock) as mock_update, \
             patch("app.users.controller.UserController.delete_user", new_callable=AsyncMock) as mock_delete, \
             patch("app.app_helpers.auth_helpers.require_role", return_value=lambda: admin_user), \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=admin_user), \
             patch("app.core.database.get_db", return_value=AsyncMock()):
            
            mock_create.return_value = mock_user
            mock_get.return_value = mock_user
            mock_update.return_value = mock_user
            mock_delete.return_value = {"success": True, "message": "User deleted successfully"}
            
            # Create
            create_response = await self.make_request("POST", create_url, async_client, json=user_data)
            self.assert_status_code(create_response, 201, f"CRUD Create in {api_version}")
            created_user = create_response.json()["data"]
            user_id = created_user["id"]
            
            # Read
            read_url = self.get_endpoint_url(api_version, "users", user_id)
            read_response = await self.make_request("GET", read_url, async_client)
            self.assert_status_code(read_response, 200, f"CRUD Read in {api_version}")
            
            # Update
            update_data = test_data_factory.build_update_data(api_version, "user", first_name="Updated Name")
            update_response = await self.make_request("PUT", read_url, async_client, json=update_data)
            self.assert_status_code(update_response, 200, f"CRUD Update in {api_version}")
            
            # Delete (requires system admin user)
            with patch("app.app_helpers.auth_helpers.require_role", return_value=lambda: system_admin), \
                 patch("app.app_helpers.auth_helpers.get_current_user", return_value=system_admin):
                delete_response = await self.make_request("DELETE", read_url, async_client)
                self.assert_status_code(delete_response, 200, f"CRUD Delete in {api_version}")
            
            # Verify all operations were called
            mock_create.assert_called_once()
            mock_get.assert_called_once()
            mock_update.assert_called_once()
            mock_delete.assert_called_once()