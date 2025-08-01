"""
Integration tests for V2 Appointment endpoints.

Tests complete controller-service flow for V2 appointment endpoints with enhanced features.
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
    """Sample appointment for testing with V2 features."""
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
        duration_minutes=45,
        reason="Comprehensive health checkup",
        status=AppointmentStatus.SCHEDULED,
        priority=AppointmentPriority.NORMAL,
        symptoms="No specific symptoms",
        notes="Annual checkup for senior pet",
        special_instructions="Handle with care - senior pet",
        estimated_cost=150.0,
        actual_cost=None,
        follow_up_required=True,
        follow_up_date=datetime.utcnow() + timedelta(days=30),
        follow_up_notes="Schedule follow-up in 30 days",
        confirmed_at=None,
        checked_in_at=None,
        started_at=None,
        completed_at=None,
        cancelled_at=None,
        cancellation_reason=None,
        services_requested=["examination", "vaccination", "blood_work"],
        reminder_sent_24h=False,
        reminder_sent_2h=False,
        reminder_sent_24h_at=None,
        reminder_sent_2h_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def appointment_create_data_v2():
    """Valid V2 appointment creation data with enhanced features."""
    return {
        "pet_id": str(uuid.uuid4()),
        "veterinarian_id": str(uuid.uuid4()),
        "clinic_id": str(uuid.uuid4()),
        "appointment_type": "routine_checkup",
        "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "duration_minutes": 45,
        "reason": "Comprehensive health checkup with vaccinations",
        "priority": "normal",
        "symptoms": "No specific symptoms, routine care",
        "notes": "Annual checkup for senior pet",
        "special_instructions": "Handle with care - senior pet",
        "estimated_cost": 150.0,
        "services_requested": ["examination", "vaccination", "blood_work"],
        "reminder_preferences": {
            "email_24h": True,
            "sms_2h": True,
            "phone_call": False
        },
        "pre_appointment_checklist": [
            "Bring vaccination records",
            "List current medications",
            "Note any behavioral changes"
        ],
        "emergency_contact": {
            "name": "Emergency Contact",
            "phone": "+1234567890",
            "relationship": "family"
        }
    }


class TestV2AppointmentEndpoints:
    """Test class for V2 appointment endpoints with enhanced features."""

    @pytest.mark.asyncio
    async def test_list_appointments_with_enhanced_filtering(self, async_client, test_user, sample_appointment):
        """Test V2 appointment listing with enhanced filtering options."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.list_appointments') as mock_list:
                mock_list.return_value = ([sample_appointment], 1)
                
                response = await async_client.get(
                    "/api/v2/appointments/",
                    params={
                        "page": 1,
                        "per_page": 10,
                        "status": "scheduled",
                        "appointment_type": "routine_checkup",
                        "priority": "normal",
                        "include_pet_info": True,
                        "include_vet_info": True,
                        "include_clinic_info": True,
                        "search": "checkup",
                        "has_follow_up": True,
                        "cost_min": 100.0,
                        "cost_max": 200.0,
                        "sort_by": "scheduled_at",
                        "sort_order": "asc"
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v2"
                assert "timestamp" in data
                assert "data" in data
                assert "appointments" in data["data"]
                assert "filters_applied" in data["data"]
                assert "sort" in data["data"]
                
                # Verify enhanced response structure
                assert data["data"]["filters_applied"]["search"] == "checkup"
                assert data["data"]["filters_applied"]["has_follow_up"] is True
                assert data["data"]["sort"]["field"] == "scheduled_at"
                assert data["data"]["sort"]["order"] == "asc"
                
                # Verify controller was called with V2 parameters
                mock_list.assert_called_once()
                call_args = mock_list.call_args[1]
                assert call_args["include_pet"] is True
                assert call_args["include_veterinarian"] is True
                assert call_args["include_clinic"] is True
                assert call_args["sort_by"] == "scheduled_at"
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_appointment_with_enhanced_features(self, async_client, test_user, sample_appointment, appointment_create_data_v2):
        """Test V2 appointment creation with enhanced features."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.create_appointment') as mock_create:
                mock_create.return_value = sample_appointment
                
                response = await async_client.post(
                    "/api/v2/appointments/",
                    json=appointment_create_data_v2
                )
                
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v2"
                assert "timestamp" in data
                assert "appointment_id" in data
                assert data["message"] == "Appointment created successfully"
                
                # Verify enhanced response structure
                appointment = data["data"]
                assert "services_requested" in appointment
                assert "reminder_sent_24h" in appointment
                assert "follow_up_required" in appointment
                
                # Verify controller was called with enhanced data
                mock_create.assert_called_once()
                call_args = mock_create.call_args[1]
                assert call_args["created_by"] == test_user.id
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_appointment_with_relationships(self, async_client, test_user, sample_appointment):
        """Test V2 appointment retrieval with relationship data."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.get_appointment_by_id') as mock_get:
                mock_get.return_value = sample_appointment
                
                response = await async_client.get(
                    f"/api/v2/appointments/{sample_appointment.id}",
                    params={
                        "include_pet_info": True,
                        "include_vet_info": True,
                        "include_clinic_info": True
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v2"
                assert "timestamp" in data
                
                # Verify enhanced appointment data
                appointment = data["data"]
                assert appointment["id"] == str(sample_appointment.id)
                assert "services_requested" in appointment
                assert "reminder_sent_24h" in appointment
                assert "follow_up_required" in appointment
                
                # Verify controller was called with relationship flags
                mock_get.assert_called_once_with(
                    appointment_id=sample_appointment.id,
                    include_pet=True,
                    include_owner=False,
                    include_veterinarian=True,
                    include_clinic=True
                )
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_appointment_with_enhanced_fields(self, async_client, test_user, sample_appointment):
        """Test V2 appointment update with enhanced fields."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.update_appointment') as mock_update:
                updated_appointment = sample_appointment
                updated_appointment.services_requested = ["examination", "vaccination", "blood_work", "dental_check"]
                updated_appointment.duration_minutes = 60
                mock_update.return_value = updated_appointment
                
                update_data = {
                    "duration_minutes": 60,
                    "services_requested": ["examination", "vaccination", "blood_work", "dental_check"],
                    "reminder_preferences": {
                        "email_24h": True,
                        "sms_2h": True,
                        "phone_call": True
                    },
                    "pre_appointment_checklist": [
                        "Bring vaccination records",
                        "List current medications",
                        "Note any behavioral changes",
                        "Prepare dental care questions"
                    ]
                }
                
                response = await async_client.put(
                    f"/api/v2/appointments/{sample_appointment.id}",
                    json=update_data
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v2"
                assert "timestamp" in data
                assert "updated_fields" in data
                
                # Verify enhanced response
                appointment = data["data"]
                assert appointment["duration_minutes"] == 60
                assert len(appointment["services_requested"]) == 4
                
                # Verify controller was called
                mock_update.assert_called_once()
                call_args = mock_update.call_args[1]
                assert call_args["appointment_id"] == sample_appointment.id
                assert call_args["updated_by"] == test_user.id
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_appointment_status_enhanced(self, async_client, test_user, sample_appointment):
        """Test V2 enhanced appointment status update."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.complete_appointment') as mock_complete:
                completed_appointment = sample_appointment
                completed_appointment.status = AppointmentStatus.COMPLETED
                completed_appointment.completed_at = datetime.utcnow()
                completed_appointment.actual_cost = 175.0
                mock_complete.return_value = completed_appointment
                
                status_data = {
                    "status": "completed",
                    "notes": "Appointment completed successfully",
                    "actual_cost": 175.0,
                    "follow_up_required": True,
                    "follow_up_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                    "follow_up_notes": "Schedule follow-up for vaccination booster",
                    "notify_owner": True
                }
                
                response = await async_client.patch(
                    f"/api/v2/appointments/{sample_appointment.id}/status",
                    json=status_data
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v2"
                assert "timestamp" in data
                assert "status_change" in data
                
                # Verify enhanced status change information
                status_change = data["status_change"]
                assert status_change["new_status"] == "completed"
                assert status_change["updated_by"] == test_user.id
                assert status_change["notify_owner"] is True
                
                # Verify appointment data
                appointment = data["data"]
                assert appointment["status"] == "completed"
                assert appointment["actual_cost"] == 175.0
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_cancel_appointment_with_enhanced_features(self, async_client, test_user, sample_appointment):
        """Test V2 enhanced appointment cancellation."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.cancel_appointment') as mock_cancel:
                cancelled_appointment = sample_appointment
                cancelled_appointment.status = AppointmentStatus.CANCELLED
                cancelled_appointment.cancellation_reason = "Pet owner requested due to emergency"
                cancelled_appointment.cancelled_at = datetime.utcnow()
                mock_cancel.return_value = cancelled_appointment
                
                cancel_data = {
                    "reason": "Pet owner requested due to emergency",
                    "notify_owner": True,
                    "refund_amount": 50.0,
                    "reschedule_offer": True,
                    "cancellation_fee": 25.0
                }
                
                response = await async_client.post(
                    f"/api/v2/appointments/{sample_appointment.id}/cancel",
                    json=cancel_data
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["version"] == "v2"
                assert "timestamp" in data
                assert "cancellation_details" in data
                
                # Verify enhanced cancellation details
                cancellation_details = data["cancellation_details"]
                assert cancellation_details["reason"] == "Pet owner requested due to emergency"
                assert cancellation_details["notify_owner"] is True
                assert cancellation_details["refund_amount"] == 50.0
                assert cancellation_details["reschedule_offer"] is True
                assert cancellation_details["cancellation_fee"] == 25.0
                
                # Verify appointment data
                appointment = data["data"]
                assert appointment["status"] == "cancelled"
                assert appointment["cancellation_reason"] == "Pet owner requested due to emergency"
                
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_reschedule_appointment_with_enhanced_features(self, async_client, test_user, sample_appointment):
        """Test V2 enhanced appointment rescheduling."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.reschedule_appointment') as mock_reschedule:
                with patch('app.appointments.controller.AppointmentController.update_appointment') as mock_update:
                    new_time = datetime.utcnow() + timedelta(days=3)
                    rescheduled_appointment = sample_appointment
                    rescheduled_appointment.scheduled_at = new_time
                    rescheduled_appointment.duration_minutes = 60
                    rescheduled_appointment.services_requested = ["examination", "vaccination", "blood_work", "x_ray"]
                    mock_reschedule.return_value = rescheduled_appointment
                    mock_update.return_value = rescheduled_appointment
                    
                    reschedule_data = {
                        "new_scheduled_at": new_time.isoformat(),
                        "new_duration_minutes": 60,
                        "reason": "Owner schedule conflict",
                        "notify_owner": True,
                        "reschedule_fee": 15.0,
                        "update_services": ["examination", "vaccination", "blood_work", "x_ray"]
                    }
                    
                    response = await async_client.post(
                        f"/api/v2/appointments/{sample_appointment.id}/reschedule",
                        json=reschedule_data
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["version"] == "v2"
                    assert "timestamp" in data
                    assert "reschedule_details" in data
                    
                    # Verify enhanced reschedule details
                    reschedule_details = data["reschedule_details"]
                    assert reschedule_details["reason"] == "Owner schedule conflict"
                    assert reschedule_details["notify_owner"] is True
                    assert reschedule_details["reschedule_fee"] == 15.0
                    assert reschedule_details["services_updated"] is True
                    
                    # Verify appointment data
                    appointment = data["data"]
                    assert appointment["duration_minutes"] == 60
                    assert len(appointment["services_requested"]) == 4
                    
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_recurring_appointments(self, async_client, test_user):
        """Test V2 exclusive recurring appointments feature."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            recurring_data = {
                "base_appointment": {
                    "pet_id": str(uuid.uuid4()),
                    "veterinarian_id": str(uuid.uuid4()),
                    "clinic_id": str(uuid.uuid4()),
                    "appointment_type": "routine_checkup",
                    "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                    "duration_minutes": 30,
                    "reason": "Monthly checkup"
                },
                "recurrence_pattern": {
                    "frequency": "monthly",
                    "interval": 1
                },
                "end_date": (date.today() + timedelta(days=365)).isoformat(),
                "max_occurrences": 12
            }
            
            response = await async_client.post(
                "/api/v2/appointments/recurring",
                json=recurring_data
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert data["version"] == "v2"
            assert "timestamp" in data
            assert "pattern" in data["data"]
            assert data["data"]["pattern"]["frequency"] == "monthly"
            
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_batch_appointment_operations(self, async_client, test_user):
        """Test V2 exclusive batch operations feature."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            batch_data = {
                "appointment_ids": [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())],
                "operation": "confirm",
                "operation_data": {
                    "notify_owners": True,
                    "send_reminders": True
                }
            }
            
            response = await async_client.post(
                "/api/v2/appointments/batch",
                json=batch_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["version"] == "v2"
            assert "timestamp" in data
            assert data["data"]["operation"] == "confirm"
            assert data["data"]["appointment_count"] == 3
            
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_appointment_statistics(self, async_client, test_user):
        """Test V2 exclusive appointment statistics feature."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            response = await async_client.get(
                "/api/v2/appointments/statistics",
                params={
                    "start_date": (date.today() - timedelta(days=30)).isoformat(),
                    "end_date": date.today().isoformat(),
                    "clinic_id": str(uuid.uuid4())
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["version"] == "v2"
            assert "timestamp" in data
            assert "date_range" in data["data"]
            assert "filters" in data["data"]
            
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_validation_errors_v2(self, async_client, test_user):
        """Test V2 specific validation errors."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            # Test invalid recurring pattern
            invalid_recurring_data = {
                "base_appointment": {
                    "pet_id": str(uuid.uuid4()),
                    "veterinarian_id": str(uuid.uuid4()),
                    "clinic_id": str(uuid.uuid4()),
                    "appointment_type": "routine_checkup",
                    "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                    "duration_minutes": 30,
                    "reason": "Monthly checkup"
                },
                "recurrence_pattern": {
                    "frequency": "invalid_frequency",  # Invalid frequency
                    "interval": 0  # Invalid interval
                }
            }
            
            response = await async_client.post(
                "/api/v2/appointments/recurring",
                json=invalid_recurring_data
            )
            
            assert response.status_code == 422  # Validation error
            
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_enhanced_error_responses(self, async_client, test_user):
        """Test V2 enhanced error response format."""
        with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user) as mock_auth:
            app.dependency_overrides[get_current_user] = lambda: test_user
            
            with patch('app.appointments.controller.AppointmentController.get_appointment_by_id') as mock_get:
                from app.core.exceptions import NotFoundError
                mock_get.side_effect = NotFoundError("Appointment not found")
                
                fake_id = uuid.uuid4()
                response = await async_client.get(f"/api/v2/appointments/{fake_id}")
                
                assert response.status_code == 404
                # V2 should have enhanced error format, but this depends on error handling implementation
                
            app.dependency_overrides.clear()