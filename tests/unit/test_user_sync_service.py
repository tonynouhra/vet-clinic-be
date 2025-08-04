"""
Unit tests for UserSyncService.
Tests all synchronization scenarios including creation, updates, and deletion.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
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


class TestUserSyncService:
    """Test cases for UserSyncService."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        session.execute = AsyncMock()
        return session

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
        """Sample User model for testing."""
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

    @patch('app.services.user_sync_service.User')
    async def test_create_user_from_clerk_success(self, mock_user_class, user_sync_service, sample_clerk_user, mock_db_session):
        """Test successful user creation from Clerk data."""
        # Mock database queries to return None (user doesn't exist)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Mock the created user instance
        mock_user_instance = MagicMock()
        mock_user_instance.id = "new_user_123"
        mock_user_instance.email = "test@example.com"
        mock_user_class.return_value = mock_user_instance

        result = await user_sync_service.create_user_from_clerk(sample_clerk_user)

        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

        # Verify user creation
        mock_user_class.assert_called_once()
        call_kwargs = mock_user_class.call_args[1]
        assert call_kwargs["clerk_id"] == "clerk_123"
        assert call_kwargs["email"] == "test@example.com"
        assert call_kwargs["first_name"] == "John"
        assert call_kwargs["last_name"] == "Doe"
        assert call_kwargs["role"] == UserRole.PET_OWNER

    async def test_create_user_from_clerk_validation_error(self, user_sync_service, mock_db_session):
        """Test user creation with invalid Clerk data."""
        # Create invalid Clerk user (missing required fields)
        invalid_clerk_user = ClerkUser(
            id="",  # Empty ID should cause validation error
            email_addresses=[],
            phone_numbers=[],
            first_name=None,
            last_name=None,
            created_at=int(datetime.utcnow().timestamp() * 1000),
            updated_at=int(datetime.utcnow().timestamp() * 1000)
        )

        with pytest.raises(HTTPException) as exc_info:
            await user_sync_service.create_user_from_clerk(invalid_clerk_user)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid Clerk user data" in str(exc_info.value.detail)
        mock_db_session.rollback.assert_called_once()

    async def test_create_user_from_clerk_user_exists(self, user_sync_service, sample_clerk_user, sample_user, mock_db_session):
        """Test user creation when user already exists."""
        # Mock database to return existing user
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await user_sync_service.create_user_from_clerk(sample_clerk_user)

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "User already exists" in str(exc_info.value.detail)
        mock_db_session.rollback.assert_called_once()

    async def test_update_user_from_clerk_success(self, user_sync_service, sample_clerk_user, sample_user, mock_db_session):
        """Test successful user update from Clerk data."""
        # Update Clerk user data
        sample_clerk_user.first_name = "Jane"
        sample_clerk_user.last_name = "Smith"
        sample_clerk_user.public_metadata = {"role": "veterinarian"}

        # Mock database queries for email check
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await user_sync_service.update_user_from_clerk(sample_user, sample_clerk_user)

        # Verify database operations
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

        # Verify user was updated
        assert sample_user.first_name == "Jane"
        assert sample_user.last_name == "Smith"
        assert sample_user.role == UserRole.VETERINARIAN

    async def test_update_user_from_clerk_email_conflict(self, user_sync_service, sample_clerk_user, sample_user, mock_db_session):
        """Test user update with email conflict."""
        # Change email in Clerk data
        sample_clerk_user.email_addresses = [
            ClerkEmailAddress(id="email_2", email_address="newemail@example.com")
        ]

        # Mock database to return another user with the same email
        conflicting_user = MagicMock()
        conflicting_user.id = "other_user"
        conflicting_user.email = "newemail@example.com"
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = conflicting_user
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await user_sync_service.update_user_from_clerk(sample_user, sample_clerk_user)

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "Email already in use" in str(exc_info.value.detail)
        mock_db_session.rollback.assert_called_once()

    async def test_handle_user_deletion_success(self, user_sync_service, sample_user, mock_db_session):
        """Test successful user deletion handling."""
        # Mock database to return the user
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        await user_sync_service.handle_user_deletion("clerk_123")

        # Verify user was soft deleted
        assert sample_user.is_active == False
        assert sample_user.is_verified == False
        assert sample_user.phone_number is None
        assert sample_user.avatar_url is None
        assert sample_user.preferences == {}
        assert sample_user.email.startswith("deleted_")
        assert sample_user.first_name == "Deleted"
        assert sample_user.last_name == "User"

        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    async def test_handle_user_deletion_user_not_found(self, user_sync_service, mock_db_session):
        """Test user deletion when user doesn't exist."""
        # Mock database to return None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Should not raise exception, just log warning
        await user_sync_service.handle_user_deletion("nonexistent_clerk_id")

        # Should not attempt database operations
        mock_db_session.commit.assert_not_called()

    async def test_sync_user_data_create_new_user(self, user_sync_service, sample_clerk_user, mock_db_session):
        """Test sync_user_data creating a new user."""
        # Mock database queries to return None (user doesn't exist)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await user_sync_service.sync_user_data(sample_clerk_user)

        assert isinstance(result, ClerkUserSyncResponse)
        assert result.success == True
        assert result.action == "created"
        assert "created successfully" in result.message

    async def test_sync_user_data_update_existing_user(self, user_sync_service, sample_clerk_user, sample_user, mock_db_session):
        """Test sync_user_data updating an existing user."""
        # Mock database to return existing user for first query, None for email check
        mock_results = [
            AsyncMock(),  # First query - get user by clerk_id
            AsyncMock(),  # Second query - check email availability
        ]
        mock_results[0].scalar_one_or_none.return_value = sample_user
        mock_results[1].scalar_one_or_none.return_value = None
        mock_db_session.execute.side_effect = mock_results

        # Modify Clerk user to trigger update
        sample_clerk_user.first_name = "Updated"

        result = await user_sync_service.sync_user_data(sample_clerk_user)

        assert isinstance(result, ClerkUserSyncResponse)
        assert result.success == True
        assert result.action == "updated"
        assert "updated successfully" in result.message

    async def test_sync_user_data_skip_update(self, user_sync_service, sample_clerk_user, sample_user, mock_db_session):
        """Test sync_user_data skipping update when data is current."""
        # Mock database to return existing user
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        # Set user updated_at to be newer than Clerk data
        sample_user.updated_at = datetime.utcnow() + timedelta(hours=1)

        result = await user_sync_service.sync_user_data(sample_clerk_user)

        assert isinstance(result, ClerkUserSyncResponse)
        assert result.success == True
        assert result.action == "skipped"
        assert "up to date" in result.message

    async def test_sync_user_data_force_update(self, user_sync_service, sample_clerk_user, sample_user, mock_db_session):
        """Test sync_user_data with force_update=True."""
        # Mock database to return existing user for first query, None for email check
        mock_results = [
            AsyncMock(),  # First query - get user by clerk_id
            AsyncMock(),  # Second query - check email availability
        ]
        mock_results[0].scalar_one_or_none.return_value = sample_user
        mock_results[1].scalar_one_or_none.return_value = None
        mock_db_session.execute.side_effect = mock_results

        # Set user updated_at to be newer than Clerk data
        sample_user.updated_at = datetime.utcnow() + timedelta(hours=1)

        result = await user_sync_service.sync_user_data(sample_clerk_user, force_update=True)

        assert isinstance(result, ClerkUserSyncResponse)
        assert result.success == True
        assert result.action == "updated"

    async def test_get_user_by_clerk_id_success(self, user_sync_service, sample_user, mock_db_session):
        """Test getting user by Clerk ID."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        result = await user_sync_service.get_user_by_clerk_id("clerk_123")

        assert result == sample_user

    async def test_get_user_by_clerk_id_not_found(self, user_sync_service, mock_db_session):
        """Test getting user by Clerk ID when not found."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await user_sync_service.get_user_by_clerk_id("nonexistent")

        assert result is None

    async def test_get_user_by_email_success(self, user_sync_service, sample_user, mock_db_session):
        """Test getting user by email."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        result = await user_sync_service.get_user_by_email("test@example.com")

        assert result == sample_user

    async def test_get_users_by_role(self, user_sync_service, mock_db_session):
        """Test getting users by role."""
        user1 = MagicMock(spec=User)
        user1.id = "user1"
        user1.role = UserRole.VETERINARIAN
        
        user2 = MagicMock(spec=User)
        user2.id = "user2"
        user2.role = UserRole.VETERINARIAN
        
        users = [user1, user2]
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = users
        mock_db_session.execute.return_value = mock_result

        result = await user_sync_service.get_users_by_role(UserRole.VETERINARIAN)

        assert len(result) == 2
        assert all(user.role == UserRole.VETERINARIAN for user in result)

    async def test_cleanup_inactive_users(self, user_sync_service, mock_db_session):
        """Test cleanup of inactive users."""
        # Create inactive users
        user1 = MagicMock(spec=User)
        user1.id = "user1"
        user1.email = "deleted_user1@deleted.local"
        user1.is_active = False
        user1.updated_at = datetime.utcnow() - timedelta(days=100)
        user1.preferences = {"old": "data"}
        user1.notification_settings = {"old": "settings"}
        
        user2 = MagicMock(spec=User)
        user2.id = "user2"
        user2.email = "deleted_user2@deleted.local"
        user2.is_active = False
        user2.updated_at = datetime.utcnow() - timedelta(days=100)
        user2.preferences = {"old": "data"}
        user2.notification_settings = {"old": "settings"}
        
        inactive_users = [user1, user2]

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = inactive_users
        mock_db_session.execute.return_value = mock_result

        result = await user_sync_service.cleanup_inactive_users(days_inactive=90)

        assert result == 2
        mock_db_session.commit.assert_called_once()

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

    def test_should_update_user_no_changes(self, user_sync_service, sample_user, sample_clerk_user):
        """Test _should_update_user when no changes are needed."""
        # Set user updated_at to be newer than Clerk data
        sample_user.updated_at = datetime.utcnow() + timedelta(hours=1)
        
        result = user_sync_service._should_update_user(sample_user, sample_clerk_user)
        
        assert result == False

    async def test_validate_user_permissions(self, user_sync_service, sample_user):
        """Test user permission validation."""
        result = await user_sync_service.validate_user_permissions(sample_user, "pets:read")
        
        # Should return True for pet owner with pets:read permission
        assert result == True

    async def test_get_sync_statistics(self, user_sync_service, mock_db_session):
        """Test getting synchronization statistics."""
        # Mock database queries for statistics
        mock_results = []
        
        # Mock results for each role query
        for role in UserRole:
            mock_user = MagicMock(spec=User)
            mock_user.role = role
            mock_result = AsyncMock()
            mock_result.scalars.return_value.all.return_value = [mock_user]
            mock_results.append(mock_result)
        
        # Mock results for active/inactive counts
        active_user1 = MagicMock(spec=User)
        active_user2 = MagicMock(spec=User)
        active_result = AsyncMock()
        active_result.scalars.return_value.all.return_value = [active_user1, active_user2]
        mock_results.append(active_result)
        
        inactive_user = MagicMock(spec=User)
        inactive_result = AsyncMock()
        inactive_result.scalars.return_value.all.return_value = [inactive_user]
        mock_results.append(inactive_result)
        
        mock_db_session.execute.side_effect = mock_results

        result = await user_sync_service.get_sync_statistics()

        assert "total_users" in result
        assert "active_users" in result
        assert "inactive_users" in result
        assert "users_by_role" in result
        assert "last_updated" in result
        assert result["total_users"] == 3  # 2 active + 1 inactive
        assert result["active_users"] == 2
        assert result["inactive_users"] == 1

    async def test_role_mapping_configuration(self, user_sync_service):
        """Test role mapping configuration."""
        role_mapping = user_sync_service.role_mapping
        
        # Test default mappings
        assert role_mapping.get_internal_role("admin") == UserRole.ADMIN
        assert role_mapping.get_internal_role("veterinarian") == UserRole.VETERINARIAN
        assert role_mapping.get_internal_role("pet_owner") == UserRole.PET_OWNER
        
        # Test default role for unknown mapping
        assert role_mapping.get_internal_role("unknown_role") == UserRole.PET_OWNER
        assert role_mapping.get_internal_role(None) == UserRole.PET_OWNER

    async def test_database_error_handling(self, user_sync_service, sample_clerk_user, mock_db_session):
        """Test database error handling during user creation."""
        # Mock database to raise exception
        mock_db_session.execute.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await user_sync_service.create_user_from_clerk(sample_clerk_user)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_db_session.rollback.assert_called_once()

    async def test_concurrent_user_creation_handling(self, user_sync_service, sample_clerk_user, mock_db_session):
        """Test handling of concurrent user creation attempts."""
        # First call returns None (user doesn't exist)
        # Second call (during creation) should handle the conflict
        mock_results = [
            AsyncMock(),  # First check - user doesn't exist
            AsyncMock(),  # Email check - email available
        ]
        mock_results[0].scalar_one_or_none.return_value = None
        mock_results[1].scalar_one_or_none.return_value = None
        mock_db_session.execute.side_effect = mock_results

        # Mock commit to raise integrity error (simulating concurrent creation)
        from sqlalchemy.exc import IntegrityError
        mock_db_session.commit.side_effect = IntegrityError("duplicate key", None, None)

        with pytest.raises(HTTPException) as exc_info:
            await user_sync_service.create_user_from_clerk(sample_clerk_user)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_db_session.rollback.assert_called_once()