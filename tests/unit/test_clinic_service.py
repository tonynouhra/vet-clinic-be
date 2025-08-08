"""
Unit tests for ClinicService.

Tests the core business logic and data access methods for clinic and veterinarian
management without HTTP layer dependencies.
"""

import pytest
import uuid
from datetime import date, time
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.clinics.services import ClinicService
from app.models.clinic import (
    Clinic, Veterinarian, VeterinarianAvailability, ClinicReview, VeterinarianReview,
    ClinicType, VeterinarianSpecialty, DayOfWeek
)
from app.models.user import User, UserRole
from app.core.exceptions import NotFoundError, ValidationError


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def clinic_service(mock_db):
    """Create ClinicService instance with mocked database."""
    return ClinicService(mock_db)


@pytest.fixture
def sample_clinic():
    """Sample clinic for testing."""
    return Clinic(
        id=uuid.uuid4(),
        name="Test Veterinary Clinic",
        clinic_type=ClinicType.GENERAL_PRACTICE,
        description="A test clinic",
        phone_number="555-0123",
        email="test@clinic.com",
        address_line1="123 Main St",
        city="Test City",
        state="Test State",
        zip_code="12345",
        country="United States",
        latitude=40.7128,
        longitude=-74.0060,
        is_emergency_clinic=False,
        is_24_hour=False,
        is_active=True,
        is_accepting_new_patients=True
    )


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return User(
        id=uuid.uuid4(),
        clerk_id="test_clerk_id",
        email="vet@test.com",
        first_name="Dr. John",
        last_name="Doe",
        role=UserRole.VETERINARIAN,
        is_active=True
    )


@pytest.fixture
def sample_veterinarian(sample_user, sample_clinic):
    """Sample veterinarian for testing."""
    return Veterinarian(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        clinic_id=sample_clinic.id,
        license_number="VET123456",
        years_of_experience=5,
        bio="Experienced veterinarian",
        consultation_fee=150.0,
        is_available_for_emergency=True,
        is_accepting_new_patients=True,
        is_active=True,
        user=sample_user,
        clinic=sample_clinic
    )


class TestClinicService:
    """Test cases for ClinicService."""

    @pytest.mark.asyncio
    async def test_list_clinics_basic(self, clinic_service, mock_db, sample_clinic):
        """Test basic clinic listing."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_clinic]
        mock_db.execute.return_value = mock_result
        
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        # Test
        clinics, total = await clinic_service.list_clinics(page=1, per_page=10)
        
        # Assertions
        assert len(clinics) == 1
        assert total == 1
        assert clinics[0] == sample_clinic
        assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_list_clinics_with_filters(self, clinic_service, mock_db, sample_clinic):
        """Test clinic listing with filters."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_clinic]
        mock_db.execute.return_value = mock_result
        
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        # Test with filters
        clinics, total = await clinic_service.list_clinics(
            page=1,
            per_page=10,
            clinic_type=ClinicType.GENERAL_PRACTICE,
            city="Test City",
            is_emergency=False
        )
        
        # Assertions
        assert len(clinics) == 1
        assert total == 1
        assert clinics[0] == sample_clinic

    @pytest.mark.asyncio
    async def test_list_clinics_location_search(self, clinic_service, mock_db, sample_clinic):
        """Test clinic listing with location-based search."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_clinic]
        mock_db.execute.return_value = mock_result
        
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        # Test with location search
        clinics, total = await clinic_service.list_clinics(
            page=1,
            per_page=10,
            latitude=40.7128,
            longitude=-74.0060,
            radius_miles=25
        )
        
        # Assertions
        assert len(clinics) == 1
        assert total == 1
        assert clinics[0] == sample_clinic

    @pytest.mark.asyncio
    async def test_get_clinic_by_id_success(self, clinic_service, mock_db, sample_clinic):
        """Test successful clinic retrieval by ID."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_clinic
        mock_db.execute.return_value = mock_result
        
        # Test
        clinic = await clinic_service.get_clinic_by_id(sample_clinic.id)
        
        # Assertions
        assert clinic == sample_clinic
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_clinic_by_id_not_found(self, clinic_service, mock_db):
        """Test clinic retrieval when clinic doesn't exist."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Test
        with pytest.raises(NotFoundError, match="Clinic with id .* not found"):
            await clinic_service.get_clinic_by_id(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_list_veterinarians_basic(self, clinic_service, mock_db, sample_veterinarian):
        """Test basic veterinarian listing."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_veterinarian]
        mock_db.execute.return_value = mock_result
        
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        # Test
        veterinarians, total = await clinic_service.list_veterinarians(page=1, per_page=10)
        
        # Assertions
        assert len(veterinarians) == 1
        assert total == 1
        assert veterinarians[0] == sample_veterinarian
        assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_list_veterinarians_with_filters(self, clinic_service, mock_db, sample_veterinarian):
        """Test veterinarian listing with filters."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_veterinarian]
        mock_db.execute.return_value = mock_result
        
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        # Test with filters
        veterinarians, total = await clinic_service.list_veterinarians(
            page=1,
            per_page=10,
            specialty=VeterinarianSpecialty.GENERAL_PRACTICE,
            is_available_for_emergency=True,
            min_experience_years=3
        )
        
        # Assertions
        assert len(veterinarians) == 1
        assert total == 1
        assert veterinarians[0] == sample_veterinarian

    @pytest.mark.asyncio
    async def test_get_veterinarian_by_id_success(self, clinic_service, mock_db, sample_veterinarian):
        """Test successful veterinarian retrieval by ID."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_veterinarian
        mock_db.execute.return_value = mock_result
        
        # Test
        veterinarian = await clinic_service.get_veterinarian_by_id(sample_veterinarian.id)
        
        # Assertions
        assert veterinarian == sample_veterinarian
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_veterinarian_by_id_not_found(self, clinic_service, mock_db):
        """Test veterinarian retrieval when veterinarian doesn't exist."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Test
        with pytest.raises(NotFoundError, match="Veterinarian with id .* not found"):
            await clinic_service.get_veterinarian_by_id(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_veterinarian_by_user_id(self, clinic_service, mock_db, sample_veterinarian, sample_user):
        """Test veterinarian retrieval by user ID."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_veterinarian
        mock_db.execute.return_value = mock_result
        
        # Test
        veterinarian = await clinic_service.get_veterinarian_by_user_id(sample_user.id)
        
        # Assertions
        assert veterinarian == sample_veterinarian
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_veterinarian_availability(self, clinic_service, mock_db, sample_veterinarian):
        """Test veterinarian availability retrieval."""
        # Create sample availability
        availability = VeterinarianAvailability(
            id=uuid.uuid4(),
            veterinarian_id=sample_veterinarian.id,
            day_of_week=DayOfWeek.MONDAY,
            is_available=True,
            start_time=time(9, 0),
            end_time=time(17, 0),
            default_appointment_duration=30
        )
        
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [availability]
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await clinic_service.get_veterinarian_availability(sample_veterinarian.id)
        
        # Assertions
        assert len(result) == 1
        assert result[0] == availability
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_veterinarian_availability(self, clinic_service, mock_db, sample_veterinarian):
        """Test veterinarian availability update."""
        # Mock get_veterinarian_by_id
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = sample_veterinarian
        
        # Mock delete query
        mock_delete_result = MagicMock()
        
        # Set up execute side effects
        mock_db.execute.side_effect = [mock_get_result, mock_delete_result]
        
        # Test data
        availability_data = [
            {
                "day_of_week": DayOfWeek.MONDAY,
                "is_available": True,
                "start_time": time(9, 0),
                "end_time": time(17, 0),
                "default_appointment_duration": 30
            }
        ]
        
        # Test
        result = await clinic_service.update_veterinarian_availability(
            sample_veterinarian.id,
            availability_data
        )
        
        # Assertions
        assert len(result) == 1
        assert result[0].veterinarian_id == sample_veterinarian.id
        assert result[0].day_of_week == DayOfWeek.MONDAY
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_clinic_review(self, clinic_service, mock_db, sample_clinic, sample_user):
        """Test clinic review creation."""
        # Mock get_clinic_by_id
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = sample_clinic
        mock_db.execute.return_value = mock_get_result
        
        # Test
        review = await clinic_service.create_clinic_review(
            clinic_id=sample_clinic.id,
            reviewer_id=sample_user.id,
            rating=5,
            title="Great clinic!",
            review_text="Excellent service and care."
        )
        
        # Assertions
        assert review.clinic_id == sample_clinic.id
        assert review.reviewer_id == sample_user.id
        assert review.rating == 5
        assert review.title == "Great clinic!"
        assert review.review_text == "Excellent service and care."
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_clinic_review_invalid_rating(self, clinic_service, mock_db, sample_clinic, sample_user):
        """Test clinic review creation with invalid rating."""
        # Mock get_clinic_by_id
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = sample_clinic
        mock_db.execute.return_value = mock_get_result
        
        # Test with invalid rating
        with pytest.raises(ValidationError, match="Rating must be between 1 and 5"):
            await clinic_service.create_clinic_review(
                clinic_id=sample_clinic.id,
                reviewer_id=sample_user.id,
                rating=6,
                title="Great clinic!"
            )

    @pytest.mark.asyncio
    async def test_create_veterinarian_review(self, clinic_service, mock_db, sample_veterinarian, sample_user):
        """Test veterinarian review creation."""
        # Mock get_veterinarian_by_id
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = sample_veterinarian
        mock_db.execute.return_value = mock_get_result
        
        # Test
        review = await clinic_service.create_veterinarian_review(
            veterinarian_id=sample_veterinarian.id,
            reviewer_id=sample_user.id,
            rating=5,
            title="Excellent vet!",
            review_text="Very knowledgeable and caring.",
            bedside_manner_rating=5,
            expertise_rating=5,
            communication_rating=4
        )
        
        # Assertions
        assert review.veterinarian_id == sample_veterinarian.id
        assert review.reviewer_id == sample_user.id
        assert review.rating == 5
        assert review.title == "Excellent vet!"
        assert review.bedside_manner_rating == 5
        assert review.expertise_rating == 5
        assert review.communication_rating == 4
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_clinic_reviews(self, clinic_service, mock_db, sample_clinic):
        """Test clinic reviews retrieval."""
        # Create sample review
        review = ClinicReview(
            id=uuid.uuid4(),
            clinic_id=sample_clinic.id,
            reviewer_id=uuid.uuid4(),
            rating=5,
            title="Great clinic!",
            review_text="Excellent service."
        )
        
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [review]
        mock_db.execute.return_value = mock_result
        
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        # Test
        reviews, total = await clinic_service.get_clinic_reviews(sample_clinic.id)
        
        # Assertions
        assert len(reviews) == 1
        assert total == 1
        assert reviews[0] == review

    @pytest.mark.asyncio
    async def test_get_veterinarian_reviews(self, clinic_service, mock_db, sample_veterinarian):
        """Test veterinarian reviews retrieval."""
        # Create sample review
        review = VeterinarianReview(
            id=uuid.uuid4(),
            veterinarian_id=sample_veterinarian.id,
            reviewer_id=uuid.uuid4(),
            rating=5,
            title="Excellent vet!",
            review_text="Very professional."
        )
        
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [review]
        mock_db.execute.return_value = mock_result
        
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        # Test
        reviews, total = await clinic_service.get_veterinarian_reviews(sample_veterinarian.id)
        
        # Assertions
        assert len(reviews) == 1
        assert total == 1
        assert reviews[0] == review

    @pytest.mark.asyncio
    async def test_search_veterinarians_by_location(self, clinic_service, mock_db, sample_veterinarian):
        """Test location-based veterinarian search."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.all.return_value = [(sample_veterinarian, 5.2)]  # vet with distance
        mock_db.execute.return_value = mock_result
        
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        # Test
        veterinarians, total = await clinic_service.search_veterinarians_by_location(
            latitude=40.7128,
            longitude=-74.0060,
            radius_miles=25
        )
        
        # Assertions
        assert len(veterinarians) == 1
        assert total == 1
        assert veterinarians[0] == sample_veterinarian

    @pytest.mark.asyncio
    async def test_get_veterinarian_specialties(self, clinic_service, mock_db, sample_veterinarian):
        """Test veterinarian specialties retrieval."""
        # Mock database response
        mock_row = MagicMock()
        mock_row.specialty = VeterinarianSpecialty.GENERAL_PRACTICE
        mock_row.certification_date = date(2020, 1, 1)
        mock_row.certification_body = "Test Board"
        
        mock_result = MagicMock()
        mock_result.__iter__ = lambda x: iter([mock_row])
        mock_db.execute.return_value = mock_result
        
        # Test
        specialties = await clinic_service.get_veterinarian_specialties(sample_veterinarian.id)
        
        # Assertions
        assert len(specialties) == 1
        assert specialties[0]["specialty"] == VeterinarianSpecialty.GENERAL_PRACTICE
        assert specialties[0]["certification_date"] == date(2020, 1, 1)
        assert specialties[0]["certification_body"] == "Test Board"