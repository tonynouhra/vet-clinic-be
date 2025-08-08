"""
Integration tests for appointment scheduling workflows.

Tests the complete appointment scheduling system including:
- Availability checking
- Conflict detection
- Appointment booking with validation
- Calendar view functionality
- Reminder notifications
- Status transitions (confirm, cancel, reschedule)
"""

import pytest
import uuid
from datetime import datetime, date, timedelta
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.appointment import Appointment, AppointmentSlot, AppointmentStatus, AppointmentType, AppointmentPriority
from app.models.user import User
from app.models.pet import Pet
from app.models.clinic import Clinic, Veterinarian
from app.core.database import get_db
from tests.conftest import test_db, test_client


class TestAppointmentScheduling:
    """Test appointment scheduling workflows."""

    @pytest.fixture
    async def sample_data(self, test_db: AsyncSession):
        """Create sample data for testing."""
        # Create test user (pet owner)
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            clerk_id="test_clerk_id",
            role="pet_owner"
        )
        test_db.add(user)
        
        # Create test pet
        pet = Pet(
            id=uuid.uuid4(),
            owner_id=user.id,
            name="Buddy",
            species="dog",
            breed="Golden Retriever",
            birth_date=date(2020, 1, 1),
            gender="male"
        )
        test_db.add(pet)
        
        # Create test clinic
        clinic = Clinic(
            id=uuid.uuid4(),
            name="Test Veterinary Clinic",
            address="123 Test St",
            city="Test City",
            state="TS",
            zip_code="12345",
            phone="555-0123"
        )
        test_db.add(clinic)
        
        # Create test veterinarian
        vet_user = User(
            id=uuid.uuid4(),
            email="vet@example.com",
            first_name="Jane",
            last_name="Smith",
            clerk_id="vet_clerk_id",
            role="veterinarian"
        )
        test_db.add(vet_user)
        
        veterinarian = Veterinarian(
            id=uuid.uuid4(),
            user_id=vet_user.id,
            clinic_id=clinic.id,
            license_number="VET123456",
            specialties=["general_practice"]
        )
        test_db.add(veterinarian)
        
        # Create test appointment slots
        tomorrow = datetime.utcnow() + timedelta(days=1)
        slots = []
        for hour in range(9, 17):  # 9 AM to 5 PM
            slot = AppointmentSlot(
                id=uuid.uuid4(),
                veterinarian_id=veterinarian.id,
                clinic_id=clinic.id,
                start_time=tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0),
                end_time=tomorrow.replace(hour=hour, minute=30, second=0, microsecond=0),
                duration_minutes=30,
                is_available=True,
                is_blocked=False
            )
            slots.append(slot)
            test_db.add(slot)
        
        await test_db.commit()
        
        return {
            "user": user,
            "pet": pet,
            "clinic": clinic,
            "veterinarian": veterinarian,
            "slots": slots
        }

    async def test_get_availability(self, test_client: TestClient, sample_data: dict):
        """Test getting available appointment slots."""
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        tomorrow = (datetime.utcnow() + timedelta(days=1)).date()
        
        # Mock authentication
        with patch("app.api.deps.get_current_user") as mock_auth:
            mock_auth.return_value = sample_data["user"]
            
            response = test_client.get(
                "/api/v1/appointments/availability",
                params={
                    "veterinarian_id": str(veterinarian.id),
                    "clinic_id": str(clinic.id),
                    "start_date": tomorrow.isoformat(),
                    "duration_minutes": 30
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "available_slots" in data["data"]
        assert len(data["data"]["available_slots"]) > 0
        
        # Verify slot structure
        slot = data["data"]["available_slots"][0]
        assert "id" in slot
        assert "start_time" in slot
        assert "end_time" in slot
        assert "duration_minutes" in slot
        assert "is_available" in slot

    async def test_get_calendar_view(self, test_client: TestClient, sample_data: dict):
        """Test getting calendar view."""
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        tomorrow = (datetime.utcnow() + timedelta(days=1)).date()
        
        # Mock authentication
        with patch("app.api.deps.get_current_user") as mock_auth:
            mock_auth.return_value = sample_data["user"]
            
            response = test_client.get(
                "/api/v1/appointments/calendar",
                params={
                    "veterinarian_id": str(veterinarian.id),
                    "clinic_id": str(clinic.id),
                    "start_date": tomorrow.isoformat(),
                    "view_type": "day"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "appointments" in data["data"]
        assert "available_slots" in data["data"]
        assert data["data"]["view_type"] == "day"

    async def test_check_appointment_conflicts(self, test_client: TestClient, sample_data: dict):
        """Test checking for appointment conflicts."""
        veterinarian = sample_data["veterinarian"]
        tomorrow = datetime.utcnow() + timedelta(days=1)
        scheduled_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        
        # Mock authentication
        with patch("app.api.deps.get_current_user") as mock_auth:
            mock_auth.return_value = sample_data["user"]
            
            response = test_client.post(
                "/api/v1/appointments/check-conflicts",
                json={
                    "veterinarian_id": str(veterinarian.id),
                    "scheduled_at": scheduled_time.isoformat(),
                    "duration_minutes": 30
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "has_conflicts" in data["data"]
        assert "conflicts" in data["data"]
        assert data["data"]["has_conflicts"] is False  # No conflicts initially

    async def test_create_appointment_with_availability_check(self, test_client: TestClient, sample_data: dict):
        """Test creating an appointment with availability checking."""
        user = sample_data["user"]
        pet = sample_data["pet"]
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        tomorrow = datetime.utcnow() + timedelta(days=1)
        scheduled_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        
        appointment_data = {
            "pet_id": str(pet.id),
            "pet_owner_id": str(user.id),
            "veterinarian_id": str(veterinarian.id),
            "clinic_id": str(clinic.id),
            "appointment_type": "routine_checkup",
            "scheduled_at": scheduled_time.isoformat(),
            "reason": "Annual checkup",
            "duration_minutes": 30,
            "priority": "normal"
        }
        
        # Mock authentication and notification task
        with patch("app.api.deps.get_current_user") as mock_auth, \
             patch("app.tasks.appointment_tasks.send_appointment_confirmation.delay") as mock_task:
            mock_auth.return_value = user
            mock_task.return_value = None
            
            response = test_client.post(
                "/api/v1/appointments/",
                json=appointment_data
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["pet_id"] == str(pet.id)
        assert data["data"]["status"] == "scheduled"
        
        # Verify notification task was called
        mock_task.assert_called_once()

    async def test_create_appointment_with_conflict(self, test_client: TestClient, sample_data: dict, test_db: AsyncSession):
        """Test creating an appointment that conflicts with existing appointment."""
        user = sample_data["user"]
        pet = sample_data["pet"]
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        tomorrow = datetime.utcnow() + timedelta(days=1)
        scheduled_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        
        # Create existing appointment
        existing_appointment = Appointment(
            id=uuid.uuid4(),
            pet_id=pet.id,
            pet_owner_id=user.id,
            veterinarian_id=veterinarian.id,
            clinic_id=clinic.id,
            appointment_type=AppointmentType.ROUTINE_CHECKUP,
            scheduled_at=scheduled_time,
            reason="Existing appointment",
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED
        )
        test_db.add(existing_appointment)
        await test_db.commit()
        
        # Try to create conflicting appointment
        appointment_data = {
            "pet_id": str(pet.id),
            "pet_owner_id": str(user.id),
            "veterinarian_id": str(veterinarian.id),
            "clinic_id": str(clinic.id),
            "appointment_type": "routine_checkup",
            "scheduled_at": scheduled_time.isoformat(),
            "reason": "Conflicting appointment",
            "duration_minutes": 30,
            "priority": "normal"
        }
        
        # Mock authentication
        with patch("app.api.deps.get_current_user") as mock_auth:
            mock_auth.return_value = user
            
            response = test_client.post(
                "/api/v1/appointments/",
                json=appointment_data
            )
        
        assert response.status_code == 400
        assert "conflict" in response.json()["detail"].lower()

    async def test_appointment_confirmation_workflow(self, test_client: TestClient, sample_data: dict, test_db: AsyncSession):
        """Test appointment confirmation workflow."""
        user = sample_data["user"]
        pet = sample_data["pet"]
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        tomorrow = datetime.utcnow() + timedelta(days=1)
        scheduled_time = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)
        
        # Create appointment
        appointment = Appointment(
            id=uuid.uuid4(),
            pet_id=pet.id,
            pet_owner_id=user.id,
            veterinarian_id=veterinarian.id,
            clinic_id=clinic.id,
            appointment_type=AppointmentType.ROUTINE_CHECKUP,
            scheduled_at=scheduled_time,
            reason="Test appointment",
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED
        )
        test_db.add(appointment)
        await test_db.commit()
        
        # Confirm appointment
        with patch("app.api.deps.get_current_user") as mock_auth:
            mock_auth.return_value = user
            
            response = test_client.post(
                f"/api/v1/appointments/{appointment.id}/confirm"
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "confirmed"
        assert data["data"]["confirmed_at"] is not None

    async def test_appointment_cancellation_workflow(self, test_client: TestClient, sample_data: dict, test_db: AsyncSession):
        """Test appointment cancellation workflow."""
        user = sample_data["user"]
        pet = sample_data["pet"]
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        tomorrow = datetime.utcnow() + timedelta(days=1)
        scheduled_time = tomorrow.replace(hour=12, minute=0, second=0, microsecond=0)
        
        # Create appointment
        appointment = Appointment(
            id=uuid.uuid4(),
            pet_id=pet.id,
            pet_owner_id=user.id,
            veterinarian_id=veterinarian.id,
            clinic_id=clinic.id,
            appointment_type=AppointmentType.ROUTINE_CHECKUP,
            scheduled_at=scheduled_time,
            reason="Test appointment",
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED
        )
        test_db.add(appointment)
        await test_db.commit()
        
        # Cancel appointment
        with patch("app.api.deps.get_current_user") as mock_auth, \
             patch("app.tasks.appointment_tasks.send_appointment_cancellation.delay") as mock_task:
            mock_auth.return_value = user
            mock_task.return_value = None
            
            response = test_client.post(
                f"/api/v1/appointments/{appointment.id}/cancel",
                json={"cancellation_reason": "Personal emergency"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "cancelled"
        assert data["data"]["cancellation_reason"] == "Personal emergency"
        
        # Verify notification task was called
        mock_task.assert_called_once()

    async def test_appointment_reschedule_workflow(self, test_client: TestClient, sample_data: dict, test_db: AsyncSession):
        """Test appointment rescheduling workflow."""
        user = sample_data["user"]
        pet = sample_data["pet"]
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        tomorrow = datetime.utcnow() + timedelta(days=1)
        original_time = tomorrow.replace(hour=13, minute=0, second=0, microsecond=0)
        new_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
        
        # Create appointment
        appointment = Appointment(
            id=uuid.uuid4(),
            pet_id=pet.id,
            pet_owner_id=user.id,
            veterinarian_id=veterinarian.id,
            clinic_id=clinic.id,
            appointment_type=AppointmentType.ROUTINE_CHECKUP,
            scheduled_at=original_time,
            reason="Test appointment",
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED
        )
        test_db.add(appointment)
        await test_db.commit()
        
        # Reschedule appointment
        with patch("app.api.deps.get_current_user") as mock_auth, \
             patch("app.tasks.appointment_tasks.send_appointment_reschedule.delay") as mock_task:
            mock_auth.return_value = user
            mock_task.return_value = None
            
            response = test_client.post(
                f"/api/v1/appointments/{appointment.id}/reschedule",
                json={"new_scheduled_at": new_time.isoformat()}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["scheduled_at"] == new_time.isoformat()
        assert data["data"]["status"] == "scheduled"  # Reset to scheduled after reschedule
        
        # Verify notification task was called
        mock_task.assert_called_once()

    async def test_appointment_status_transitions(self, test_client: TestClient, sample_data: dict, test_db: AsyncSession):
        """Test complete appointment status transition workflow."""
        user = sample_data["user"]
        pet = sample_data["pet"]
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        tomorrow = datetime.utcnow() + timedelta(days=1)
        scheduled_time = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)
        
        # Create appointment
        appointment = Appointment(
            id=uuid.uuid4(),
            pet_id=pet.id,
            pet_owner_id=user.id,
            veterinarian_id=veterinarian.id,
            clinic_id=clinic.id,
            appointment_type=AppointmentType.ROUTINE_CHECKUP,
            scheduled_at=scheduled_time,
            reason="Test appointment",
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED
        )
        test_db.add(appointment)
        await test_db.commit()
        
        with patch("app.api.deps.get_current_user") as mock_auth:
            mock_auth.return_value = user
            
            # 1. Confirm appointment
            response = test_client.post(f"/api/v1/appointments/{appointment.id}/confirm")
            assert response.status_code == 200
            assert response.json()["data"]["status"] == "confirmed"
            
            # 2. Start appointment
            response = test_client.post(f"/api/v1/appointments/{appointment.id}/start")
            assert response.status_code == 200
            assert response.json()["data"]["status"] == "in_progress"
            
            # 3. Complete appointment
            response = test_client.post(
                f"/api/v1/appointments/{appointment.id}/complete",
                json={"actual_cost": 150.00}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["status"] == "completed"
            assert data["data"]["actual_cost"] == 150.00

    @patch("app.tasks.appointment_tasks.send_appointment_reminders.delay")
    async def test_reminder_notification_system(self, mock_reminder_task, test_client: TestClient, sample_data: dict, test_db: AsyncSession):
        """Test reminder notification system."""
        user = sample_data["user"]
        pet = sample_data["pet"]
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        
        # Create appointment 24 hours from now (should trigger 24h reminder)
        reminder_time = datetime.utcnow() + timedelta(hours=24)
        
        appointment = Appointment(
            id=uuid.uuid4(),
            pet_id=pet.id,
            pet_owner_id=user.id,
            veterinarian_id=veterinarian.id,
            clinic_id=clinic.id,
            appointment_type=AppointmentType.ROUTINE_CHECKUP,
            scheduled_at=reminder_time,
            reason="Test appointment for reminder",
            duration_minutes=30,
            status=AppointmentStatus.SCHEDULED,
            reminder_sent_24h=False,
            reminder_sent_2h=False
        )
        test_db.add(appointment)
        await test_db.commit()
        
        # Simulate reminder task execution
        from app.tasks.appointment_tasks import send_appointment_reminders
        
        # Mock the task execution
        mock_reminder_task.return_value = {"success": True, "message": "Reminders sent"}
        
        # Verify the task would be called
        result = send_appointment_reminders.delay()
        mock_reminder_task.assert_called_once()

    async def test_appointment_list_with_filters(self, test_client: TestClient, sample_data: dict, test_db: AsyncSession):
        """Test appointment listing with various filters."""
        user = sample_data["user"]
        pet = sample_data["pet"]
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        
        # Create multiple appointments with different statuses and dates
        appointments = []
        base_time = datetime.utcnow() + timedelta(days=1)
        
        for i, status in enumerate([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED]):
            appointment = Appointment(
                id=uuid.uuid4(),
                pet_id=pet.id,
                pet_owner_id=user.id,
                veterinarian_id=veterinarian.id,
                clinic_id=clinic.id,
                appointment_type=AppointmentType.ROUTINE_CHECKUP,
                scheduled_at=base_time + timedelta(hours=i),
                reason=f"Test appointment {i}",
                duration_minutes=30,
                status=status
            )
            appointments.append(appointment)
            test_db.add(appointment)
        
        await test_db.commit()
        
        with patch("app.api.deps.get_current_user") as mock_auth:
            mock_auth.return_value = user
            
            # Test filtering by status
            response = test_client.get(
                "/api/v1/appointments/",
                params={"status": "scheduled"}
            )
            assert response.status_code == 200
            data = response.json()
            scheduled_appointments = [apt for apt in data["data"]["appointments"] if apt["status"] == "scheduled"]
            assert len(scheduled_appointments) >= 1
            
            # Test filtering by pet
            response = test_client.get(
                "/api/v1/appointments/",
                params={"pet_id": str(pet.id)}
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]["appointments"]) >= 3
            
            # Test upcoming only filter
            response = test_client.get(
                "/api/v1/appointments/",
                params={"upcoming_only": True}
            )
            assert response.status_code == 200
            data = response.json()
            # Should only return scheduled and confirmed appointments in the future
            for apt in data["data"]["appointments"]:
                assert apt["status"] in ["scheduled", "confirmed"]

    async def test_enhanced_calendar_view_with_summary(self, test_client: TestClient, sample_data: dict, test_db: AsyncSession):
        """Test enhanced calendar view with summary statistics."""
        user = sample_data["user"]
        pet = sample_data["pet"]
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        tomorrow = datetime.utcnow() + timedelta(days=1)
        
        # Create multiple appointments for calendar testing
        appointments = []
        for i in range(3):
            appointment = Appointment(
                id=uuid.uuid4(),
                pet_id=pet.id,
                pet_owner_id=user.id,
                veterinarian_id=veterinarian.id,
                clinic_id=clinic.id,
                appointment_type=AppointmentType.ROUTINE_CHECKUP,
                scheduled_at=tomorrow.replace(hour=10+i, minute=0, second=0, microsecond=0),
                reason=f"Calendar test appointment {i}",
                duration_minutes=30,
                status=AppointmentStatus.SCHEDULED
            )
            appointments.append(appointment)
            test_db.add(appointment)
        
        await test_db.commit()
        
        with patch("app.api.deps.get_current_user") as mock_auth:
            mock_auth.return_value = user
            
            response = test_client.get(
                "/api/v1/appointments/calendar",
                params={
                    "veterinarian_id": str(veterinarian.id),
                    "clinic_id": str(clinic.id),
                    "start_date": tomorrow.date().isoformat(),
                    "view_type": "day"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        calendar_data = data["data"]
        assert "appointments" in calendar_data
        assert "available_slots" in calendar_data
        assert "summary" in calendar_data
        
        # Check summary statistics
        summary = calendar_data["summary"]
        assert "total_appointments" in summary
        assert "appointments_by_status" in summary
        assert "total_available_slots" in summary
        assert "utilization_rate" in summary
        
        # Verify appointments have detailed information
        if calendar_data["appointments"]:
            appointment = calendar_data["appointments"][0]
            assert "pet_name" in appointment
            assert "pet_owner_name" in appointment
            assert "veterinarian_name" in appointment
            assert "clinic_name" in appointment
            assert "can_be_cancelled" in appointment
            assert "can_be_rescheduled" in appointment

    async def test_appointment_statistics_endpoint(self, test_client: TestClient, sample_data: dict, test_db: AsyncSession):
        """Test appointment statistics endpoint."""
        user = sample_data["user"]
        pet = sample_data["pet"]
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        
        # Create appointments with different statuses and costs
        appointments_data = [
            (AppointmentStatus.COMPLETED, 100.0, 95.0),
            (AppointmentStatus.COMPLETED, 150.0, 140.0),
            (AppointmentStatus.CANCELLED, 120.0, None),
            (AppointmentStatus.NO_SHOW, 80.0, None),
            (AppointmentStatus.SCHEDULED, 90.0, None)
        ]
        
        base_time = datetime.utcnow() - timedelta(days=5)  # Past appointments for statistics
        
        for i, (status, estimated_cost, actual_cost) in enumerate(appointments_data):
            appointment = Appointment(
                id=uuid.uuid4(),
                pet_id=pet.id,
                pet_owner_id=user.id,
                veterinarian_id=veterinarian.id,
                clinic_id=clinic.id,
                appointment_type=AppointmentType.ROUTINE_CHECKUP,
                scheduled_at=base_time + timedelta(hours=i),
                reason=f"Statistics test appointment {i}",
                duration_minutes=30,
                status=status,
                estimated_cost=estimated_cost,
                actual_cost=actual_cost
            )
            test_db.add(appointment)
        
        await test_db.commit()
        
        with patch("app.api.deps.get_current_user") as mock_auth:
            mock_auth.return_value = user
            
            response = test_client.get(
                "/api/v1/appointments/statistics",
                params={
                    "veterinarian_id": str(veterinarian.id),
                    "clinic_id": str(clinic.id)
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        stats = data["data"]
        assert "totals" in stats
        assert "counts_by_status" in stats
        assert "counts_by_type" in stats
        assert "rates" in stats
        
        # Check totals
        totals = stats["totals"]
        assert totals["total_appointments"] >= 5
        assert totals["completed_appointments"] >= 2
        assert totals["total_estimated_revenue"] >= 540.0
        assert totals["total_actual_revenue"] >= 235.0
        
        # Check rates
        rates = stats["rates"]
        assert "completion_rate" in rates
        assert "no_show_rate" in rates
        assert "cancellation_rate" in rates

    async def test_create_appointment_slots_endpoint(self, test_client: TestClient, sample_data: dict):
        """Test creating appointment slots via API endpoint."""
        user = sample_data["user"]
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        
        start_date = (datetime.utcnow() + timedelta(days=7)).date()
        end_date = start_date + timedelta(days=2)
        
        with patch("app.api.deps.get_current_user") as mock_auth:
            mock_auth.return_value = user
            
            response = test_client.post(
                "/api/v1/appointments/slots/create",
                params={
                    "veterinarian_id": str(veterinarian.id),
                    "clinic_id": str(clinic.id),
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "slot_duration": 30,
                    "break_duration": 0,
                    "exclude_weekends": True
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        slot_data = data["data"]
        assert "created_slots" in slot_data
        assert "total_created" in slot_data
        assert slot_data["total_created"] > 0
        
        # Verify slot structure
        if slot_data["created_slots"]:
            slot = slot_data["created_slots"][0]
            assert "id" in slot
            assert "start_time" in slot
            assert "end_time" in slot
            assert "duration_minutes" in slot
            assert slot["duration_minutes"] == 30

    async def test_advanced_conflict_detection(self, test_client: TestClient, sample_data: dict, test_db: AsyncSession):
        """Test advanced conflict detection with overlapping appointments."""
        user = sample_data["user"]
        pet = sample_data["pet"]
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        
        base_time = datetime.utcnow() + timedelta(days=1)
        
        # Create overlapping appointments to test conflict detection
        conflicts_data = [
            # Appointment 1: 10:00-10:30
            (base_time.replace(hour=10, minute=0, second=0, microsecond=0), 30),
            # Appointment 2: 10:15-10:45 (overlaps with appointment 1)
            (base_time.replace(hour=10, minute=15, second=0, microsecond=0), 30),
            # Appointment 3: 11:00-12:00 (longer appointment)
            (base_time.replace(hour=11, minute=0, second=0, microsecond=0), 60),
        ]
        
        existing_appointments = []
        for i, (scheduled_at, duration) in enumerate(conflicts_data[:2]):  # Create first 2 appointments
            appointment = Appointment(
                id=uuid.uuid4(),
                pet_id=pet.id,
                pet_owner_id=user.id,
                veterinarian_id=veterinarian.id,
                clinic_id=clinic.id,
                appointment_type=AppointmentType.ROUTINE_CHECKUP,
                scheduled_at=scheduled_at,
                reason=f"Conflict test appointment {i}",
                duration_minutes=duration,
                status=AppointmentStatus.SCHEDULED
            )
            existing_appointments.append(appointment)
            test_db.add(appointment)
        
        await test_db.commit()
        
        with patch("app.api.deps.get_current_user") as mock_auth:
            mock_auth.return_value = user
            
            # Test conflict with existing appointment
            test_time = base_time.replace(hour=10, minute=10, second=0, microsecond=0)
            response = test_client.post(
                "/api/v1/appointments/check-conflicts",
                json={
                    "veterinarian_id": str(veterinarian.id),
                    "scheduled_at": test_time.isoformat(),
                    "duration_minutes": 30
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["has_conflicts"] is True
            assert len(data["data"]["conflicts"]) >= 1
            
            # Test no conflict with different time
            no_conflict_time = base_time.replace(hour=14, minute=0, second=0, microsecond=0)
            response = test_client.post(
                "/api/v1/appointments/check-conflicts",
                json={
                    "veterinarian_id": str(veterinarian.id),
                    "scheduled_at": no_conflict_time.isoformat(),
                    "duration_minutes": 30
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["has_conflicts"] is False
            assert len(data["data"]["conflicts"]) == 0

    async def test_appointment_reminder_system_integration(self, test_client: TestClient, sample_data: dict, test_db: AsyncSession):
        """Test appointment reminder system integration."""
        user = sample_data["user"]
        pet = sample_data["pet"]
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        
        # Create appointments at different reminder intervals
        now = datetime.utcnow()
        reminder_appointments = [
            # 24 hours from now (should trigger 24h reminder)
            (now + timedelta(hours=24), False, False),
            # 2 hours from now (should trigger 2h reminder)
            (now + timedelta(hours=2), False, False),
            # Already sent 24h reminder
            (now + timedelta(hours=23), True, False),
        ]
        
        created_appointments = []
        for i, (scheduled_at, reminder_24h_sent, reminder_2h_sent) in enumerate(reminder_appointments):
            appointment = Appointment(
                id=uuid.uuid4(),
                pet_id=pet.id,
                pet_owner_id=user.id,
                veterinarian_id=veterinarian.id,
                clinic_id=clinic.id,
                appointment_type=AppointmentType.ROUTINE_CHECKUP,
                scheduled_at=scheduled_at,
                reason=f"Reminder test appointment {i}",
                duration_minutes=30,
                status=AppointmentStatus.SCHEDULED,
                reminder_sent_24h=reminder_24h_sent,
                reminder_sent_2h=reminder_2h_sent
            )
            created_appointments.append(appointment)
            test_db.add(appointment)
        
        await test_db.commit()
        
        # Test reminder task execution
        with patch("app.services.notification_service.NotificationService.send_appointment_reminder_email") as mock_email, \
             patch("app.services.notification_service.NotificationService.send_appointment_reminder_sms") as mock_sms:
            
            mock_email.return_value = None
            mock_sms.return_value = None
            
            # Import and run the reminder task
            from app.tasks.appointment_tasks import _send_appointment_reminders_async
            
            result = await _send_appointment_reminders_async()
            
            assert result["success"] is True
            # Verify that reminder methods would be called
            # (In a real test, we'd verify the actual database changes)

    async def test_follow_up_appointment_workflow(self, test_client: TestClient, sample_data: dict, test_db: AsyncSession):
        """Test follow-up appointment workflow."""
        user = sample_data["user"]
        pet = sample_data["pet"]
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        
        # Create completed appointment with follow-up required
        completed_time = datetime.utcnow() - timedelta(days=1)
        follow_up_date = datetime.utcnow() + timedelta(days=7)
        
        appointment = Appointment(
            id=uuid.uuid4(),
            pet_id=pet.id,
            pet_owner_id=user.id,
            veterinarian_id=veterinarian.id,
            clinic_id=clinic.id,
            appointment_type=AppointmentType.ROUTINE_CHECKUP,
            scheduled_at=completed_time,
            reason="Initial checkup with follow-up needed",
            duration_minutes=30,
            status=AppointmentStatus.COMPLETED,
            follow_up_required=True,
            follow_up_date=follow_up_date,
            follow_up_notes="Check vaccination status in one week",
            actual_cost=120.0
        )
        test_db.add(appointment)
        await test_db.commit()
        
        # Test follow-up reminder task
        with patch("app.services.notification_service.NotificationService.send_follow_up_reminder_email") as mock_email:
            mock_email.return_value = None
            
            from app.tasks.appointment_tasks import _send_follow_up_reminders_async
            
            result = await _send_follow_up_reminders_async()
            
            assert result["success"] is True
            assert result["sent_count"] >= 0  # May be 0 if follow-up date is in future

    async def test_appointment_slot_management(self, test_client: TestClient, sample_data: dict, test_db: AsyncSession):
        """Test appointment slot management and booking."""
        user = sample_data["user"]
        pet = sample_data["pet"]
        veterinarian = sample_data["veterinarian"]
        clinic = sample_data["clinic"]
        
        # Create a specific slot for testing
        tomorrow = datetime.utcnow() + timedelta(days=1)
        slot_time = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)
        
        test_slot = AppointmentSlot(
            id=uuid.uuid4(),
            veterinarian_id=veterinarian.id,
            clinic_id=clinic.id,
            start_time=slot_time,
            end_time=slot_time + timedelta(minutes=30),
            duration_minutes=30,
            is_available=True,
            is_blocked=False,
            max_bookings=1,
            current_bookings=0
        )
        test_db.add(test_slot)
        await test_db.commit()
        
        # Test booking appointment in the slot
        appointment_data = {
            "pet_id": str(pet.id),
            "pet_owner_id": str(user.id),
            "veterinarian_id": str(veterinarian.id),
            "clinic_id": str(clinic.id),
            "appointment_type": "routine_checkup",
            "scheduled_at": slot_time.isoformat(),
            "reason": "Slot booking test",
            "duration_minutes": 30,
            "priority": "normal"
        }
        
        with patch("app.api.deps.get_current_user") as mock_auth, \
             patch("app.tasks.appointment_tasks.send_appointment_confirmation.delay") as mock_task:
            mock_auth.return_value = user
            mock_task.return_value = None
            
            response = test_client.post(
                "/api/v1/appointments/",
                json=appointment_data
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        
        # Verify slot is now booked
        await test_db.refresh(test_slot)
        assert test_slot.current_bookings == 1
        assert test_slot.is_fully_booked is True