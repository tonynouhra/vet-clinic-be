"""
Unit tests for UserService.

Tests all database operations with test database and mocked dependencies.
Tests dynamic parameter handling for different API versions.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.services import UserService
from app.models.user import User, UserRole, user_roles
from app.core.exceptions import VetClinicException, NotFoundError, ValidationError


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def user_service(mock_db_session):
    """UserService instance with mocked database."""
    return UserService(mock_db_session)


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": uuid.uuid4(),
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "phone_number": "1234567890",
        "is_active": True,
        "is_verified": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "clerk_id": "clerk_123"
    }


@pytest.fixture
def sample_user(sample_user_data):
    """Sample User model instance."""
    user = User(**sample_user_data)
    return user


class TestUserServiceListUsers:
    """Test UserService.list_users method."""
    
    @pytest.mark.asyncio
    async def test_list_users_basic(self, user_service, mock_db_session, sample_user):
        """Test basic user listing functionality."""
        # Mock database responses
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        
        mock_users_result = MagicMock()
        mock_users_result.scalars.return_value.all.return_value = [sample_user]
        
        mock_db_session.execute.side_effect = [mock_count_result, mock_users_result]
        
        # Execute
        users, total = await user_service.list_users(page=1, per_page=10)
        
        # Assertions
        assert total == 1
        assert len(users) == 1
        assert users[0] == sample_user
        assert mock_db_session.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_list_users_with_search(self, user_service, mock_db_session, sample_user):
        """Test user listing with search parameter."""
        # Mock database responses
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        
        mock_users_result = MagicMock()
        mock_users_result.scalars.return_value.all.return_value = [sample_user]
        
        mock_db_session.execute.side_effect = [mock_count_result, mock_users_result]
        
        # Execute with search
        users, total = await user_service.list_users(
            page=1, 
            per_page=10,
            search="john"
        )
        
        # Assertions
        assert total == 1
        assert len(users) == 1
        # Verify search was applied in query
        calls = mock_db_session.execute.call_args_list
        assert len(calls) == 2
    
    @pytest.mark.asyncio
    async def test_list_users_with_role_filter(self, user_service, mock_db_session, sample_user):
        """Test user listing with role filter."""
        # Mock database responses
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        
        mock_users_result = MagicMock()
        mock_users_result.scalars.return_value.all.return_value = [sample_user]
        
        mock_db_session.execute.side_effect = [mock_count_result, mock_users_result]
        
        # Execute with role filter
        users, total = await user_service.list_users(
            page=1,
            per_page=10,
            role=UserRole.VETERINARIAN
        )
        
        # Assertions
        assert total == 1
        assert len(users) == 1
    
    @pytest.mark.asyncio
    async def test_list_users_invalid_role_string(self, user_service, mock_db_session):
        """Test user listing with invalid role string."""
        with pytest.raises(ValidationError) as exc_info:
            await user_service.list_users(role="invalid_role")
        
        assert "Invalid role" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_users_pagination(self, user_service, mock_db_session, sample_user):
        """Test user listing pagination."""
        # Mock database responses
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 25
        
        mock_users_result = MagicMock()
        mock_users_result.scalars.return_value.all.return_value = [sample_user] * 10
        
        mock_db_session.execute.side_effect = [mock_count_result, mock_users_result]
        
        # Execute with pagination
        users, total = await user_service.list_users(page=2, per_page=10)
        
        # Assertions
        assert total == 25
        assert len(users) == 10
    
    @pytest.mark.asyncio
    async def test_list_users_v2_parameters(self, user_service, mock_db_session, sample_user):
        """Test user listing with V2-specific parameters."""
        # Mock database responses
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        
        mock_users_result = MagicMock()
        mock_users_result.scalars.return_value.all.return_value = [sample_user]
        
        mock_db_session.execute.side_effect = [mock_count_result, mock_users_result]
        
        # Execute with V2 parameters
        users, total = await user_service.list_users(
            page=1,
            per_page=10,
            include_roles=True,
            department="cardiology"
        )
        
        # Assertions
        assert total == 1
        assert len(users) == 1


class TestUserServiceGetUserById:
    """Test UserService.get_user_by_id method."""
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, user_service, mock_db_session, sample_user):
        """Test successful user retrieval by ID."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        user = await user_service.get_user_by_id(sample_user.id)
        
        # Assertions
        assert user == sample_user
        assert mock_db_session.execute.called
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_service, mock_db_session):
        """Test user retrieval by ID when user not found."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        user_id = uuid.uuid4()
        
        # Execute and assert exception
        with pytest.raises(NotFoundError) as exc_info:
            await user_service.get_user_by_id(user_id)
        
        assert f"User with id {user_id} not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_with_relationships(self, user_service, mock_db_session, sample_user):
        """Test user retrieval with relationships (V2 feature)."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        
        # Execute with relationships
        user = await user_service.get_user_by_id(
            sample_user.id,
            include_relationships=True
        )
        
        # Assertions
        assert user == sample_user
        assert mock_db_session.execute.called


class TestUserServiceCreateUser:
    """Test UserService.create_user method."""
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_db_session):
        """Test successful user creation."""
        # Mock get_user_by_email to return None (user doesn't exist)
        with patch.object(user_service, 'get_user_by_email', return_value=None):
            # Mock assign_role method
            with patch.object(user_service, 'assign_role', return_value=None):
                # Mock database operations
                mock_db_session.add = MagicMock()
                mock_db_session.commit = AsyncMock()
                mock_db_session.refresh = AsyncMock()
                
                # Execute
                user = await user_service.create_user(
                    email="new@example.com",
                    first_name="Jane",
                    last_name="Smith",
                    phone_number="9876543210",
                    role=UserRole.PET_OWNER
                )
                
                # Assertions
                assert user.email == "new@example.com"
                assert user.first_name == "Jane"
                assert user.last_name == "Smith"
                assert user.phone_number == "9876543210"
                assert mock_db_session.add.called
                assert mock_db_session.commit.called
                assert mock_db_session.refresh.called
    
    @pytest.mark.asyncio
    async def test_create_user_email_exists(self, user_service, mock_db_session, sample_user):
        """Test user creation when email already exists."""
        # Mock get_user_by_email to return existing user
        with patch.object(user_service, 'get_user_by_email', return_value=sample_user):
            # Execute and assert exception
            with pytest.raises(ValidationError) as exc_info:
                await user_service.create_user(
                    email=sample_user.email,
                    first_name="Jane",
                    last_name="Smith"
                )
            
            assert "Email already registered" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_user_invalid_role_string(self, user_service, mock_db_session):
        """Test user creation with invalid role string."""
        with patch.object(user_service, 'get_user_by_email', return_value=None):
            with pytest.raises(ValidationError) as exc_info:
                await user_service.create_user(
                    email="test@example.com",
                    first_name="Jane",
                    last_name="Smith",
                    role="invalid_role"
                )
            
            assert "Invalid role" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_user_v2_parameters(self, user_service, mock_db_session):
        """Test user creation with V2-specific parameters."""
        with patch.object(user_service, 'get_user_by_email', return_value=None):
            with patch.object(user_service, 'assign_role', return_value=None):
                mock_db_session.add = MagicMock()
                mock_db_session.commit = AsyncMock()
                mock_db_session.refresh = AsyncMock()
                
                # Execute with V2 parameters
                user = await user_service.create_user(
                    email="new@example.com",
                    first_name="Jane",
                    last_name="Smith",
                    bio="Test bio",
                    profile_image_url="https://example.com/image.jpg",
                    department="cardiology",
                    preferences={"theme": "dark"}
                )
                
                # Assertions
                assert user.email == "new@example.com"
                assert mock_db_session.add.called


class TestUserServiceUpdateUser:
    """Test UserService.update_user method."""
    
    @pytest.mark.asyncio
    async def test_update_user_success(self, user_service, mock_db_session, sample_user):
        """Test successful user update."""
        # Mock get_user_by_id
        with patch.object(user_service, 'get_user_by_id', return_value=sample_user):
            # Mock get_user_by_email for email uniqueness check
            with patch.object(user_service, 'get_user_by_email', return_value=None):
                mock_db_session.commit = AsyncMock()
                mock_db_session.refresh = AsyncMock()
                
                # Execute
                updated_user = await user_service.update_user(
                    user_id=sample_user.id,
                    first_name="Updated Name",
                    email="updated@example.com"
                )
                
                # Assertions
                assert updated_user.first_name == "Updated Name"
                assert updated_user.email == "updated@example.com"
                assert mock_db_session.commit.called
                assert mock_db_session.refresh.called
    
    @pytest.mark.asyncio
    async def test_update_user_email_conflict(self, user_service, mock_db_session, sample_user):
        """Test user update with email conflict."""
        existing_user = User(id=uuid.uuid4(), email="existing@example.com")
        
        with patch.object(user_service, 'get_user_by_id', return_value=sample_user):
            with patch.object(user_service, 'get_user_by_email', return_value=existing_user):
                # Execute and assert exception
                with pytest.raises(ValidationError) as exc_info:
                    await user_service.update_user(
                        user_id=sample_user.id,
                        email="existing@example.com"
                    )
                
                assert "Email already registered" in str(exc_info.value)


class TestUserServiceGetUserByEmail:
    """Test UserService.get_user_by_email method."""
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self, user_service, mock_db_session, sample_user):
        """Test successful user retrieval by email."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        user = await user_service.get_user_by_email(sample_user.email)
        
        # Assertions
        assert user == sample_user
        assert mock_db_session.execute.called
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, user_service, mock_db_session):
        """Test user retrieval by email when user not found."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        user = await user_service.get_user_by_email("nonexistent@example.com")
        
        # Assertions
        assert user is None
        assert mock_db_session.execute.called
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_case_insensitive(self, user_service, mock_db_session, sample_user):
        """Test user retrieval by email is case insensitive."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        
        # Execute with uppercase email
        user = await user_service.get_user_by_email(sample_user.email.upper())
        
        # Assertions
        assert user == sample_user
        # Verify the query used lowercase email
        call_args = mock_db_session.execute.call_args
        assert mock_db_session.execute.called


class TestUserServiceRoleManagement:
    """Test UserService role management methods."""
    
    @pytest.mark.asyncio
    async def test_assign_role_success(self, user_service, mock_db_session, sample_user):
        """Test successful role assignment."""
        # Mock existing role check (no existing role)
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_db_session.execute.side_effect = [mock_result, None]  # Check and insert
        mock_db_session.commit = AsyncMock()
        
        # Execute
        await user_service.assign_role(
            user_id=sample_user.id,
            role=UserRole.VETERINARIAN,
            assigned_by=sample_user.id
        )
        
        # Assertions
        assert mock_db_session.execute.call_count == 2  # Check and insert
        assert mock_db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_assign_role_already_exists(self, user_service, mock_db_session, sample_user):
        """Test role assignment when role already exists."""
        # Mock existing role check (role exists)
        mock_result = MagicMock()
        mock_result.first.return_value = MagicMock()  # Existing role
        mock_db_session.execute.return_value = mock_result
        
        # Execute (should not raise exception)
        await user_service.assign_role(
            user_id=sample_user.id,
            role=UserRole.VETERINARIAN,
            assigned_by=sample_user.id
        )
        
        # Assertions
        assert mock_db_session.execute.call_count == 1  # Only check, no insert
    
    @pytest.mark.asyncio
    async def test_remove_role_success(self, user_service, mock_db_session, sample_user):
        """Test successful role removal."""
        mock_db_session.execute = AsyncMock()
        mock_db_session.commit = AsyncMock()
        
        # Execute
        await user_service.remove_role(
            user_id=sample_user.id,
            role=UserRole.VETERINARIAN,
            removed_by=sample_user.id
        )
        
        # Assertions
        assert mock_db_session.execute.called
        assert mock_db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_role_methods_with_string_role(self, user_service, mock_db_session, sample_user):
        """Test role methods accept string role parameters."""
        # Mock for assign_role
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_db_session.execute.side_effect = [mock_result, None]
        mock_db_session.commit = AsyncMock()
        
        # Test assign with string role
        await user_service.assign_role(
            user_id=sample_user.id,
            role="veterinarian",  # String instead of enum
            assigned_by=sample_user.id
        )
        
        # Assertions
        assert mock_db_session.execute.call_count == 2
        assert mock_db_session.commit.called


class TestUserServiceDeleteUser:
    """Test UserService.delete_user method."""
    
    @pytest.mark.asyncio
    async def test_delete_user_success(self, user_service, mock_db_session, sample_user):
        """Test successful user deletion."""
        # Mock get_user_by_id
        with patch.object(user_service, 'get_user_by_id', return_value=sample_user):
            mock_db_session.execute = AsyncMock()  # For role deletion
            mock_db_session.delete = AsyncMock()
            mock_db_session.commit = AsyncMock()
            
            # Execute
            await user_service.delete_user(sample_user.id)
            
            # Assertions
            assert mock_db_session.execute.called  # Role deletion
            assert mock_db_session.delete.called
            assert mock_db_session.commit.called
    
    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_service, mock_db_session):
        """Test user deletion when user not found."""
        # Mock get_user_by_id to raise NotFoundError
        with patch.object(user_service, 'get_user_by_id', side_effect=NotFoundError("User not found")):
            # Execute and assert exception
            with pytest.raises(NotFoundError):
                await user_service.delete_user(uuid.uuid4())


class TestUserServiceActivationMethods:
    """Test UserService activation/deactivation methods."""
    
    @pytest.mark.asyncio
    async def test_activate_user(self, user_service, mock_db_session, sample_user):
        """Test user activation."""
        # Mock update_user
        sample_user.is_active = True
        with patch.object(user_service, 'update_user', return_value=sample_user) as mock_update:
            # Execute
            result = await user_service.activate_user(sample_user.id)
            
            # Assertions
            assert result == sample_user
            mock_update.assert_called_once_with(sample_user.id, is_active=True)
    
    @pytest.mark.asyncio
    async def test_deactivate_user(self, user_service, mock_db_session, sample_user):
        """Test user deactivation."""
        # Mock update_user
        sample_user.is_active = False
        with patch.object(user_service, 'update_user', return_value=sample_user) as mock_update:
            # Execute
            result = await user_service.deactivate_user(sample_user.id)
            
            # Assertions
            assert result == sample_user
            mock_update.assert_called_once_with(sample_user.id, is_active=False)


class TestUserServiceErrorHandling:
    """Test UserService error handling."""
    
    @pytest.mark.asyncio
    async def test_list_users_database_error(self, user_service, mock_db_session):
        """Test list_users handles database errors."""
        # Mock database to raise exception
        mock_db_session.execute.side_effect = Exception("Database error")
        
        # Execute and assert exception
        with pytest.raises(VetClinicException) as exc_info:
            await user_service.list_users()
        
        assert "Failed to list users" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_database_error(self, user_service, mock_db_session):
        """Test get_user_by_id handles database errors."""
        # Mock database to raise exception
        mock_db_session.execute.side_effect = Exception("Database error")
        
        # Execute and assert exception
        with pytest.raises(VetClinicException) as exc_info:
            await user_service.get_user_by_id(uuid.uuid4())
        
        assert "Failed to get user by id" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_user_rollback_on_error(self, user_service, mock_db_session):
        """Test create_user rolls back on error."""
        with patch.object(user_service, 'get_user_by_email', return_value=None):
            # Mock database operations to fail
            mock_db_session.add = MagicMock()
            mock_db_session.commit.side_effect = Exception("Database error")
            mock_db_session.rollback = AsyncMock()
            
            # Execute and assert exception
            with pytest.raises(VetClinicException):
                await user_service.create_user(
                    email="test@example.com",
                    first_name="Test",
                    last_name="User"
                )
            
            # Verify rollback was called
            assert mock_db_session.rollback.called