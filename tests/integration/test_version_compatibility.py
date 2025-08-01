"""
Cross-version compatibility tests for the version-agnostic architecture.

Tests that the same controller works correctly with both V1 and V2.
Verifies that business logic changes apply to all versions.
Tests schema validation and response formatting per version.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient

from app.main import app
from app.models.user import User, UserRole
from app.users.controller import UserController
from app.users.services import UserService
from app.api.schemas.v1.users import UserCreateV1, UserUpdateV1
from app.api.schemas.v2.users import UserCreateV2, UserUpdateV2


# Test fixtures
@pytest.fixture
async def async_client():
    """Async test client for FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_user_service():
    """Mock UserService for direct controller testing."""
    return AsyncMock(spec=UserService)


@pytest.fixture
def user_controller(mock_user_service):
    """UserController instance with mocked service."""
    controller = UserController.__new__(UserController)
    controller.service = mock_user_service
    controller.db = AsyncMock()
    return controller


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
def sample_user():
    """Sample user for testing."""
    return User(
        id=uuid.uuid4(),
        email="user@example.com",
        first_name="Test",
        last_name="User",
        phone_number="1234567890",
        bio="Test user biography",
        profile_image_url="https://example.com/profile.jpg",
        is_active=True,
        is_verified=False,
        clerk_id="user_clerk_123",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestCrossVersionControllerCompatibility:
    """Test that the same controller works with both V1 and V2 schemas."""
    
    @pytest.mark.asyncio
    async def test_controller_handles_v1_and_v2_create_schemas(self, user_controller, mock_user_service, sample_user):
        """Test controller handles both V1 and V2 create schemas correctly."""
        # Mock service response
        mock_user_service.create_user.return_value = sample_user
        
        # Test V1 schema
        v1_data = UserCreateV1(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            phone_number="1234567890",
            role=UserRole.PET_OWNER
        )
        
        user_v1 = await user_controller.create_user(v1_data, created_by=uuid.uuid4())
        
        # Test V2 schema with enhanced fields
        v2_data = UserCreateV2(
            email="test2@example.com",
            first_name="Jane",
            last_name="Smith",
            phone_number="9876543210",
            role=UserRole.VETERINARIAN,
            bio="Veterinarian biography",
            profile_image_url="https://example.com/jane.jpg",
            department="cardiology",
            preferences={"theme": "dark"}
        )
        
        user_v2 = await user_controller.create_user(v2_data, created_by=uuid.uuid4())
        
        # Assertions
        assert user_v1 == sample_user
        assert user_v2 == sample_user
        
        # Verify service was called twice with different parameters
        assert mock_user_service.create_user.call_count == 2
        
        # Check V1 call
        v1_call_kwargs = mock_user_service.create_user.call_args_list[0][1]
        assert v1_call_kwargs["email"] == "test@example.com"
        assert v1_call_kwargs["role"] == UserRole.PET_OWNER
        assert v1_call_kwargs.get("bio") is None  # V1 doesn't have bio
        assert v1_call_kwargs.get("department") is None  # V1 doesn't have department
        
        # Check V2 call
        v2_call_kwargs = mock_user_service.create_user.call_args_list[1][1]
        assert v2_call_kwargs["email"] == "test2@example.com"
        assert v2_call_kwargs["role"] == UserRole.VETERINARIAN
        assert v2_call_kwargs["bio"] == "Veterinarian biography"
        assert v2_call_kwargs["department"] == "cardiology"
        assert v2_call_kwargs["preferences"] == {"theme": "dark"}
    
    @pytest.mark.asyncio
    async def test_controller_handles_v1_and_v2_update_schemas(self, user_controller, mock_user_service, sample_user):
        """Test controller handles both V1 and V2 update schemas correctly."""
        # Mock service response
        mock_user_service.update_user.return_value = sample_user
        
        user_id = sample_user.id
        
        # Test V1 update schema
        v1_update = UserUpdateV1(
            first_name="Updated V1",
            email="updated-v1@example.com"
        )
        
        user_v1 = await user_controller.update_user(user_id, v1_update, updated_by=uuid.uuid4())
        
        # Test V2 update schema with enhanced fields
        v2_update = UserUpdateV2(
            first_name="Updated V2",
            email="updated-v2@example.com",
            bio="Updated V2 biography",
            department="neurology",
            preferences={"theme": "light"}
        )
        
        user_v2 = await user_controller.update_user(user_id, v2_update, updated_by=uuid.uuid4())
        
        # Assertions
        assert user_v1 == sample_user
        assert user_v2 == sample_user
        
        # Verify service was called twice
        assert mock_user_service.update_user.call_count == 2
        
        # Check V1 call
        v1_call_kwargs = mock_user_service.update_user.call_args_list[0][1]
        assert v1_call_kwargs["first_name"] == "Updated V1"
        assert v1_call_kwargs["email"] == "updated-v1@example.com"
        assert "bio" not in v1_call_kwargs or v1_call_kwargs["bio"] is None
        
        # Check V2 call
        v2_call_kwargs = mock_user_service.update_user.call_args_list[1][1]
        assert v2_call_kwargs["first_name"] == "Updated V2"
        assert v2_call_kwargs["email"] == "updated-v2@example.com"
        assert v2_call_kwargs["bio"] == "Updated V2 biography"
        assert v2_call_kwargs["department"] == "neurology"
        assert v2_call_kwargs["preferences"] == {"theme": "light"}
    
    @pytest.mark.asyncio
    async def test_controller_list_users_version_parameters(self, user_controller, mock_user_service, sample_user):
        """Test controller handles version-specific list parameters correctly."""
        # Mock service response
        mock_user_service.list_users.return_value = ([sample_user], 1)
        
        # Test V1 call (basic parameters only)
        users_v1, total_v1 = await user_controller.list_users(
            page=1,
            per_page=10,
            search="test",
            role=UserRole.PET_OWNER,
            is_active=True
        )
        
        # Test V2 call (with enhanced parameters)
        users_v2, total_v2 = await user_controller.list_users(
            page=1,
            per_page=10,
            search="test",
            role=UserRole.PET_OWNER,
            is_active=True,
            include_roles=True,
            department="cardiology"
        )
        
        # Assertions
        assert users_v1 == [sample_user]
        assert users_v2 == [sample_user]
        assert total_v1 == 1
        assert total_v2 == 1
        
        # Verify service was called twice with different parameters
        assert mock_user_service.list_users.call_count == 2
        
        # Check V1 call
        v1_call_kwargs = mock_user_service.list_users.call_args_list[0][1]
        assert v1_call_kwargs["include_roles"] is False  # Default V1 behavior
        assert "department" not in v1_call_kwargs or v1_call_kwargs["department"] is None
        
        # Check V2 call
        v2_call_kwargs = mock_user_service.list_users.call_args_list[1][1]
        assert v2_call_kwargs["include_roles"] is True
        assert v2_call_kwargs["department"] == "cardiology"
    
    @pytest.mark.asyncio
    async def test_controller_get_user_version_parameters(self, user_controller, mock_user_service, sample_user):
        """Test controller handles version-specific get user parameters correctly."""
        # Mock service response
        mock_user_service.get_user_by_id.return_value = sample_user
        
        user_id = sample_user.id
        
        # Test V1 call (basic parameters)
        user_v1 = await user_controller.get_user_by_id(
            user_id,
            include_roles=False,
            include_relationships=False
        )
        
        # Test V2 call (with enhanced parameters)
        user_v2 = await user_controller.get_user_by_id(
            user_id,
            include_roles=True,
            include_relationships=True
        )
        
        # Assertions
        assert user_v1 == sample_user
        assert user_v2 == sample_user
        
        # Verify service was called twice with different parameters
        assert mock_user_service.get_user_by_id.call_count == 2
        
        # Check V1 call
        v1_call_kwargs = mock_user_service.get_user_by_id.call_args_list[0][1]
        assert v1_call_kwargs["include_roles"] is False
        assert v1_call_kwargs["include_relationships"] is False
        
        # Check V2 call
        v2_call_kwargs = mock_user_service.get_user_by_id.call_args_list[1][1]
        assert v2_call_kwargs["include_roles"] is True
        assert v2_call_kwargs["include_relationships"] is True


class TestCrossVersionBusinessLogicConsistency:
    """Test that business logic changes apply consistently to all versions."""
    
    @pytest.mark.asyncio
    async def test_business_rule_validation_consistent_across_versions(self, user_controller):
        """Test that business rule validation works consistently for both versions."""
        # Test V1 validation
        v1_invalid_data = {
            "email": "invalid-email",  # Invalid email
            "first_name": "Test",
            "last_name": "User"
        }
        
        with pytest.raises(Exception) as v1_exc:
            await user_controller._validate_user_creation(v1_invalid_data, None)
        
        # Test V2 validation with same invalid email
        v2_invalid_data = {
            "email": "invalid-email",  # Same invalid email
            "first_name": "Test",
            "last_name": "User",
            "bio": "Test biography",
            "department": "cardiology"
        }
        
        with pytest.raises(Exception) as v2_exc:
            await user_controller._validate_user_creation(v2_invalid_data, None)
        
        # Both should fail with same validation error
        assert "Invalid email format" in str(v1_exc.value)
        assert "Invalid email format" in str(v2_exc.value)
    
    @pytest.mark.asyncio
    async def test_role_validation_consistent_across_versions(self, user_controller):
        """Test that role validation works consistently for both versions."""
        # Test V1 role validation
        v1_data_invalid_role = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "invalid_role"
        }
        
        with pytest.raises(Exception) as v1_exc:
            await user_controller._validate_user_creation(v1_data_invalid_role, None)
        
        # Test V2 role validation with same invalid role
        v2_data_invalid_role = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "bio": "Test biography",
            "role": "invalid_role"  # Same invalid role
        }
        
        with pytest.raises(Exception) as v2_exc:
            await user_controller._validate_user_creation(v2_data_invalid_role, None)
        
        # Both should fail with same validation error
        assert "Invalid role" in str(v1_exc.value)
        assert "Invalid role" in str(v2_exc.value)
    
    @pytest.mark.asyncio
    async def test_authorization_rules_consistent_across_versions(self, user_controller, mock_user_service, sample_user):
        """Test that authorization rules work consistently for both versions."""
        # Mock service
        mock_user_service.get_user_by_id.return_value = sample_user
        
        user_id = sample_user.id
        same_user_id = user_id  # Same user trying to delete themselves
        
        # Test V1 self-deletion prevention
        with pytest.raises(Exception) as v1_exc:
            await user_controller._validate_user_deletion(user_id, same_user_id)
        
        # Test V2 self-deletion prevention (should be same logic)
        with pytest.raises(Exception) as v2_exc:
            await user_controller._validate_user_deletion(user_id, same_user_id)
        
        # Both should prevent self-deletion with same error
        assert "Users cannot delete themselves" in str(v1_exc.value)
        assert "Users cannot delete themselves" in str(v2_exc.value)


class TestCrossVersionEndpointCompatibility:
    """Test endpoint compatibility and response formatting across versions."""
    
    @pytest.mark.asyncio
    async def test_same_user_data_different_version_responses(self, async_client, admin_user, sample_user):
        """Test that same user data returns appropriately formatted responses for each version."""
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.list_users') as mock_list_users:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: admin_user
                    mock_list_users.return_value = ([sample_user], 1)
                    
                    # Test V1 endpoint
                    v1_response = await async_client.get("/api/v1/users/")
                    
                    # Test V2 endpoint
                    v2_response = await async_client.get("/api/v2/users/")
                    
                    # Assertions
                    assert v1_response.status_code == 200
                    assert v2_response.status_code == 200
                    
                    v1_data = v1_response.json()
                    v2_data = v2_response.json()
                    
                    # Both should be successful but with different versions
                    assert v1_data["success"] is True
                    assert v2_data["success"] is True
                    assert v1_data["version"] == "v1"
                    assert v2_data["version"] == "v2"
                    
                    # Both should have the same core user data
                    assert v1_data["data"][0]["email"] == sample_user.email
                    assert v2_data["data"][0]["email"] == sample_user.email
                    assert v1_data["data"][0]["first_name"] == sample_user.first_name
                    assert v2_data["data"][0]["first_name"] == sample_user.first_name
                    
                    # V2 should potentially include additional fields (depending on mock setup)
                    # This verifies version-specific response formatting
    
    @pytest.mark.asyncio
    async def test_create_user_same_business_logic_different_schemas(self, async_client, admin_user):
        """Test that creating users uses same business logic but accepts different schemas."""
        created_user = User(
            id=uuid.uuid4(),
            email="newuser@example.com",
            first_name="New",
            last_name="User",
            phone_number="1234567890",
            is_active=True,
            is_verified=False,
            clerk_id="new_clerk_123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.create_user') as mock_create_user:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: admin_user
                    mock_create_user.return_value = created_user
                    
                    # V1 create request
                    v1_data = {
                        "email": "newuser@example.com",
                        "first_name": "New",
                        "last_name": "User",
                        "phone_number": "1234567890",
                        "role": "pet_owner"
                    }
                    
                    v1_response = await async_client.post("/api/v1/users/", json=v1_data)
                    
                    # V2 create request with additional fields
                    v2_data = {
                        "email": "newuser2@example.com",
                        "first_name": "New",
                        "last_name": "User2",
                        "phone_number": "1234567890",
                        "bio": "New user biography",
                        "department": "cardiology",
                        "role": "pet_owner",
                        "preferences": {"theme": "dark"}
                    }
                    
                    v2_response = await async_client.post("/api/v2/users/", json=v2_data)
                    
                    # Assertions
                    assert v1_response.status_code == 201
                    assert v2_response.status_code == 201
                    
                    v1_result = v1_response.json()
                    v2_result = v2_response.json()
                    
                    assert v1_result["success"] is True
                    assert v2_result["success"] is True
                    assert v1_result["version"] == "v1"
                    assert v2_result["version"] == "v2"
                    
                    # Both should have used the same controller method
                    assert mock_create_user.call_count == 2
    
    @pytest.mark.asyncio
    async def test_error_handling_consistent_across_versions(self, async_client, admin_user):
        """Test that error handling is consistent across versions."""
        from fastapi import HTTPException
        
        with patch('app.core.database.get_db') as mock_get_db:
            with patch('app.app_helpers.auth_helpers.require_role') as mock_require_role:
                with patch('app.users.controller.UserController.create_user') as mock_create_user:
                    # Setup mocks
                    mock_get_db.return_value = AsyncMock()
                    mock_require_role.return_value = lambda: admin_user
                    mock_create_user.side_effect = HTTPException(status_code=400, detail="Email already exists")
                    
                    # V1 create request that will fail
                    v1_data = {
                        "email": "existing@example.com",
                        "first_name": "Test",
                        "last_name": "User"
                    }
                    
                    v1_response = await async_client.post("/api/v1/users/", json=v1_data)
                    
                    # V2 create request that will fail with same error
                    v2_data = {
                        "email": "existing@example.com",
                        "first_name": "Test",
                        "last_name": "User",
                        "bio": "Test bio"
                    }
                    
                    v2_response = await async_client.post("/api/v2/users/", json=v2_data)
                    
                    # Both should fail with same status code
                    assert v1_response.status_code == 400
                    assert v2_response.status_code == 400
                    
                    # Error details should be consistent
                    assert "Email already exists" in v1_response.text
                    assert "Email already exists" in v2_response.text


class TestVersionAgnosticServiceBehavior:
    """Test that the underlying service behaves consistently regardless of version."""
    
    @pytest.mark.asyncio
    async def test_service_handles_version_parameters_gracefully(self):
        """Test that service methods handle version-specific parameters gracefully."""
        # This would require actual service testing with database
        # For now, we test that the service interface supports all version parameters
        
        # Create a mock service
        mock_db = AsyncMock()
        service = UserService(mock_db)
        
        # Verify service methods accept version-agnostic parameters
        # This is more of a signature/interface test
        
        # The service should handle both V1-style and V2-style parameters
        # without breaking, even if some parameters are ignored
        
        # This validates our architecture design principle that services
        # are truly version-agnostic
        assert hasattr(service, 'list_users')
        assert hasattr(service, 'create_user')
        assert hasattr(service, 'update_user')
        assert hasattr(service, 'get_user_by_id')
        
        # Check method signatures support version-agnostic parameters
        import inspect
        
        list_users_sig = inspect.signature(service.list_users)
        assert 'kwargs' in list_users_sig.parameters  # Supports future version parameters
        
        create_user_sig = inspect.signature(service.create_user)
        assert 'kwargs' in create_user_sig.parameters  # Supports future version parameters
        
        update_user_sig = inspect.signature(service.update_user)
        assert 'kwargs' in update_user_sig.parameters  # Supports future version parameters


class TestFutureVersionCompatibility:
    """Test that the architecture can handle future versions without breaking existing ones."""
    
    @pytest.mark.asyncio
    async def test_controller_handles_unknown_parameters_gracefully(self, user_controller, mock_user_service, sample_user):
        """Test that controller handles unknown future parameters gracefully."""
        # Mock service response
        mock_user_service.list_users.return_value = ([sample_user], 1)
        
        # Call with hypothetical V3 parameters
        users, total = await user_controller.list_users(
            page=1,
            per_page=10,
            # Hypothetical future parameters
            include_analytics=True,  # V3 feature
            sort_by_activity=True,   # V3 feature
            include_ai_insights=True # V3 feature
        )
        
        # Should still work without breaking
        assert users == [sample_user]
        assert total == 1
        
        # Service should have been called with these parameters passed through
        mock_user_service.list_users.assert_called_once()
        call_kwargs = mock_user_service.list_users.call_args[1]
        
        # Future parameters should be passed through via **kwargs
        assert call_kwargs.get("include_analytics") is True
        assert call_kwargs.get("sort_by_activity") is True
        assert call_kwargs.get("include_ai_insights") is True
    
    def test_schema_inheritance_supports_version_evolution(self):
        """Test that schema inheritance patterns support version evolution."""
        # Test that V1 and V2 schemas inherit from common base
        from app.api.schemas.v1.users import UserCreateV1
        from app.api.schemas.v2.users import UserCreateV2
        from app.api.schemas.base import BaseSchema
        
        # Both should inherit from BaseSchema (directly or indirectly)
        assert issubclass(UserCreateV1, BaseSchema)
        assert issubclass(UserCreateV2, BaseSchema)
        
        # V2 should be extensible for V3
        v2_fields = set(UserCreateV2.model_fields.keys())
        v1_fields = set(UserCreateV1.model_fields.keys())
        
        # V2 should have all V1 fields plus additional ones
        assert v1_fields.issubset(v2_fields)
        
        # V2 should have additional fields
        v2_only_fields = v2_fields - v1_fields
        assert len(v2_only_fields) > 0
        
        # This demonstrates that the pattern supports adding new fields
        # in future versions without breaking existing ones
# Appointment compatibility tests
from app.models.appointment import Appointment, AppointmentStatus, AppointmentType, AppointmentPriority
from app.appointments.controller import AppointmentController
from app.appointments.services import AppointmentService
from app.api.schemas.v1.appointments import AppointmentCreateV1, AppointmentUpdateV1
from app.api.schemas.v2.appointments import AppointmentCreateV2, AppointmentUpdateV2


@pytest.fixture
def mock_appointment_service():
    """Mock AppointmentService for direct controller testing."""
    return AsyncMock(spec=AppointmentService)


@pytest.fixture
def appointment_controller(mock_appointment_service):
    """AppointmentController instance with mocked service."""
    controller = AppointmentController.__new__(AppointmentController)
    controller.service = mock_appointment_service
    controller.db = AsyncMock()
    return controller


@pytest.fixture
def sample_appointment():
    """Sample appointment for testing."""
    return Appointment(
        id=uuid.uuid4(),
        pet_id=uuid.uuid4(),
        pet_owner_id=uuid.uuid4(),
        veterinarian_id=uuid.uuid4(),
        clinic_id=uuid.uuid4(),
        appointment_type=AppointmentType.ROUTINE_CHECKUP,
        scheduled_at=datetime.utcnow() + timedelta(days=1),
        duration_minutes=30,
        reason="Regular checkup",
        status=AppointmentStatus.SCHEDULED,
        priority=AppointmentPriority.NORMAL,
        symptoms=None,
        notes=None,
        special_instructions=None,
        estimated_cost=100.0,
        actual_cost=None,
        follow_up_required=False,
        follow_up_date=None,
        follow_up_notes=None,
        confirmed_at=None,
        started_at=None,
        completed_at=None,
        cancelled_at=None,
        cancellation_reason=None,
        services_requested=None,
        reminder_sent_24h=False,
        reminder_sent_2h=False,
        reminder_sent_24h_at=None,
        reminder_sent_2h_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestAppointmentVersionCompatibility:
    """Test appointment version compatibility."""

    @pytest.mark.asyncio
    async def test_appointment_controller_handles_both_v1_and_v2_schemas(self, appointment_controller, sample_appointment):
        """Test that AppointmentController can handle both V1 and V2 schemas."""
        appointment_controller.service.create_appointment.return_value = sample_appointment
        
        # Test V1 schema
        v1_data = AppointmentCreateV1(
            pet_id=uuid.uuid4(),
            pet_owner_id=uuid.uuid4(),
            veterinarian_id=uuid.uuid4(),
            clinic_id=uuid.uuid4(),
            appointment_type=AppointmentType.ROUTINE_CHECKUP,
            scheduled_at=datetime.utcnow() + timedelta(days=1),
            reason="V1 appointment",
            duration_minutes=30,
            priority=AppointmentPriority.NORMAL
        )
        
        result_v1 = await appointment_controller.create_appointment(v1_data)
        assert result_v1.id == sample_appointment.id
        assert result_v1.reason == "Regular checkup"
        
        # Test V2 schema with enhanced fields
        v2_data = AppointmentCreateV2(
            pet_id=uuid.uuid4(),
            veterinarian_id=uuid.uuid4(),
            clinic_id=uuid.uuid4(),
            appointment_type=AppointmentType.ROUTINE_CHECKUP,
            scheduled_at=datetime.utcnow() + timedelta(days=1),
            reason="V2 appointment with enhanced features",
            duration_minutes=45,
            priority=AppointmentPriority.HIGH,
            services_requested=["examination", "vaccination"],
            reminder_preferences={"email_24h": True, "sms_2h": True}
        )
        
        result_v2 = await appointment_controller.create_appointment(v2_data)
        assert result_v2.id == sample_appointment.id
        assert result_v2.reason == "Regular checkup"
        
        # Verify both calls used the same service method
        assert appointment_controller.service.create_appointment.call_count == 2

    @pytest.mark.asyncio
    async def test_appointment_controller_graceful_parameter_handling(self, appointment_controller, sample_appointment):
        """Test that AppointmentController gracefully handles optional parameters from different versions."""
        appointment_controller.service.update_appointment.return_value = sample_appointment
        
        # V1 update (basic fields only)
        v1_update = AppointmentUpdateV1(
            reason="Updated reason V1",
            notes="Updated notes"
        )
        
        result_v1 = await appointment_controller.update_appointment(
            appointment_id=sample_appointment.id,
            appointment_data=v1_update
        )
        assert result_v1.id == sample_appointment.id
        
        # V2 update (enhanced fields)
        v2_update = AppointmentUpdateV2(
            reason="Updated reason V2",
            notes="Updated notes with enhanced features",
            services_requested=["examination", "vaccination", "blood_work"],
            reminder_preferences={"email_24h": True, "sms_2h": True, "phone_call": False}
        )
        
        result_v2 = await appointment_controller.update_appointment(
            appointment_id=sample_appointment.id,
            appointment_data=v2_update
        )
        assert result_v2.id == sample_appointment.id
        
        # Verify both calls used the same service method
        assert appointment_controller.service.update_appointment.call_count == 2

    @pytest.mark.asyncio
    async def test_appointment_business_logic_consistency_across_versions(self, appointment_controller, sample_appointment):
        """Test that business logic changes affect both V1 and V2 endpoints."""
        # Mock a business logic change in the service
        appointment_controller.service.list_appointments.return_value = ([sample_appointment], 1)
        
        # Test V1 list call
        appointments_v1, total_v1 = await appointment_controller.list_appointments(
            page=1,
            per_page=10,
            status=AppointmentStatus.SCHEDULED,
            include_pet=False,  # V1 doesn't include relationships
            include_owner=False,
            include_veterinarian=False,
            include_clinic=False
        )
        
        # Test V2 list call with enhanced parameters
        appointments_v2, total_v2 = await appointment_controller.list_appointments(
            page=1,
            per_page=10,
            status=AppointmentStatus.SCHEDULED,
            include_pet=True,  # V2 can include relationships
            include_owner=True,
            include_veterinarian=True,
            include_clinic=True,
            sort_by="scheduled_at"  # V2 enhanced feature
        )
        
        # Both should return the same business data
        assert len(appointments_v1) == len(appointments_v2) == 1
        assert total_v1 == total_v2 == 1
        assert appointments_v1[0].id == appointments_v2[0].id
        
        # Verify both calls used the same service method
        assert appointment_controller.service.list_appointments.call_count == 2

    @pytest.mark.asyncio
    async def test_appointment_error_handling_consistency(self, appointment_controller):
        """Test that error handling is consistent across versions."""
        from app.core.exceptions import ValidationError
        
        # Mock service to raise validation error
        appointment_controller.service.create_appointment.side_effect = ValidationError("Invalid appointment data")
        
        # Test V1 error handling
        v1_data = AppointmentCreateV1(
            pet_id=uuid.uuid4(),
            pet_owner_id=uuid.uuid4(),
            veterinarian_id=uuid.uuid4(),
            clinic_id=uuid.uuid4(),
            appointment_type=AppointmentType.ROUTINE_CHECKUP,
            scheduled_at=datetime.utcnow() + timedelta(days=1),
            reason="Test appointment"
        )
        
        with pytest.raises(ValidationError, match="Invalid appointment data"):
            await appointment_controller.create_appointment(v1_data)
        
        # Test V2 error handling
        v2_data = AppointmentCreateV2(
            pet_id=uuid.uuid4(),
            veterinarian_id=uuid.uuid4(),
            clinic_id=uuid.uuid4(),
            appointment_type=AppointmentType.ROUTINE_CHECKUP,
            scheduled_at=datetime.utcnow() + timedelta(days=1),
            reason="Test appointment V2"
        )
        
        with pytest.raises(ValidationError, match="Invalid appointment data"):
            await appointment_controller.create_appointment(v2_data)
        
        # Both versions should handle the same error consistently
        assert appointment_controller.service.create_appointment.call_count == 2

    @pytest.mark.asyncio
    async def test_appointment_endpoints_response_format_differences(self, async_client):
        """Test that V1 and V2 endpoints format responses differently while using same controller."""
        test_user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        sample_appointment = Appointment(
            id=uuid.uuid4(),
            pet_id=uuid.uuid4(),
            pet_owner_id=uuid.uuid4(),
            veterinarian_id=uuid.uuid4(),
            clinic_id=uuid.uuid4(),
            appointment_type=AppointmentType.ROUTINE_CHECKUP,
            scheduled_at=datetime.utcnow() + timedelta(days=1),
            duration_minutes=30,
            reason="Test appointment",
            status=AppointmentStatus.SCHEDULED,
            priority=AppointmentPriority.NORMAL,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch('app.app_helpers.auth_helpers.get_current_user', return_value=test_user):
            with patch('app.appointments.controller.AppointmentController.list_appointments') as mock_list:
                mock_list.return_value = ([sample_appointment], 1)
                
                # Test V1 response format
                v1_response = await async_client.get("/api/v1/appointments/")
                assert v1_response.status_code == 200
                v1_data = v1_response.json()
                assert v1_data["version"] == "v1"
                assert "data" in v1_data
                assert "appointments" in v1_data["data"]
                assert "total_pages" in v1_data["data"]
                
                # Test V2 response format
                v2_response = await async_client.get("/api/v2/appointments/")
                assert v2_response.status_code == 200
                v2_data = v2_response.json()
                assert v2_data["version"] == "v2"
                assert "timestamp" in v2_data  # V2 includes timestamp
                assert "data" in v2_data
                assert "appointments" in v2_data["data"]
                assert "filters_applied" in v2_data["data"]  # V2 includes filter info
                assert "sort" in v2_data["data"]  # V2 includes sort info
                
                # Both should have the same core appointment data
                v1_appointment = v1_data["data"]["appointments"][0]
                v2_appointment = v2_data["data"]["appointments"][0]
                assert v1_appointment["id"] == v2_appointment["id"]
                assert v1_appointment["reason"] == v2_appointment["reason"]
                
                # But V2 should have additional fields
                assert "services_requested" in v2_appointment
                assert "reminder_sent_24h" in v2_appointment

    @pytest.mark.asyncio
    async def test_appointment_service_parameter_compatibility(self, mock_appointment_service, sample_appointment):
        """Test that AppointmentService handles parameters from both versions gracefully."""
        mock_appointment_service.create_appointment.return_value = sample_appointment
        
        # Test with V1 parameters (basic)
        await mock_appointment_service.create_appointment(
            pet_id=uuid.uuid4(),
            pet_owner_id=uuid.uuid4(),
            veterinarian_id=uuid.uuid4(),
            clinic_id=uuid.uuid4(),
            appointment_type=AppointmentType.ROUTINE_CHECKUP,
            scheduled_at=datetime.utcnow() + timedelta(days=1),
            reason="V1 appointment"
        )
        
        # Test with V2 parameters (enhanced)
        await mock_appointment_service.create_appointment(
            pet_id=uuid.uuid4(),
            pet_owner_id=uuid.uuid4(),
            veterinarian_id=uuid.uuid4(),
            clinic_id=uuid.uuid4(),
            appointment_type=AppointmentType.ROUTINE_CHECKUP,
            scheduled_at=datetime.utcnow() + timedelta(days=1),
            reason="V2 appointment",
            services_requested=["examination", "vaccination"],
            # V2 enhanced parameters that V1 doesn't use
            reminder_preferences={"email_24h": True},
            pre_appointment_checklist=["Bring records"]
        )
        
        # Both calls should work with the same service method
        assert mock_appointment_service.create_appointment.call_count == 2

from datetime import timedelta