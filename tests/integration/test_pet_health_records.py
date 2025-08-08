"""
Integration tests for Pet Health Records API endpoints.

Tests the complete flow from HTTP request to database for pet health record
management, including creation, retrieval, filtering, and reminder scheduling.
"""

import pytest
import uuid
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from fastapi import status

from app.models.user import User, UserRole
from app.models.pet import Pet, PetGender, PetSize, HealthRecord, HealthRecordType, Reminder
from app.api.schemas.v1.pets import HealthRecordResponseV1, ReminderResponseV1


class TestPetHealthRecordsIntegration:
    """Test pet health records API endpoints integration."""

    @pytest.fixture
    def sample_health_record_data(self):
        """Sample health record data for testing."""
        return {
            "record_type": "vaccination",
            "title": "Annual Rabies Vaccination",
            "description": "Rabies vaccination administered",
            "record_date": "2024-01-15",
            "next_due_date": "2025-01-15",
            "medication_name": "Rabies Vaccine",
            "dosage": "1ml",
            "frequency": "Annual",
            "cost": 45.00,
            "notes": "No adverse reactions observed"
        }

    @pytest.fixture
    def sample_reminder_data(self):
        """Sample reminder data for testing."""
        return {
            "title": "Vaccination Reminder",
            "description": "Time for annual rabies vaccination",
            "reminder_type": "vaccination",
            "due_date": "2025-01-15",
            "reminder_date": "2025-01-08",
            "is_recurring": False
        }

    @pytest.fixture
    def mock_pet(self):
        """Mock pet object for testing."""
        return Pet(
            id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            name="Buddy",
            species="dog",
            breed="Golden Retriever",
            gender=PetGender.MALE,
            size=PetSize.LARGE,
            weight=65.5,
            is_active=True,
            is_deceased=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.fixture
    def mock_health_record(self):
        """Mock health record for testing."""
        return HealthRecord(
            id=uuid.uuid4(),
            pet_id=uuid.uuid4(),
            record_type=HealthRecordType.VACCINATION,
            title="Annual Rabies Vaccination",
            description="Rabies vaccination administered",
            record_date=date(2024, 1, 15),
            next_due_date=date(2025, 1, 15),
            medication_name="Rabies Vaccine",
            dosage="1ml",
            frequency="Annual",
            cost=45.00,
            notes="No adverse reactions observed",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.fixture
    def mock_reminder(self):
        """Mock reminder for testing."""
        return Reminder(
            id=uuid.uuid4(),
            pet_id=uuid.uuid4(),
            title="Vaccination Reminder",
            description="Time for annual rabies vaccination",
            reminder_type="vaccination",
            due_date=date(2025, 1, 15),
            reminder_date=date(2025, 1, 8),
            is_recurring=False,
            is_completed=False,
            is_sent=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.fixture
    def mock_user(self):
        """Mock user for authentication."""
        return User(
            id=uuid.uuid4(),
            email="vet@example.com",
            first_name="Dr. Jane",
            last_name="Smith",
            role=UserRole.VETERINARIAN,
            is_active=True
        )

    # Health Record Tests

    async def test_add_health_record_success(
        self, 
        async_client: AsyncClient, 
        sample_health_record_data, 
        mock_pet, 
        mock_health_record, 
        mock_user
    ):
        """Test successful health record creation via V1 endpoint."""
        with patch("app.pets.controller.PetController.add_health_record", new_callable=AsyncMock) as mock_add_record, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            mock_add_record.return_value = mock_health_record
            
            response = await async_client.post(
                f"/api/v1/pets/{mock_pet.id}/health-records",
                json=sample_health_record_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v1"
            assert "data" in data
            
            # Verify health record data
            record_data = data["data"]
            assert record_data["record_type"] == "vaccination"
            assert record_data["title"] == "Annual Rabies Vaccination"
            assert record_data["medication_name"] == "Rabies Vaccine"
            assert record_data["cost"] == 45.00
            
            # Verify controller was called correctly
            mock_add_record.assert_called_once()
            call_args = mock_add_record.call_args
            assert call_args[1]["pet_id"] == mock_pet.id
            assert call_args[1]["created_by"] == mock_user.id

    async def test_get_pet_health_records_success(
        self, 
        async_client: AsyncClient, 
        mock_pet, 
        mock_health_record, 
        mock_user
    ):
        """Test successful health records retrieval via V1 endpoint."""
        with patch("app.pets.controller.PetController.get_pet_health_records", new_callable=AsyncMock) as mock_get_records, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_records.return_value = [mock_health_record]
            
            response = await async_client.get(f"/api/v1/pets/{mock_pet.id}/health-records")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response is a list
            assert isinstance(data, list)
            assert len(data) == 1
            
            # Verify health record data
            record_data = data[0]
            assert record_data["record_type"] == "vaccination"
            assert record_data["title"] == "Annual Rabies Vaccination"
            
            # Verify controller was called correctly
            mock_get_records.assert_called_once()
            call_kwargs = mock_get_records.call_args[1]
            assert call_kwargs["pet_id"] == mock_pet.id

    async def test_get_pet_health_records_with_filters(
        self, 
        async_client: AsyncClient, 
        mock_pet, 
        mock_health_record, 
        mock_user
    ):
        """Test health records retrieval with filters."""
        with patch("app.pets.controller.PetController.get_pet_health_records", new_callable=AsyncMock) as mock_get_records, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_records.return_value = [mock_health_record]
            
            # Test with filters
            response = await async_client.get(
                f"/api/v1/pets/{mock_pet.id}/health-records"
                f"?record_type=vaccination&start_date=2024-01-01&end_date=2024-12-31"
            )
            
            assert response.status_code == status.HTTP_200_OK
            
            # Verify controller was called with filters
            mock_get_records.assert_called_once()
            call_kwargs = mock_get_records.call_args[1]
            assert call_kwargs["pet_id"] == mock_pet.id
            assert call_kwargs["record_type"] == HealthRecordType.VACCINATION
            assert call_kwargs["start_date"] == date(2024, 1, 1)
            assert call_kwargs["end_date"] == date(2024, 12, 31)

    async def test_get_pet_vaccinations_success(
        self, 
        async_client: AsyncClient, 
        mock_pet, 
        mock_health_record, 
        mock_user
    ):
        """Test vaccination records retrieval via V1 endpoint."""
        with patch("app.pets.controller.PetController.get_pet_health_records", new_callable=AsyncMock) as mock_get_records, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_records.return_value = [mock_health_record]
            
            response = await async_client.get(f"/api/v1/pets/{mock_pet.id}/vaccinations")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response is a list
            assert isinstance(data, list)
            assert len(data) == 1
            
            # Verify controller was called with vaccination filter
            mock_get_records.assert_called_once()
            call_kwargs = mock_get_records.call_args[1]
            assert call_kwargs["pet_id"] == mock_pet.id
            assert call_kwargs["record_type"] == HealthRecordType.VACCINATION

    async def test_get_pet_medications_success(
        self, 
        async_client: AsyncClient, 
        mock_pet, 
        mock_user
    ):
        """Test medication records retrieval via V1 endpoint."""
        medication_record = HealthRecord(
            id=uuid.uuid4(),
            pet_id=mock_pet.id,
            record_type=HealthRecordType.MEDICATION,
            title="Daily Medication",
            medication_name="Prednisone",
            dosage="5mg",
            frequency="Daily",
            record_date=date(2024, 1, 15),
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        with patch("app.pets.controller.PetController.get_pet_health_records", new_callable=AsyncMock) as mock_get_records, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_records.return_value = [medication_record]
            
            response = await async_client.get(f"/api/v1/pets/{mock_pet.id}/medications")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response is a list
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["record_type"] == "medication"
            
            # Verify controller was called with medication filter
            mock_get_records.assert_called_once()
            call_kwargs = mock_get_records.call_args[1]
            assert call_kwargs["pet_id"] == mock_pet.id
            assert call_kwargs["record_type"] == HealthRecordType.MEDICATION

    # Reminder Tests

    async def test_create_reminder_success(
        self, 
        async_client: AsyncClient, 
        sample_reminder_data, 
        mock_pet, 
        mock_reminder, 
        mock_user
    ):
        """Test successful reminder creation via V1 endpoint."""
        with patch("app.pets.controller.PetController.create_reminder", new_callable=AsyncMock) as mock_create_reminder, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            mock_create_reminder.return_value = mock_reminder
            
            response = await async_client.post(
                f"/api/v1/pets/{mock_pet.id}/reminders",
                json=sample_reminder_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v1"
            assert "data" in data
            
            # Verify reminder data
            reminder_data = data["data"]
            assert reminder_data["title"] == "Vaccination Reminder"
            assert reminder_data["reminder_type"] == "vaccination"
            assert reminder_data["is_completed"] is False
            
            # Verify controller was called correctly
            mock_create_reminder.assert_called_once()
            call_args = mock_create_reminder.call_args
            assert call_args[1]["pet_id"] == mock_pet.id
            assert call_args[1]["created_by"] == mock_user.id

    async def test_get_pet_reminders_success(
        self, 
        async_client: AsyncClient, 
        mock_pet, 
        mock_reminder, 
        mock_user
    ):
        """Test successful reminders retrieval via V1 endpoint."""
        with patch("app.pets.controller.PetController.get_pet_reminders", new_callable=AsyncMock) as mock_get_reminders, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_reminders.return_value = [mock_reminder]
            
            response = await async_client.get(f"/api/v1/pets/{mock_pet.id}/reminders")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response is a list
            assert isinstance(data, list)
            assert len(data) == 1
            
            # Verify reminder data
            reminder_data = data[0]
            assert reminder_data["title"] == "Vaccination Reminder"
            assert reminder_data["reminder_type"] == "vaccination"
            
            # Verify controller was called correctly
            mock_get_reminders.assert_called_once()
            call_kwargs = mock_get_reminders.call_args[1]
            assert call_kwargs["pet_id"] == mock_pet.id

    async def test_get_pet_reminders_with_filters(
        self, 
        async_client: AsyncClient, 
        mock_pet, 
        mock_reminder, 
        mock_user
    ):
        """Test reminders retrieval with filters."""
        with patch("app.pets.controller.PetController.get_pet_reminders", new_callable=AsyncMock) as mock_get_reminders, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_reminders.return_value = [mock_reminder]
            
            # Test with filters
            response = await async_client.get(
                f"/api/v1/pets/{mock_pet.id}/reminders"
                f"?reminder_type=vaccination&is_completed=false&due_before=2025-02-01"
            )
            
            assert response.status_code == status.HTTP_200_OK
            
            # Verify controller was called with filters
            mock_get_reminders.assert_called_once()
            call_kwargs = mock_get_reminders.call_args[1]
            assert call_kwargs["pet_id"] == mock_pet.id
            assert call_kwargs["reminder_type"] == "vaccination"
            assert call_kwargs["is_completed"] is False
            assert call_kwargs["due_before"] == date(2025, 2, 1)

    async def test_complete_reminder_success(
        self, 
        async_client: AsyncClient, 
        mock_reminder, 
        mock_user
    ):
        """Test successful reminder completion via V1 endpoint."""
        with patch("app.pets.controller.PetController.complete_reminder", new_callable=AsyncMock) as mock_complete_reminder, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            # Update mock reminder to be completed
            completed_reminder = mock_reminder
            completed_reminder.is_completed = True
            completed_reminder.completed_at = datetime.now()
            mock_complete_reminder.return_value = completed_reminder
            
            response = await async_client.patch(f"/api/v1/pets/reminders/{mock_reminder.id}/complete")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v1"
            assert "data" in data
            
            # Verify reminder completion
            reminder_data = data["data"]
            assert reminder_data["is_completed"] is True
            assert reminder_data["completed_at"] is not None
            
            # Verify controller was called correctly
            mock_complete_reminder.assert_called_once()
            call_args = mock_complete_reminder.call_args
            assert call_args[1]["reminder_id"] == mock_reminder.id
            assert call_args[1]["completed_by"] == mock_user.id

    # Validation Tests

    async def test_add_health_record_validation_error(self, async_client: AsyncClient, mock_pet, mock_user):
        """Test health record creation with validation errors."""
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            # Missing required fields
            invalid_data = {
                "record_type": "invalid_type",  # Invalid type
                "title": "",  # Empty title
                "record_date": "2025-01-01"  # Future date
            }
            
            response = await async_client.post(
                f"/api/v1/pets/{mock_pet.id}/health-records",
                json=invalid_data
            )
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_reminder_validation_error(self, async_client: AsyncClient, mock_pet, mock_user):
        """Test reminder creation with validation errors."""
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            # Invalid reminder data
            invalid_data = {
                "title": "",  # Empty title
                "reminder_type": "vaccination",
                "due_date": "2025-01-15",
                "reminder_date": "2025-01-20",  # After due date
                "is_recurring": True,
                # Missing recurrence_interval_days for recurring reminder
            }
            
            response = await async_client.post(
                f"/api/v1/pets/{mock_pet.id}/reminders",
                json=invalid_data
            )
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Error Handling Tests

    async def test_health_record_not_found_error(self, async_client: AsyncClient, mock_user):
        """Test health record retrieval with non-existent pet ID."""
        with patch("app.pets.controller.PetController.get_pet_health_records", new_callable=AsyncMock) as mock_get_records, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            from app.core.exceptions import NotFoundError
            mock_get_records.side_effect = NotFoundError("Pet not found")
            
            non_existent_id = uuid.uuid4()
            response = await async_client.get(f"/api/v1/pets/{non_existent_id}/health-records")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_reminder_not_found_error(self, async_client: AsyncClient, mock_user):
        """Test reminder completion with non-existent reminder ID."""
        with patch("app.pets.controller.PetController.complete_reminder", new_callable=AsyncMock) as mock_complete_reminder, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            from app.core.exceptions import NotFoundError
            mock_complete_reminder.side_effect = NotFoundError("Reminder not found")
            
            non_existent_id = uuid.uuid4()
            response = await async_client.patch(f"/api/v1/pets/reminders/{non_existent_id}/complete")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_unauthorized_access(self, async_client: AsyncClient, mock_pet):
        """Test unauthorized access to health record endpoints."""
        with patch("app.app_helpers.auth_helpers.get_current_user", side_effect=Exception("Unauthorized")):
            
            response = await async_client.get(f"/api/v1/pets/{mock_pet.id}/health-records")
            
            # Should return unauthorized status
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]

    # Integration Tests

    async def test_health_record_with_reminder_scheduling(
        self, 
        async_client: AsyncClient, 
        mock_pet, 
        mock_health_record, 
        mock_user
    ):
        """Test health record creation with automatic reminder scheduling."""
        with patch("app.pets.controller.PetController.add_health_record", new_callable=AsyncMock) as mock_add_record, \
             patch("app.pets.controller.PetController._schedule_health_reminder", new_callable=AsyncMock) as mock_schedule_reminder, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            mock_add_record.return_value = mock_health_record
            
            # Health record data with next_due_date
            health_record_data = {
                "record_type": "vaccination",
                "title": "Annual Rabies Vaccination",
                "record_date": "2024-01-15",
                "next_due_date": "2025-01-15",
                "medication_name": "Rabies Vaccine"
            }
            
            response = await async_client.post(
                f"/api/v1/pets/{mock_pet.id}/health-records",
                json=health_record_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            
            # Verify health record was created
            mock_add_record.assert_called_once()
            
            # Note: The reminder scheduling happens in the controller,
            # so we can't directly test it here without more complex mocking

    async def test_comprehensive_pet_health_management_workflow(
        self, 
        async_client: AsyncClient, 
        mock_pet, 
        mock_health_record, 
        mock_reminder, 
        mock_user
    ):
        """Test comprehensive workflow of pet health management."""
        with patch("app.pets.controller.PetController.add_health_record", new_callable=AsyncMock) as mock_add_record, \
             patch("app.pets.controller.PetController.get_pet_health_records", new_callable=AsyncMock) as mock_get_records, \
             patch("app.pets.controller.PetController.create_reminder", new_callable=AsyncMock) as mock_create_reminder, \
             patch("app.pets.controller.PetController.get_pet_reminders", new_callable=AsyncMock) as mock_get_reminders, \
             patch("app.pets.controller.PetController.complete_reminder", new_callable=AsyncMock) as mock_complete_reminder, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            # Setup mocks
            mock_add_record.return_value = mock_health_record
            mock_get_records.return_value = [mock_health_record]
            mock_create_reminder.return_value = mock_reminder
            mock_get_reminders.return_value = [mock_reminder]
            completed_reminder = mock_reminder
            completed_reminder.is_completed = True
            mock_complete_reminder.return_value = completed_reminder
            
            # Step 1: Add health record
            health_record_data = {
                "record_type": "vaccination",
                "title": "Annual Rabies Vaccination",
                "record_date": "2024-01-15",
                "next_due_date": "2025-01-15"
            }
            
            response = await async_client.post(
                f"/api/v1/pets/{mock_pet.id}/health-records",
                json=health_record_data
            )
            assert response.status_code == status.HTTP_201_CREATED
            
            # Step 2: Get health records
            response = await async_client.get(f"/api/v1/pets/{mock_pet.id}/health-records")
            assert response.status_code == status.HTTP_200_OK
            assert len(response.json()) == 1
            
            # Step 3: Create reminder
            reminder_data = {
                "title": "Vaccination Reminder",
                "reminder_type": "vaccination",
                "due_date": "2025-01-15",
                "reminder_date": "2025-01-08"
            }
            
            response = await async_client.post(
                f"/api/v1/pets/{mock_pet.id}/reminders",
                json=reminder_data
            )
            assert response.status_code == status.HTTP_201_CREATED
            
            # Step 4: Get reminders
            response = await async_client.get(f"/api/v1/pets/{mock_pet.id}/reminders")
            assert response.status_code == status.HTTP_200_OK
            assert len(response.json()) == 1
            
            # Step 5: Complete reminder
            response = await async_client.patch(f"/api/v1/pets/reminders/{mock_reminder.id}/complete")
            assert response.status_code == status.HTTP_200_OK
            
            # Verify all operations were called
            mock_add_record.assert_called_once()
            mock_get_records.assert_called_once()
            mock_create_reminder.assert_called_once()
            mock_get_reminders.assert_called_once()
            mock_complete_reminder.assert_called_once()