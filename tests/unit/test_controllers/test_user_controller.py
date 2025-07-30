"""
Unit tests for UserController.

Tests business logic with mocked service dependencies.
Tests handling of both V1 and V2 schemas in the same controller.
Tests business rule validation and error handling.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from pydantic import BaseModel

from app.users.controller import UserController
from app.users.services import UserService
from app.models.user import User, UserRole
from app.core.exceptions import VetClinicException, NotFoundError, ValidationError


class MockUserCreateV1(BaseModel):
    """Mock V1 user creation schema."""
    email: str
    first_name: str
    last_name: str
    phone_number: str = None
    role: UserRole = UserRole.PET_OWNER


class MockUserCreateV2(BaseModel):
    """Mock V2 user creation schema."""
    email: str
    first_name: str
    last_name: str
    phone_number: str = None
    role: UserRole = UserRole.PET_OWNER
    bio: str = None
    profile_image_url: str = None
    department: str = None
    preferences: dict = None


class MockUserUpdateV1(BaseModel):
    """Mock V1 user update schema."""
    email: str = None
    first_name: str = None
    last_name: str = None
    phone_number: str = None


class MockUserUpdateV2(BaseModel):
    """Mock V2 user update schema."""
    email: str = None
    first_name: str = None
    last_name: str = None
    phone_number: str = None
    bio: str = None
    profile_image_url: str = None
    department: str = None
    preferences: dict = None


@pytest.fixture
def mock_user_service():
    """Mock UserService."""
    return AsyncMock(spec=UserService)


@pytest.fixture
def user_controller(mock_user_service):
    """UserController instance with mocked service."""
    controller = UserController.__new__(UserController)
    controller.service = mock_user_service
    controller.db = AsyncMock()
    return controller


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
    return User(**sample_user_data)


class TestUserControllerListUsers:
    """Test UserController.list_users method."""
    
    @pytest.mark.asyncio
    async def test_list_users_success(self, user_controller, mock_user_service, sample_user):
        """Test successful user listing."""
        # Mock service response
        mock_user_service.list_users.return_value = ([sample_user], 1)
        
        # Execute
        users, total = await user_controller.list_users(page=1, per_page=10)
        
        # Assertions
        assert len(users) == 1
        assert total == 1
        assert users[0] == sample_user
        mock_user_service.list_users.assert_called_once_with(
            page=1,
            per_page=10,
            search=None,
            role=None,
            is_active=None,
            include_roles=False
        )
    
    @pytest.mark.asyncio
    async def test_list_users_invalid_page(self, user_controller, mock_user_service):
        """Test list users with invalid page number."""
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.list_users(page=0, per_page=10)
        
        assert exc_info.value.status_code == 400
        assert "Page must be greater than 0" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_list_users_invalid_per_page(self, user_controller, mock_user_service):
        """Test list users with invalid per_page number."""
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.list_users(page=1, per_page=101)
        
        assert exc_info.value.status_code == 400
        assert "Items per page must be between 1 and 100" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_list_users_with_filters(self, user_controller, mock_user_service, sample_user):
        """Test user listing with filters."""
        # Mock service response
        mock_user_service.list_users.return_value = ([sample_user], 1)
        
        # Execute with filters
        users, total = await user_controller.list_users(
            page=1,
            per_page=10,
            search="john",
            role=UserRole.VETERINARIAN,
            is_active=True,
            include_roles=True
        )
        
        # Assertions
        assert len(users) == 1
        assert total == 1
        mock_user_service.list_users.assert_called_once_with(
            page=1,
            per_page=10,
            search="john",
            role=UserRole.VETERINARIAN,
            is_active=True,
            include_roles=True
        )
    
    @pytest.mark.asyncio
    async def test_list_users_service_error(self, user_controller, mock_user_service):
        """Test list users handles service errors."""
        # Mock service to raise VetClinicException
        mock_user_service.list_users.side_effect = VetClinicException("Service error")
        
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.list_users()
        
        assert exc_info.value.status_code == 400
        assert "Service error" in str(exc_info.value.detail)


class TestUserControllerGetUserById:
    """Test UserController.get_user_by_id method."""
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, user_controller, mock_user_service, sample_user):
        """Test successful user retrieval by ID."""
        # Mock service response
        mock_user_service.get_user_by_id.return_value = sample_user
        
        # Execute
        user = await user_controller.get_user_by_id(sample_user.id)
        
        # Assertions
        assert user == sample_user
        mock_user_service.get_user_by_id.assert_called_once_with(
            user_id=sample_user.id,
            include_roles=False,
            include_relationships=False
        )
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_controller, mock_user_service):
        """Test get user by ID when user not found."""
        user_id = uuid.uuid4()
        # Mock service to raise NotFoundError
        mock_user_service.get_user_by_id.side_effect = NotFoundError("User not found")
        
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.get_user_by_id(user_id)
        
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_v2_parameters(self, user_controller, mock_user_service, sample_user):
        """Test get user by ID with V2 parameters."""
        # Mock service response
        mock_user_service.get_user_by_id.return_value = sample_user
        
        # Execute with V2 parameters
        user = await user_controller.get_user_by_id(
            sample_user.id,
            include_roles=True,
            include_relationships=True
        )
        
        # Assertions
        assert user == sample_user
        mock_user_service.get_user_by_id.assert_called_once_with(
            user_id=sample_user.id,
            include_roles=True,
            include_relationships=True
        )


class TestUserControllerCreateUser:
    """Test UserController.create_user method."""
    
    @pytest.mark.asyncio
    async def test_create_user_v1_schema(self, user_controller, mock_user_service, sample_user):
        """Test user creation with V1 schema."""
        # Mock service response
        mock_user_service.create_user.return_value = sample_user
        
        # Create V1 schema data
        v1_data = MockUserCreateV1(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            phone_number="1234567890"
        )
        
        # Execute
        user = await user_controller.create_user(v1_data, created_by=uuid.uuid4())
        
        # Assertions
        assert user == sample_user
        mock_user_service.create_user.assert_called_once()
        call_kwargs = mock_user_service.create_user.call_args[1]
        assert call_kwargs["email"] == "test@example.com"
        assert call_kwargs["first_name"] == "John"
        assert call_kwargs["last_name"] == "Doe"
        assert call_kwargs["phone_number"] == "1234567890"
        assert call_kwargs["role"] == UserRole.PET_OWNER
    
    @pytest.mark.asyncio
    async def test_create_user_v2_schema(self, user_controller, mock_user_service, sample_user):
        """Test user creation with V2 schema."""
        # Mock service response
        mock_user_service.create_user.return_value = sample_user
        
        # Create V2 schema data with enhanced fields
        v2_data = MockUserCreateV2(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            phone_number="1234567890",
            bio="Test bio",
            department="cardiology",
            preferences={"theme": "dark"}
        )
        
        # Execute
        user = await user_controller.create_user(v2_data, created_by=uuid.uuid4())
        
        # Assertions
        assert user == sample_user
        mock_user_service.create_user.assert_called_once()
        call_kwargs = mock_user_service.create_user.call_args[1]
        assert call_kwargs["email"] == "test@example.com"
        assert call_kwargs["bio"] == "Test bio"
        assert call_kwargs["department"] == "cardiology"
        assert call_kwargs["preferences"] == {"theme": "dark"}
    
    @pytest.mark.asyncio
    async def test_create_user_dict_data(self, user_controller, mock_user_service, sample_user):
        """Test user creation with dictionary data."""
        # Mock service response
        mock_user_service.create_user.return_value = sample_user
        
        # Create dictionary data
        dict_data = {
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "phone_number": "1234567890"
        }
        
        # Execute
        user = await user_controller.create_user(dict_data, created_by=uuid.uuid4())
        
        # Assertions
        assert user == sample_user
        mock_user_service.create_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user_validation_error(self, user_controller, mock_user_service):
        """Test user creation with validation error."""
        # Mock validation to raise ValidationError
        mock_user_service.create_user.side_effect = ValidationError("Email already exists")
        
        v1_data = MockUserCreateV1(
            email="existing@example.com",
            first_name="John",
            last_name="Doe"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.create_user(v1_data)
        
        assert exc_info.value.status_code == 400
        assert "Email already exists" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_create_user_business_validation(self, user_controller, mock_user_service):
        """Test user creation business validation."""
        # Test with missing required fields
        incomplete_data = {
            "first_name": "John",
            "last_name": "Doe"
            # Missing email
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.create_user(incomplete_data)
        
        assert exc_info.value.status_code == 400
        assert "email is required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_create_user_invalid_email(self, user_controller, mock_user_service):
        """Test user creation with invalid email."""
        invalid_data = {
            "email": "invalid-email",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.create_user(invalid_data)
        
        assert exc_info.value.status_code == 400
        assert "Invalid email format" in str(exc_info.value.detail)


class TestUserControllerUpdateUser:
    """Test UserController.update_user method."""
    
    @pytest.mark.asyncio
    async def test_update_user_v1_schema(self, user_controller, mock_user_service, sample_user):
        """Test user update with V1 schema."""
        # Mock service response
        mock_user_service.update_user.return_value = sample_user
        
        # Create V1 update data
        v1_data = MockUserUpdateV1(
            first_name="Updated Name",
            email="updated@example.com"
        )
        
        # Execute
        user = await user_controller.update_user(
            sample_user.id,
            v1_data,
            updated_by=uuid.uuid4()
        )
        
        # Assertions
        assert user == sample_user
        mock_user_service.update_user.assert_called_once()
        call_kwargs = mock_user_service.update_user.call_args[1]
        assert call_kwargs["first_name"] == "Updated Name"
        assert call_kwargs["email"] == "updated@example.com"
    
    @pytest.mark.asyncio
    async def test_update_user_v2_schema(self, user_controller, mock_user_service, sample_user):
        """Test user update with V2 schema."""
        # Mock service response
        mock_user_service.update_user.return_value = sample_user
        
        # Create V2 update data with enhanced fields
        v2_data = MockUserUpdateV2(
            first_name="Updated Name",
            bio="Updated bio",
            department="neurology",
            preferences={"theme": "light"}
        )
        
        # Execute
        user = await user_controller.update_user(
            sample_user.id,
            v2_data,
            updated_by=uuid.uuid4()
        )
        
        # Assertions
        assert user == sample_user
        mock_user_service.update_user.assert_called_once()
        call_kwargs = mock_user_service.update_user.call_args[1]
        assert call_kwargs["first_name"] == "Updated Name"
        assert call_kwargs["bio"] == "Updated bio"
        assert call_kwargs["department"] == "neurology"
        assert call_kwargs["preferences"] == {"theme": "light"}
    
    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_controller, mock_user_service):
        """Test user update when user not found."""
        # Mock service to raise NotFoundError
        mock_user_service.update_user.side_effect = NotFoundError("User not found")
        
        v1_data = MockUserUpdateV1(first_name="Updated Name")
        
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.update_user(uuid.uuid4(), v1_data)
        
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_update_user_invalid_email(self, user_controller, mock_user_service):
        """Test user update with invalid email."""
        dict_data = {
            "email": "invalid-email"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.update_user(uuid.uuid4(), dict_data)
        
        assert exc_info.value.status_code == 400
        assert "Invalid email format" in str(exc_info.value.detail)


class TestUserControllerDeleteUser:
    """Test UserController.delete_user method."""
    
    @pytest.mark.asyncio
    async def test_delete_user_success(self, user_controller, mock_user_service):
        """Test successful user deletion."""
        # Mock service response
        mock_user_service.delete_user.return_value = None
        
        user_id = uuid.uuid4()
        deleted_by = uuid.uuid4()
        
        # Execute
        result = await user_controller.delete_user(user_id, deleted_by)
        
        # Assertions
        assert result["success"] is True
        assert result["message"] == "User deleted successfully"
        mock_user_service.delete_user.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_controller, mock_user_service):
        """Test user deletion when user not found."""
        # Mock service to raise NotFoundError
        mock_user_service.delete_user.side_effect = NotFoundError("User not found")
        
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.delete_user(uuid.uuid4(), uuid.uuid4())
        
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_delete_user_self_deletion(self, user_controller, mock_user_service):
        """Test user deletion prevents self-deletion."""
        user_id = uuid.uuid4()
        
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.delete_user(user_id, user_id)  # Same user
        
        assert exc_info.value.status_code == 400
        assert "Users cannot delete themselves" in str(exc_info.value.detail)


class TestUserControllerActivationMethods:
    """Test UserController activation/deactivation methods."""
    
    @pytest.mark.asyncio
    async def test_activate_user_success(self, user_controller, mock_user_service, sample_user):
        """Test successful user activation."""
        # Mock service response
        sample_user.is_active = True
        mock_user_service.activate_user.return_value = sample_user
        
        user_id = sample_user.id
        activated_by = uuid.uuid4()
        
        # Execute
        user = await user_controller.activate_user(user_id, activated_by)
        
        # Assertions
        assert user == sample_user
        assert user.is_active is True
        mock_user_service.activate_user.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_deactivate_user_success(self, user_controller, mock_user_service, sample_user):
        """Test successful user deactivation."""
        # Mock service response
        sample_user.is_active = False
        mock_user_service.deactivate_user.return_value = sample_user
        
        user_id = sample_user.id
        deactivated_by = uuid.uuid4()
        
        # Execute
        user = await user_controller.deactivate_user(user_id, deactivated_by)
        
        # Assertions
        assert user == sample_user
        assert user.is_active is False
        mock_user_service.deactivate_user.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_activate_user_self_change(self, user_controller, mock_user_service):
        """Test user activation prevents self status change."""
        user_id = uuid.uuid4()
        
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.activate_user(user_id, user_id)  # Same user
        
        assert exc_info.value.status_code == 400
        assert "Users cannot change their own status" in str(exc_info.value.detail)


class TestUserControllerRoleManagement:
    """Test UserController role management methods."""
    
    @pytest.mark.asyncio
    async def test_assign_role_success(self, user_controller, mock_user_service):
        """Test successful role assignment."""
        # Mock service response
        mock_user_service.assign_role.return_value = None
        
        user_id = uuid.uuid4()
        role = UserRole.VETERINARIAN
        assigned_by = uuid.uuid4()
        
        # Execute
        result = await user_controller.assign_role(user_id, role, assigned_by)
        
        # Assertions
        assert result["success"] is True
        assert f"Role {role} assigned successfully" in result["message"]
        mock_user_service.assign_role.assert_called_once_with(user_id, role, assigned_by)
    
    @pytest.mark.asyncio
    async def test_remove_role_success(self, user_controller, mock_user_service):
        """Test successful role removal."""
        # Mock service response
        mock_user_service.remove_role.return_value = None
        
        user_id = uuid.uuid4()
        role = UserRole.VETERINARIAN
        removed_by = uuid.uuid4()
        
        # Execute
        result = await user_controller.remove_role(user_id, role, removed_by)
        
        # Assertions
        assert result["success"] is True
        assert f"Role {role} removed successfully" in result["message"]
        mock_user_service.remove_role.assert_called_once_with(user_id, role, removed_by)
    
    @pytest.mark.asyncio
    async def test_assign_role_invalid_role(self, user_controller, mock_user_service):
        """Test role assignment with invalid role."""
        # Mock service to raise ValidationError
        mock_user_service.assign_role.side_effect = ValidationError("Invalid role")
        
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.assign_role(uuid.uuid4(), "invalid_role", uuid.uuid4())
        
        assert exc_info.value.status_code == 400
        assert "Invalid role" in str(exc_info.value.detail)


class TestUserControllerErrorHandling:
    """Test UserController error handling."""
    
    @pytest.mark.asyncio
    async def test_generic_exception_handling(self, user_controller, mock_user_service):
        """Test generic exception handling."""
        # Mock service to raise generic exception
        mock_user_service.list_users.side_effect = Exception("Unexpected error")
        
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.list_users()
        
        assert exc_info.value.status_code == 500
        assert "Internal server error" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_validation_error_to_http_exception(self, user_controller, mock_user_service):
        """Test ValidationError to HTTPException conversion."""
        # Mock service to raise ValidationError
        mock_user_service.create_user.side_effect = ValidationError("Validation failed")
        
        v1_data = MockUserCreateV1(
            email="test@example.com",
            first_name="John",
            last_name="Doe"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.create_user(v1_data)
        
        assert exc_info.value.status_code == 400
        assert "Validation failed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_vet_clinic_exception_to_http_exception(self, user_controller, mock_user_service):
        """Test VetClinicException to HTTPException conversion."""
        # Mock service to raise VetClinicException
        mock_user_service.get_user_by_id.side_effect = VetClinicException("Service error")
        
        with pytest.raises(HTTPException) as exc_info:
            await user_controller.get_user_by_id(uuid.uuid4())
        
        assert exc_info.value.status_code == 400
        assert "Service error" in str(exc_info.value.detail)


class TestUserControllerBusinessRuleValidation:
    """Test UserController business rule validation methods."""
    
    @pytest.mark.asyncio
    async def test_validate_user_creation_missing_fields(self, user_controller):
        """Test _validate_user_creation with missing fields."""
        incomplete_data = {
            "first_name": "John",
            "last_name": "Doe"
            # Missing email
        }
        
        with pytest.raises(ValidationError) as exc_info:
            await user_controller._validate_user_creation(incomplete_data, None)
        
        assert "email is required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_user_creation_invalid_email(self, user_controller):
        """Test _validate_user_creation with invalid email."""
        invalid_data = {
            "email": "invalid-email",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            await user_controller._validate_user_creation(invalid_data, None)
        
        assert "Invalid email format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_user_creation_invalid_role(self, user_controller):
        """Test _validate_user_creation with invalid role."""
        invalid_data = {
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "invalid_role"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            await user_controller._validate_user_creation(invalid_data, None)
        
        assert "Invalid role" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_user_update_invalid_email(self, user_controller):
        """Test _validate_user_update with invalid email."""
        invalid_data = {
            "email": "invalid-email"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            await user_controller._validate_user_update(uuid.uuid4(), invalid_data, None)
        
        assert "Invalid email format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_user_deletion_self_deletion(self, user_controller, mock_user_service, sample_user):
        """Test _validate_user_deletion prevents self-deletion."""
        # Mock service to return user
        mock_user_service.get_user_by_id.return_value = sample_user
        
        user_id = sample_user.id
        
        with pytest.raises(ValidationError) as exc_info:
            await user_controller._validate_user_deletion(user_id, user_id)
        
        assert "Users cannot delete themselves" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_user_status_change_self_change(self, user_controller, mock_user_service, sample_user):
        """Test _validate_user_status_change prevents self status change."""
        # Mock service to return user
        mock_user_service.get_user_by_id.return_value = sample_user
        
        user_id = sample_user.id
        
        with pytest.raises(ValidationError) as exc_info:
            await user_controller._validate_user_status_change(user_id, user_id)
        
        assert "Users cannot change their own status" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_role_assignment_invalid_role(self, user_controller, mock_user_service, sample_user):
        """Test _validate_role_assignment with invalid role."""
        # Mock service to return user
        mock_user_service.get_user_by_id.return_value = sample_user
        
        with pytest.raises(ValidationError) as exc_info:
            await user_controller._validate_role_assignment(
                sample_user.id,
                "invalid_role",
                uuid.uuid4()
            )
        
        assert "Invalid role" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_role_removal_invalid_role(self, user_controller, mock_user_service, sample_user):
        """Test _validate_role_removal with invalid role."""
        # Mock service to return user
        mock_user_service.get_user_by_id.return_value = sample_user
        
        with pytest.raises(ValidationError) as exc_info:
            await user_controller._validate_role_removal(
                sample_user.id,
                "invalid_role",
                uuid.uuid4()
            )
        
        assert "Invalid role" in str(exc_info.value)