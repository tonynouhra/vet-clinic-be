"""
Unit tests for Pet Service.

Tests the core business logic and data access methods for pet-related operations,
including health records, reminders, and automated scheduling functionality.
"""

import pytest
import uuid
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.pets.services import PetService
from app.models.pet import Pet, PetGender, PetSize, HealthRecord, HealthRecordType, Reminder
from app.core.exceptions import VetClinicException, NotFoundError, ValidationError


class TestPetService:
    """Test pet service business logic."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def pet_service(self, mock_db_session):
        """Pet service instance with mocked database."""
        return PetService(mock_db_session)

    @pytest.fixture
    def sample_pet(self):
        """Sample pet for testing."""
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
    def sample_health_record(self):
        """Sample health record for testing."""
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
            cost=45.00,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.fixture
    def sample_reminder(self):
        """Sample reminder for testing."""
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

    # Pet CRUD Tests

    async def test_create_pet_success(self, pet_service, mock_db_session):
        """Test successful pet creation."""
        # Setup
        owner_id = uuid.uuid4()
        pet_data = {
            "name": "Buddy",
            "species": "dog",
            "breed": "Golden Retriever",
            "gender": PetGender.MALE,
            "size": PetSize.LARGE,
            "weight": 65.5
        }
        
        # Mock database operations
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        
        # Execute
        result = await pet_service.create_pet(
            owner_id=owner_id,
            **pet_data
        )
        
        # Verify
        assert result.name == "Buddy"
        assert result.species == "dog"
        assert result.owner_id == owner_id
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    async def test_create_pet_with_microchip_duplicate(self, pet_service, mock_db_session):
        """Test pet creation with duplicate microchip ID."""
        # Setup
        owner_id = uuid.uuid4()
        microchip_id = "123456789012345"
        
        # Mock existing pet with same microchip
        existing_pet = Pet(id=uuid.uuid4(), microchip_id=microchip_id)
        
        with patch.object(pet_service, 'get_pet_by_microchip', return_value=existing_pet):
            # Execute & Verify
            with pytest.raises(ValidationError, match="Microchip ID already registered"):
                await pet_service.create_pet(
                    owner_id=owner_id,
                    name="Buddy",
                    species="dog",
                    microchip_id=microchip_id
                )

    async def test_get_pet_by_id_success(self, pet_service, mock_db_session, sample_pet):
        """Test successful pet retrieval by ID."""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_pet
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await pet_service.get_pet_by_id(sample_pet.id)
        
        # Verify
        assert result == sample_pet
        mock_db_session.execute.assert_called_once()

    async def test_get_pet_by_id_not_found(self, pet_service, mock_db_session):
        """Test pet retrieval with non-existent ID."""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Execute & Verify
        with pytest.raises(NotFoundError):
            await pet_service.get_pet_by_id(uuid.uuid4())

    async def test_update_pet_success(self, pet_service, mock_db_session, sample_pet):
        """Test successful pet update."""
        # Setup
        with patch.object(pet_service, 'get_pet_by_id', return_value=sample_pet):
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()
            
            # Execute
            result = await pet_service.update_pet(
                pet_id=sample_pet.id,
                name="Updated Buddy",
                weight=70.0
            )
            
            # Verify
            assert result.name == "Updated Buddy"
            assert result.weight == 70.0
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()

    async def test_delete_pet_success(self, pet_service, mock_db_session, sample_pet):
        """Test successful pet deletion."""
        # Setup
        with patch.object(pet_service, 'get_pet_by_id', return_value=sample_pet):
            mock_db_session.delete = AsyncMock()
            mock_db_session.commit = AsyncMock()
            
            # Execute
            await pet_service.delete_pet(sample_pet.id)
            
            # Verify
            mock_db_session.delete.assert_called_once_with(sample_pet)
            mock_db_session.commit.assert_called_once()

    async def test_list_pets_with_filters(self, pet_service, mock_db_session, sample_pet):
        """Test pet listing with filters."""
        # Setup
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 1
        mock_list_result = AsyncMock()
        mock_list_result.scalars.return_value.all.return_value = [sample_pet]
        
        mock_db_session.execute.side_effect = [mock_count_result, mock_list_result]
        
        # Execute
        pets, total = await pet_service.list_pets(
            page=1,
            per_page=10,
            species="dog",
            gender=PetGender.MALE,
            is_active=True
        )
        
        # Verify
        assert len(pets) == 1
        assert total == 1
        assert pets[0] == sample_pet
        assert mock_db_session.execute.call_count == 2

    # Health Record Tests

    async def test_add_health_record_success(self, pet_service, mock_db_session, sample_pet):
        """Test successful health record creation."""
        # Setup
        with patch.object(pet_service, 'get_pet_by_id', return_value=sample_pet):
            mock_db_session.add = MagicMock()
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()
            
            # Execute
            result = await pet_service.add_health_record(
                pet_id=sample_pet.id,
                record_type=HealthRecordType.VACCINATION,
                title="Annual Rabies Vaccination",
                description="Rabies vaccination administered",
                record_date=date(2024, 1, 15),
                medication_name="Rabies Vaccine",
                dosage="1ml",
                cost=45.00
            )
            
            # Verify
            assert result.title == "Annual Rabies Vaccination"
            assert result.record_type == HealthRecordType.VACCINATION
            assert result.pet_id == sample_pet.id
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()

    async def test_add_health_record_invalid_type(self, pet_service, mock_db_session, sample_pet):
        """Test health record creation with invalid type."""
        # Setup
        with patch.object(pet_service, 'get_pet_by_id', return_value=sample_pet):
            # Execute & Verify
            with pytest.raises(ValidationError, match="Invalid record type"):
                await pet_service.add_health_record(
                    pet_id=sample_pet.id,
                    record_type="invalid_type",
                    title="Test Record",
                    record_date=date(2024, 1, 15)
                )

    async def test_get_pet_health_records_success(self, pet_service, mock_db_session, sample_health_record):
        """Test successful health records retrieval."""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_health_record]
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await pet_service.get_pet_health_records(
            pet_id=sample_health_record.pet_id,
            record_type=HealthRecordType.VACCINATION
        )
        
        # Verify
        assert len(result) == 1
        assert result[0] == sample_health_record
        mock_db_session.execute.assert_called_once()

    async def test_get_pet_health_records_with_date_filters(self, pet_service, mock_db_session, sample_health_record):
        """Test health records retrieval with date filters."""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_health_record]
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await pet_service.get_pet_health_records(
            pet_id=sample_health_record.pet_id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        
        # Verify
        assert len(result) == 1
        assert result[0] == sample_health_record
        mock_db_session.execute.assert_called_once()

    # Reminder Tests

    async def test_create_reminder_success(self, pet_service, mock_db_session, sample_pet):
        """Test successful reminder creation."""
        # Setup
        with patch.object(pet_service, 'get_pet_by_id', return_value=sample_pet):
            mock_db_session.add = MagicMock()
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()
            
            # Execute
            result = await pet_service.create_reminder(
                pet_id=sample_pet.id,
                title="Vaccination Reminder",
                reminder_type="vaccination",
                due_date=date(2025, 1, 15),
                reminder_date=date(2025, 1, 8),
                description="Time for annual rabies vaccination"
            )
            
            # Verify
            assert result.title == "Vaccination Reminder"
            assert result.reminder_type == "vaccination"
            assert result.pet_id == sample_pet.id
            assert result.is_completed is False
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()

    async def test_get_pet_reminders_success(self, pet_service, mock_db_session, sample_reminder):
        """Test successful reminders retrieval."""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_reminder]
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await pet_service.get_pet_reminders(
            pet_id=sample_reminder.pet_id,
            reminder_type="vaccination",
            is_completed=False
        )
        
        # Verify
        assert len(result) == 1
        assert result[0] == sample_reminder
        mock_db_session.execute.assert_called_once()

    async def test_get_pet_reminders_with_due_before_filter(self, pet_service, mock_db_session, sample_reminder):
        """Test reminders retrieval with due_before filter."""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_reminder]
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await pet_service.get_pet_reminders(
            pet_id=sample_reminder.pet_id,
            due_before=date(2025, 2, 1)
        )
        
        # Verify
        assert len(result) == 1
        assert result[0] == sample_reminder
        mock_db_session.execute.assert_called_once()

    async def test_complete_reminder_success(self, pet_service, mock_db_session, sample_reminder):
        """Test successful reminder completion."""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_reminder
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        
        # Execute
        result = await pet_service.complete_reminder(sample_reminder.id)
        
        # Verify
        assert result.is_completed is True
        assert result.completed_at is not None
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    async def test_complete_reminder_not_found(self, pet_service, mock_db_session):
        """Test reminder completion with non-existent ID."""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Execute & Verify
        with pytest.raises(NotFoundError):
            await pet_service.complete_reminder(uuid.uuid4())

    async def test_get_due_reminders_success(self, pet_service, mock_db_session, sample_reminder):
        """Test successful due reminders retrieval."""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_reminder]
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await pet_service.get_due_reminders(date.today())
        
        # Verify
        assert len(result) == 1
        assert result[0] == sample_reminder
        mock_db_session.execute.assert_called_once()

    async def test_mark_reminder_sent_success(self, pet_service, mock_db_session, sample_reminder):
        """Test successful reminder sent marking."""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_reminder
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        
        # Execute
        result = await pet_service.mark_reminder_sent(sample_reminder.id)
        
        # Verify
        assert result.is_sent is True
        assert result.sent_at is not None
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    async def test_mark_reminder_sent_not_found(self, pet_service, mock_db_session):
        """Test reminder sent marking with non-existent ID."""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Execute & Verify
        with pytest.raises(NotFoundError):
            await pet_service.mark_reminder_sent(uuid.uuid4())

    # Edge Cases and Error Handling

    async def test_create_pet_database_error(self, pet_service, mock_db_session):
        """Test pet creation with database error."""
        # Setup
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock(side_effect=Exception("Database error"))
        mock_db_session.rollback = AsyncMock()
        
        # Execute & Verify
        with pytest.raises(VetClinicException, match="Failed to create pet"):
            await pet_service.create_pet(
                owner_id=uuid.uuid4(),
                name="Buddy",
                species="dog"
            )
        
        mock_db_session.rollback.assert_called_once()

    async def test_add_health_record_database_error(self, pet_service, mock_db_session, sample_pet):
        """Test health record creation with database error."""
        # Setup
        with patch.object(pet_service, 'get_pet_by_id', return_value=sample_pet):
            mock_db_session.add = MagicMock()
            mock_db_session.commit = AsyncMock(side_effect=Exception("Database error"))
            mock_db_session.rollback = AsyncMock()
            
            # Execute & Verify
            with pytest.raises(VetClinicException, match="Failed to add health record"):
                await pet_service.add_health_record(
                    pet_id=sample_pet.id,
                    record_type=HealthRecordType.VACCINATION,
                    title="Test Record",
                    record_date=date(2024, 1, 15)
                )
            
            mock_db_session.rollback.assert_called_once()

    async def test_create_reminder_database_error(self, pet_service, mock_db_session, sample_pet):
        """Test reminder creation with database error."""
        # Setup
        with patch.object(pet_service, 'get_pet_by_id', return_value=sample_pet):
            mock_db_session.add = MagicMock()
            mock_db_session.commit = AsyncMock(side_effect=Exception("Database error"))
            mock_db_session.rollback = AsyncMock()
            
            # Execute & Verify
            with pytest.raises(VetClinicException, match="Failed to create reminder"):
                await pet_service.create_reminder(
                    pet_id=sample_pet.id,
                    title="Test Reminder",
                    reminder_type="vaccination",
                    due_date=date(2025, 1, 15),
                    reminder_date=date(2025, 1, 8)
                )
            
            mock_db_session.rollback.assert_called_once()

    # Utility Method Tests

    async def test_get_pet_by_microchip_success(self, pet_service, mock_db_session, sample_pet):
        """Test successful pet retrieval by microchip."""
        # Setup
        sample_pet.microchip_id = "123456789012345"
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_pet
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await pet_service.get_pet_by_microchip("123456789012345")
        
        # Verify
        assert result == sample_pet
        mock_db_session.execute.assert_called_once()

    async def test_get_pet_by_microchip_not_found(self, pet_service, mock_db_session):
        """Test pet retrieval by microchip with non-existent ID."""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await pet_service.get_pet_by_microchip("nonexistent")
        
        # Verify
        assert result is None
        mock_db_session.execute.assert_called_once()

    async def test_get_pets_by_owner_success(self, pet_service, mock_db_session, sample_pet):
        """Test successful pets retrieval by owner."""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_pet]
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await pet_service.get_pets_by_owner(
            owner_id=sample_pet.owner_id,
            is_active=True
        )
        
        # Verify
        assert len(result) == 1
        assert result[0] == sample_pet
        mock_db_session.execute.assert_called_once()

    async def test_mark_pet_deceased_success(self, pet_service, mock_db_session, sample_pet):
        """Test successful pet deceased marking."""
        # Setup
        with patch.object(pet_service, 'get_pet_by_id', return_value=sample_pet):
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()
            
            # Execute
            result = await pet_service.mark_pet_deceased(
                pet_id=sample_pet.id,
                deceased_date=date(2024, 1, 15)
            )
            
            # Verify
            assert result.is_deceased is True
            assert result.deceased_date == date(2024, 1, 15)
            assert result.is_active is False
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()