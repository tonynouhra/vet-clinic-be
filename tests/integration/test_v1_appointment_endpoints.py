"""
Integration tests for V1 Appointment endpoints.

Tests complete controller-service flow for V1 appointment endpoints.
Tests authentication, authorization, and error scenarios.
"""

import pytest
import uuid
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.models.appointment import Appointment, AppointmentStatus, AppointmentType, AppointmentPriority
from app.models.user import User, UserRole
from app.core.database import get_db
from app.app_helpers.auth_helpers import get_current_user


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
def test_user():
    """Test user for authentication."""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_appointment():
    """Sample appointment for testing."""
    appointment_id = uuid.uuid4()
    pet_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    vet_id = uuid.uuid4()
    clinic_id = uuid.uuid4()
    
    return Appointment(
        id=appointment_id,
        pet_id=pet_id,
        pet_owner_id=owner_id,
        veterinarian_id=vet_id,
        clinic_id=clinic_id,
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


@pytest.fixture
def appointment_create_data():
    """Valid appointment creation data."""
    return {
        "pet_id": str(uuid.uuid4()),
        "pet_owner_id": str(uuid.uuid4()),
        "veterinarian_id": str(uuid.uuid4()),
        "clinic_id": str(uuid.uuid4()),
        "appointment_type": "routine_checkup",
        "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "reason": "Regular checkup for my pet",
        "duration_minutes": 30,
        "priority": "normal",
        "symptoms": "No symptoms, just routine",
        "notes": "Pet is generally healthy",
        "estimated_cost": 100.0,
        "follow_up_required": False
    }


class TestV1AppointmentEndpoints:
    """Test class for V1 appointment endpoints."""

    @pytest.mark.asyncio
    async def test_list_appointments_success(self, async_client, test_user, sample_appointment):
        """Test successful appointment listing."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.list_appointments') as mock_list:
                mock_list.return_value = ([sample_appointment], 1)
                
                response = await async_client.get("/api/v1/appointments/")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v1"
                assert "data" in data
                assert "appointments" in data["data"]
                assert len(data["data"]["appointments"]) == 1
                assert data["data"]["total"] == 1
                
                # Verify appointment structure
                appointment = data["data"]["appointments"][0]
                assert "id" in appointment
                assert "pet_id" in appointment
                assert "appointment_type" in appointment
                assert "scheduled_at" in appointment
                assert "status" in appointment
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_appointments_with_filters(self, async_client, test_user, sample_appointment):
        """Test appointment listing with filters."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.list_appointments') as mock_list:
                mock_list.return_value = ([sample_appointment], 1)
                
                response = await async_client.get(
                    "/api/v1/appointments/",
                    params={
                        "page": 1,
                        "per_page": 10,
                        "status": "scheduled",
                        "appointment_type": "routine_checkup",
                        "upcoming_only": True
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                
                # Verify controller was called with correct parameters
                mock_list.assert_called_once()
                call_args = mock_list.call_args[1]
                assert call_args["page"] == 1
                assert call_args["per_page"] == 10
                assert call_args["status"] == AppointmentStatus.SCHEDULED
                assert call_args["appointment_type"] == AppointmentType.ROUTINE_CHECKUP
                assert call_args["upcoming_only"] is True
                assert call_args["include_pet"] is False  # V1 doesn't include relationships
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_appointment_success(self, async_client, test_user, sample_appointment, appointment_create_data):
        """Test successful appointment creation."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.create_appointment') as mock_create:
                mock_create.return_value = sample_appointment
                
                response = await async_client.post(
                    "/api/v1/appointments/",
                    json=appointment_create_data
                )
                
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v1"
                assert "data" in data
                assert data["message"] == "Appointment created successfully"
                
                # Verify appointment data
                appointment = data["data"]
                assert appointment["appointment_type"] == "routine_checkup"
                assert appointment["status"] == "scheduled"
                assert appointment["reason"] == "Regular checkup"
                
                # Verify controller was called with correct data
                mock_create.assert_called_once()
                call_args = mock_create.call_args[1]
                assert call_args["created_by"] == test_user.id
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_appointment_validation_error(self, async_client, test_user):
        """Test appointment creation with validation errors."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            # Missing required fields
            invalid_data = {
                "reason": "Test appointment"
                # Missing required fields like pet_id, veterinarian_id, etc.
            }
            
            response = await async_client.post(
                "/api/v1/appointments/",
                json=invalid_data
            )
            
            assert response.status_code == 422  # Validation error
            
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_appointment_success(self, async_client, test_user, sample_appointment):
        """Test successful appointment retrieval."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.get_appointment_by_id') as mock_get:
                mock_get.return_value = sample_appointment
                
                response = await async_client.get(f"/api/v1/appointments/{sample_appointment.id}")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v1"
                assert "data" in data
                
                # Verify appointment data
                appointment = data["data"]
                assert appointment["id"] == str(sample_appointment.id)
                assert appointment["reason"] == sample_appointment.reason
                assert appointment["status"] == sample_appointment.status.value
                
                # Verify controller was called with correct parameters
                mock_get.assert_called_once_with(
                    appointment_id=sample_appointment.id,
                    include_pet=False,  # V1 doesn't include relationships
                    include_owner=False,
                    include_veterinarian=False,
                    include_clinic=False
                )
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_appointment_not_found(self, async_client, test_user):
        """Test appointment retrieval with non-existent ID."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.get_appointment_by_id') as mock_get:
                from app.core.exceptions import NotFoundError
                mock_get.side_effect = NotFoundError("Appointment not found")
                
                fake_id = uuid.uuid4()
                response = await async_client.get(f"/api/v1/appointments/{fake_id}")
                
                assert response.status_code == 404
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_appointment_success(self, async_client, test_user, sample_appointment):
        """Test successful appointment update."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.update_appointment') as mock_update:
                updated_appointment = sample_appointment
                updated_appointment.reason = "Updated reason"
                mock_update.return_value = updated_appointment
                
                update_data = {
                    "reason": "Updated reason",
                    "notes": "Updated notes"
                }
                
                response = await async_client.put(
                    f"/api/v1/appointments/{sample_appointment.id}",
                    json=update_data
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v1"
                assert data["data"]["reason"] == "Updated reason"
                
                # Verify controller was called
                mock_update.assert_called_once()
                call_args = mock_update.call_args[1]
                assert call_args["appointment_id"] == sample_appointment.id
                assert call_args["updated_by"] == test_user.id
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_cancel_appointment_success(self, async_client, test_user, sample_appointment):
        """Test successful appointment cancellation."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.cancel_appointment') as mock_cancel:
                cancelled_appointment = sample_appointment
                cancelled_appointment.status = AppointmentStatus.CANCELLED
                cancelled_appointment.cancellation_reason = "Patient request"
                mock_cancel.return_value = cancelled_appointment
                
                cancel_data = {
                    "cancellation_reason": "Patient request"
                }
                
                response = await async_client.post(
                    f"/api/v1/appointments/{sample_appointment.id}/cancel",
                    json=cancel_data
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v1"
                assert data["data"]["status"] == "cancelled"
                assert data["data"]["cancellation_reason"] == "Patient request"
                
                # Verify controller was called
                mock_cancel.assert_called_once_with(
                    appointment_id=sample_appointment.id,
                    cancellation_reason="Patient request",
                    cancelled_by=test_user.id
                )
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_confirm_appointment_success(self, async_client, test_user, sample_appointment):
        """Test successful appointment confirmation."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.confirm_appointment') as mock_confirm:
                confirmed_appointment = sample_appointment
                confirmed_appointment.status = AppointmentStatus.CONFIRMED
                confirmed_appointment.confirmed_at = datetime.utcnow()
                mock_confirm.return_value = confirmed_appointment
                
                response = await async_client.post(f"/api/v1/appointments/{sample_appointment.id}/confirm")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v1"
                assert data["data"]["status"] == "confirmed"
                assert data["data"]["confirmed_at"] is not None
                
                # Verify controller was called
                mock_confirm.assert_called_once_with(
                    appointment_id=sample_appointment.id,
                    confirmed_by=test_user.id
                )
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_start_appointment_success(self, async_client, test_user, sample_appointment):
        """Test successful appointment start."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.start_appointment') as mock_start:
                started_appointment = sample_appointment
                started_appointment.status = AppointmentStatus.IN_PROGRESS
                started_appointment.started_at = datetime.utcnow()
                mock_start.return_value = started_appointment
                
                response = await async_client.post(f"/api/v1/appointments/{sample_appointment.id}/start")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v1"
                assert data["data"]["status"] == "in_progress"
                assert data["data"]["started_at"] is not None
                
                # Verify controller was called
                mock_start.assert_called_once_with(
                    appointment_id=sample_appointment.id,
                    started_by=test_user.id
                )
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_complete_appointment_success(self, async_client, test_user, sample_appointment):
        """Test successful appointment completion."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.complete_appointment') as mock_complete:
                completed_appointment = sample_appointment
                completed_appointment.status = AppointmentStatus.COMPLETED
                completed_appointment.completed_at = datetime.utcnow()
                completed_appointment.actual_cost = 120.0
                mock_complete.return_value = completed_appointment
                
                complete_data = {
                    "actual_cost": 120.0
                }
                
                response = await async_client.post(
                    f"/api/v1/appointments/{sample_appointment.id}/complete",
                    json=complete_data
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v1"
                assert data["data"]["status"] == "completed"
                assert data["data"]["actual_cost"] == 120.0
                assert data["data"]["completed_at"] is not None
                
                # Verify controller was called
                mock_complete.assert_called_once_with(
                    appointment_id=sample_appointment.id,
                    actual_cost=120.0,
                    completed_by=test_user.id
                )
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_reschedule_appointment_success(self, async_client, test_user, sample_appointment):
        """Test successful appointment rescheduling."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.reschedule_appointment') as mock_reschedule:
                new_time = datetime.utcnow() + timedelta(days=2)
                rescheduled_appointment = sample_appointment
                rescheduled_appointment.scheduled_at = new_time
                rescheduled_appointment.status = AppointmentStatus.SCHEDULED
                mock_reschedule.return_value = rescheduled_appointment
                
                reschedule_data = {
                    "new_scheduled_at": new_time.isoformat()
                }
                
                response = await async_client.post(
                    f"/api/v1/appointments/{sample_appointment.id}/reschedule",
                    json=reschedule_data
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v1"
                assert data["data"]["status"] == "scheduled"
                
                # Verify controller was called
                mock_reschedule.assert_called_once_with(
                    appointment_id=sample_appointment.id,
                    new_scheduled_at=new_time,
                    rescheduled_by=test_user.id
                )
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_appointment_success(self, async_client, test_user, sample_appointment):
        """Test successful appointment deletion."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.delete_appointment') as mock_delete:
                mock_delete.return_value = {"success": True, "message": "Appointment deleted successfully"}
                
                response = await async_client.delete(f"/api/v1/appointments/{sample_appointment.id}")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v1"
                assert "appointment_id" in data["data"]
                assert data["message"] == "Appointment deleted successfully"
                
                # Verify controller was called
                mock_delete.assert_called_once_with(
                    appointment_id=sample_appointment.id,
                    deleted_by=test_user.id
                )
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, async_client):
        """Test unauthorized access to appointment endpoints."""
        # No authentication provided
        response = await async_client.get("/api/v1/appointments/")
        assert response.status_code == 401  # Unauthorized

    @pytest.mark.asyncio
    async def test_invalid_appointment_id_format(self, async_client, test_user):
        """Test invalid appointment ID format."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            response = await async_client.get("/api/v1/appointments/invalid-uuid")
            assert response.status_code == 422  # Validation error
            
            app.dependency_overrides.clear()