"""
Simplified unit tests for UserSyncService core functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from app.services.user_sync_service import UserSyncService
from app.models.user import UserRole
from app.schemas.clerk_schemas import (
    ClerkUser,
    ClerkEmailAddress,
    ClerkPhoneNumber,
    ClerkUserSyncResponse,
    ClerkRoleMapping
)


class TestUserSyncServiceCore:
    """Test core functionality of UserSyncService."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def user_sync_service(self, mock_db_session):
        """UserSyncService instance with mocked dependencies."""
        return UserSyncService(mock_db_session)

    @pytest.fixture
    def sample_clerk_user(self):
        """Sample ClerkUser for testing."""
        return ClerkUser(
            id="clerk_123",
            email_addresses=[
                ClerkEmailAddress(
                    id="email_1",
                    email_address="test@example.com"
                )
            ],
            phone_numbers=[
                ClerkPhoneNumber(
                    id="phone_1",
                    phone_number="+1234567890"
                )
            ],
            first_name="John",
            last_name="Doe",
            image_url="https://example.com/avatar.jpg",
            public_metadata={"role": "pet_owner"},
            private_metadata={"preferences": {"theme": "dark"}},
            created_at=int(datetime.utcnow().timestamp() * 1000),
            updated_at=int(datetime.utcnow().timestamp() * 1000),
            last_sign_in_at=int(datetime.utcnow().timestamp() * 1000),
            banned=False,
            locked=False
        )

    @pytest.fixture
    def sample_user(self):
        """Sample User mock for testing."""
        user = MagicMock()
        user.id = "user_123"
        user.clerk_id = "clerk_123"
        user.email = "test@example.com"
        user.first_name = "John"
        user.last_name = "Doe"
        user.phone_number = "+1234567890"
        user.role = UserRole.PET_OWNER
        user.is_active = True
        user.is_verified = True
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        user.avatar_url = None
        user.preferences = {}
        user.notification_settings = {}
        user.has_permission = MagicMock(return_value=True)
        return user

    def test_role_mapping_configuration(self, user_sync_service):
        """Test role mapping configuration."""
        role_mapping = user_sync_service.role_mapping
        
        # Test default mappings
        assert role_mapping.get_internal_role("admin") == UserRole.ADMIN
        assert role_mapping.get_internal_role("veterinarian") == UserRole.VETERINARIAN
        assert role_mapping.get_internal_role("pet_owner") == UserRole.PET_OWNER
        
        # Test default role for unknown mapping
        assert role_mapping.get_internal_role("unknown_role") == UserRole.PET_OWNER
        assert role_mapping.get_internal_role(None) == UserRole.PET_OWNER

    def test_should_update_user_basic_fields_changed(self, user_sync_service, sample_user, sample_clerk_user):
        """Test _should_update_user when basic fields have changed."""
        # Change first name
        sample_clerk_user.first_name = "Changed"
        
        result = user_sync_service._should_update_user(sample_user, sample_clerk_user)
        
        assert result == True

    def test_should_update_user_role_changed(self, user_sync_service, sample_user, sample_clerk_user):
        """Test _should_update_user when role has changed."""
        # Change role in metadata
        sample_clerk_user.public_metadata = {"role": "veterinarian"}
        
        result = user_sync_service._should_update_user(sample_user, sample_clerk_user)
        
        assert result == True

    def test_should_update_user_status_changed(self, user_sync_service, sample_user, sample_clerk_user):
        """Test _should_update_user when status has changed."""
        # Ban user in Clerk
        sample_clerk_user.banned = True
        
        result = user_sync_service._should_update_user(sample_user, sample_clerk_user)
        
        assert result == True

    def test_should_update_user_clerk_data_newer(self, user_sync_service, sample_user, sample_clerk_user):
        """Test _should_update_user when Clerk data is newer."""
        # Set user updated_at to be older than Clerk data
        sample_user.updated_at = datetime.utcnow() - timedelta(hours=1)
        
        result = user_sync_service._should_update_user(sample_user, sample_clerk_user)
        
        assert result == True

    def test_should_update_user_no_changes(self, user_sync_service, sample_user, sample_clerk_user):
        """Test _should_update_user when no changes are needed."""
        # Set user updated_at to be newer than Clerk data
        sample_user.updated_at = datetime.utcnow() + timedelta(hours=1)
        # Ensure all fields match
        sample_user.email = sample_clerk_user.primary_email
        sample_user.first_name = sample_clerk_user.first_name
        sample_user.last_name = sample_clerk_user.last_name
        sample_user.phone_number = sample_clerk_user.primary_phone
        sample_user.avatar_url = sample_clerk_user.image_url
        sample_user.is_active = not sample_clerk_user.banned and not sample_clerk_user.locked
        
        result = user_sync_service._should_update_user(sample_user, sample_clerk_user)
        
        assert result == False

    async def test_validate_user_permissions(self, user_sync_service, sample_user):
        """Test user permission validation."""
        result = await user_sync_service.validate_user_permissions(sample_user, "pets:read")
        
        # Should return True for pet owner with pets:read permission
        assert result == True
        sample_user.has_permission.assert_called_once_with("pets:read")

    async def test_validate_user_permissions_exception(self, user_sync_service, sample_user):
        """Test user permission validation with exception."""
        sample_user.has_permission.side_effect = Exception("Permission error")
        
        result = await user_sync_service.validate_user_permissions(sample_user, "pets:read")
        
        # Should return False when exception occurs
        assert result == False

    @patch('app.services.user_sync_service.ClerkUserValidation.validate_user_data')
    async def test_create_user_validation_error(self, mock_validate, user_sync_service, sample_clerk_user, mock_db_session):
        """Test user creation with validation errors."""
        # Mock validation to return errors
        mock_validate.return_value = ["Invalid email", "Missing name"]
        
        with pytest.raises(HTTPException) as exc_info:
            await user_sync_service.create_user_from_clerk(sample_clerk_user)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid Clerk user data" in str(exc_info.value.detail)
        mock_db_session.rollback.assert_called_once()

    @patch('app.services.user_sync_service.ClerkUserValidation.validate_user_data')
    async def test_update_user_validation_error(self, mock_validate, user_sync_service, sample_clerk_user, sample_user, mock_db_session):
        """Test user update with validation errors."""
        # Mock validation to return errors
        mock_validate.return_value = ["Invalid phone number"]
        
        with pytest.raises(HTTPException) as exc_info:
            await user_sync_service.update_user_from_clerk(sample_user, sample_clerk_user)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid Clerk user data" in str(exc_info.value.detail)
        mock_db_session.rollback.assert_called_once()

    async def test_sync_user_data_http_exception_handling(self, user_sync_service, sample_clerk_user):
        """Test sync_user_data handling HTTPException."""
        # Mock get_user_by_clerk_id to raise HTTPException
        with patch.object(user_sync_service, 'get_user_by_clerk_id', side_effect=HTTPException(status_code=404, detail="Not found")):
            result = await user_sync_service.sync_user_data(sample_clerk_user)
        
        assert isinstance(result, ClerkUserSyncResponse)
        assert result.success == False
        assert result.action == "failed"
        assert "Not found" in result.message

    async def test_sync_user_data_general_exception_handling(self, user_sync_service, sample_clerk_user):
        """Test sync_user_data handling general exceptions."""
        # Mock get_user_by_clerk_id to raise general exception
        with patch.object(user_sync_service, 'get_user_by_clerk_id', side_effect=Exception("Database error")):
            result = await user_sync_service.sync_user_data(sample_clerk_user)
        
        assert isinstance(result, ClerkUserSyncResponse)
        assert result.success == False
        assert result.action == "failed"
        assert result.message == "User synchronization failed"
        assert "Database error" in result.errors

    def test_clerk_user_transform_create_data(self, user_sync_service, sample_clerk_user):
        """Test ClerkUserTransform.to_user_create_data."""
        from app.schemas.clerk_schemas import ClerkUserTransform
        
        result = ClerkUserTransform.to_user_create_data(sample_clerk_user, user_sync_service.role_mapping)
        
        assert result["clerk_id"] == "clerk_123"
        assert result["email"] == "test@example.com"
        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"
        assert result["phone_number"] == "+1234567890"
        assert result["role"] == UserRole.PET_OWNER
        assert result["avatar_url"] == "https://example.com/avatar.jpg"
        assert result["is_active"] == True
        assert result["is_verified"] == True

    def test_clerk_user_transform_update_data(self, user_sync_service, sample_clerk_user):
        """Test ClerkUserTransform.to_user_update_data."""
        from app.schemas.clerk_schemas import ClerkUserTransform
        
        result = ClerkUserTransform.to_user_update_data(sample_clerk_user, user_sync_service.role_mapping)
        
        assert result["email"] == "test@example.com"
        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"
        assert result["phone_number"] == "+1234567890"
        assert result["role"] == UserRole.PET_OWNER
        assert result["avatar_url"] == "https://example.com/avatar.jpg"
        assert result["is_active"] == True

    def test_clerk_user_validation_valid_data(self, sample_clerk_user):
        """Test ClerkUserValidation with valid data."""
        from app.schemas.clerk_schemas import ClerkUserValidation
        
        errors = ClerkUserValidation.validate_user_data(sample_clerk_user)
        
        assert len(errors) == 0

    def test_clerk_user_validation_invalid_data(self):
        """Test ClerkUserValidation with invalid data."""
        from app.schemas.clerk_schemas import ClerkUserValidation
        
        invalid_user = ClerkUser(
            id="",  # Empty ID
            email_addresses=[],  # No email
            first_name=None,  # No first name
            last_name=None,  # No last name
            created_at=0,  # Invalid timestamp
            updated_at=0  # Invalid timestamp
        )
        
        errors = ClerkUserValidation.validate_user_data(invalid_user)
        
        assert len(errors) > 0
        assert any("Clerk user ID is required" in error for error in errors)
        assert any("Primary email address is required" in error for error in errors)
        assert any("First name is required" in error for error in errors)
        assert any("Last name is required" in error for error in errors)

    def test_clerk_role_mapping_valid_roles(self):
        """Test ClerkRoleMapping with valid roles."""
        mapping = ClerkRoleMapping()
        
        assert mapping.get_internal_role("admin") == UserRole.ADMIN
        assert mapping.get_internal_role("veterinarian") == UserRole.VETERINARIAN
        assert mapping.get_internal_role("receptionist") == UserRole.RECEPTIONIST
        assert mapping.get_internal_role("clinic_manager") == UserRole.CLINIC_MANAGER
        assert mapping.get_internal_role("pet_owner") == UserRole.PET_OWNER
        assert mapping.get_internal_role("staff") == UserRole.RECEPTIONIST

    def test_clerk_role_mapping_invalid_roles(self):
        """Test ClerkRoleMapping with invalid roles."""
        mapping = ClerkRoleMapping()
        
        assert mapping.get_internal_role("invalid_role") == UserRole.PET_OWNER
        assert mapping.get_internal_role("") == UserRole.PET_OWNER
        assert mapping.get_internal_role(None) == UserRole.PET_OWNER

    def test_clerk_user_sync_response_creation(self):
        """Test ClerkUserSyncResponse creation."""
        response = ClerkUserSyncResponse(
            success=True,
            user_id="user_123",
            action="created",
            message="User created successfully"
        )
        
        assert response.success == True
        assert response.user_id == "user_123"
        assert response.action == "created"
        assert response.message == "User created successfully"
        assert response.errors == []

    def test_clerk_user_sync_response_with_errors(self):
        """Test ClerkUserSyncResponse with errors."""
        response = ClerkUserSyncResponse(
            success=False,
            action="failed",
            message="Validation failed",
            errors=["Invalid email", "Missing name"]
        )
        
        assert response.success == False
        assert response.user_id is None
        assert response.action == "failed"
        assert response.message == "Validation failed"
        assert len(response.errors) == 2
        assert "Invalid email" in response.errors
        assert "Missing name" in response.errors