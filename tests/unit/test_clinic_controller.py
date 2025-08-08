"""
Unit tests for ClinicController.

Tests the HTTP request processing and business logic orchestration
for clinic and veterinarian management operations.
"""

import pytest
import uuid
from datetime import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status

from app.clinics.controller import ClinicController
from app.models.clinic import (
    Clinic, Veterinarian, VeterinarianAvailability, ClinicReview, VeterinarianReview,
    ClinicType, VeterinarianSpecialty, DayOfWeek
)
from app.models.user import User, UserRole
from app.core.exceptions import NotFoundError, ValidationError


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def clinic_controller(mock_db):
    """Create ClinicController instance with mocked database."""
    return ClinicController(mock_db)


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


class TestClinicController:
    """Test cases for ClinicController."""

    @pytest.mark.asyncio
    async def test_list_clinics_success(self, clinic_controller, sample_clinic):
        """Test successful clinic listing."""
        # Mock service response
        with patch.object(clinic_controller.service, 'list_clinics') as mock_list:
            mock_list.return_value = ([sample_clinic], 1)
            
            # Test
            clinics, total = await clinic_controller.list_clinics(page=1, per_page=10)
            
            # Assertions
            assert len(clinics) == 1
            assert total == 1
            assert clinics[0] == sample_clinic
            mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_clinics_invalid_pagination(self, clinic_controller):
        """Test clinic listing with invalid pagination parameters."""
        # Test invalid page
        with pytest.raises(HTTPException) as exc_info:
            await clinic_controller.list_clinics(page=0, per_page=10)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Page must be greater than 0" in str(exc_info.value.detail)
        
        # Test invalid per_page
        with pytest.raises(HTTPException) as exc_info:
            await clinic_controller.list_clinics(page=1, per_page=101)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Items per page must be between 1 and 100" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_clinics_invalid_location(self, clinic_controller):
        """Test clinic listing with invalid location parameters."""
        # Test missing longitude
        with pytest.raises(HTTPException) as exc_info:
            await clinic_controller.list_clinics(
                page=1, per_page=10, latitude=40.7128
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Both latitude and longitude are required" in str(exc_info.value.detail)
        
        # Test invalid latitude
        with pytest.raises(HTTPException) as exc_info:
            await clinic_controller.list_clinics(
                page=1, per_page=10, latitude=91.0, longitude=-74.0060
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Latitude must be between -90 and 90" in str(exc_info.value.detail)
        
        # Test invalid radius
        with pytest.raises(HTTPException) as exc_info:
            await clinic_controller.list_clinics(
                page=1, per_page=10, latitude=40.7128, longitude=-74.0060, radius_miles=501
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Radius must be between 0 and 500 miles" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_clinic_by_id_success(self, clinic_controller, sample_clinic):
        """Test successful clinic retrieval by ID."""
        # Mock service response
        with patch.object(clinic_controller.service, 'get_clinic_by_id') as mock_get:
            mock_get.return_value = sample_clinic
            
            # Test
            clinic = await clinic_controller.get_clinic_by_id(sample_clinic.id)
            
            # Assertions
            assert clinic == sample_clinic
            mock_get.assert_called_once_with(
                clinic_id=sample_clinic.id,
                include_veterinarians=False,
                include_reviews=False,
                include_operating_hours=False
            )

    @pytest.mark.asyncio
    async def test_get_clinic_by_id_not_found(self, clinic_controller):
        """Test clinic retrieval when clinic doesn't exist."""
        # Mock service to raise NotFoundError
        with patch.object(clinic_controller.service, 'get_clinic_by_id') as mock_get:
            mock_get.side_effect = NotFoundError("Clinic not found")
            
            # Test
            with pytest.raises(HTTPException) as exc_info:
                await clinic_controller.get_clinic_by_id(uuid.uuid4())
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert "Clinic not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_veterinarians_success(self, clinic_controller, sample_veterinarian):
        """Test successful veterinarian listing."""
        # Mock service response
        with patch.object(clinic_controller.service, 'list_veterinarians') as mock_list:
            mock_list.return_value = ([sample_veterinarian], 1)
            
            # Test
            veterinarians, total = await clinic_controller.list_veterinarians(page=1, per_page=10)
            
            # Assertions
            assert len(veterinarians) == 1
            assert total == 1
            assert veterinarians[0] == sample_veterinarian
            mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_veterinarians_invalid_experience(self, clinic_controller):
        """Test veterinarian listing with invalid experience parameter."""
        with pytest.raises(HTTPException) as exc_info:
            await clinic_controller.list_veterinarians(
                page=1, per_page=10, min_experience_years=-1
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Minimum experience years cannot be negative" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_veterinarian_by_id_success(self, clinic_controller, sample_veterinarian):
        """Test successful veterinarian retrieval by ID."""
        # Mock service response
        with patch.object(clinic_controller.service, 'get_veterinarian_by_id') as mock_get:
            mock_get.return_value = sample_veterinarian
            
            # Test
            veterinarian = await clinic_controller.get_veterinarian_by_id(sample_veterinarian.id)
            
            # Assertions
            assert veterinarian == sample_veterinarian
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_veterinarian_availability_success(self, clinic_controller, sample_veterinarian):
        """Test successful veterinarian availability retrieval."""
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
        
        # Mock service response
        with patch.object(clinic_controller.service, 'get_veterinarian_availability') as mock_get:
            mock_get.return_value = [availability]
            
            # Test
            result = await clinic_controller.get_veterinarian_availability(sample_veterinarian.id)
            
            # Assertions
            assert len(result) == 1
            assert result[0] == availability
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_veterinarian_availability_success(self, clinic_controller, sample_veterinarian):
        """Test successful veterinarian availability update."""
        # Create sample availability data
        availability_data = [
            {
                "day_of_week": DayOfWeek.MONDAY,
                "is_available": True,
                "start_time": time(9, 0),
                "end_time": time(17, 0),
                "default_appointment_duration": 30
            }
        ]
        
        # Create expected result
        updated_availability = VeterinarianAvailability(
            id=uuid.uuid4(),
            veterinarian_id=sample_veterinarian.id,
            day_of_week=DayOfWeek.MONDAY,
            is_available=True,
            start_time=time(9, 0),
            end_time=time(17, 0),
            default_appointment_duration=30
        )
        
        # Mock service response
        with patch.object(clinic_controller.service, 'update_veterinarian_availability') as mock_update:
            mock_update.return_value = [updated_availability]
            
            # Test
            result = await clinic_controller.update_veterinarian_availability(
                sample_veterinarian.id,
                availability_data,
                updated_by=uuid.uuid4()
            )
            
            # Assertions
            assert len(result) == 1
            assert result[0] == updated_availability
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_veterinarian_availability_validation_error(self, clinic_controller, sample_veterinarian):
        """Test veterinarian availability update with validation errors."""
        # Test empty availability data
        with pytest.raises(HTTPException) as exc_info:
            await clinic_controller.update_veterinarian_availability(
                sample_veterinarian.id,
                [],
                updated_by=uuid.uuid4()
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Availability data is required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_clinic_review_success(self, clinic_controller, sample_clinic):
        """Test successful clinic review creation."""
        # Create sample review data
        review_data = {
            "rating": 5,
            "title": "Great clinic!",
            "review_text": "Excellent service and care.",
            "is_anonymous": False
        }
        
        # Create expected result
        review = ClinicReview(
            id=uuid.uuid4(),
            clinic_id=sample_clinic.id,
            reviewer_id=uuid.uuid4(),
            rating=5,
            title="Great clinic!",
            review_text="Excellent service and care.",
            is_anonymous=False
        )
        
        # Mock service response
        with patch.object(clinic_controller.service, 'create_clinic_review') as mock_create:
            mock_create.return_value = review
            
            # Test
            result = await clinic_controller.create_clinic_review(
                sample_clinic.id,
                review_data,
                reviewer_id=uuid.uuid4()
            )
            
            # Assertions
            assert result == review
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_clinic_review_validation_error(self, clinic_controller, sample_clinic):
        """Test clinic review creation with validation errors."""
        # Test missing rating
        review_data = {
            "title": "Great clinic!",
            "review_text": "Excellent service."
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await clinic_controller.create_clinic_review(
                sample_clinic.id,
                review_data,
                reviewer_id=uuid.uuid4()
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Rating is required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_veterinarian_review_success(self, clinic_controller, sample_veterinarian):
        """Test successful veterinarian review creation."""
        # Create sample review data
        review_data = {
            "rating": 5,
            "title": "Excellent vet!",
            "review_text": "Very knowledgeable and caring.",
            "bedside_manner_rating": 5,
            "expertise_rating": 5,
            "communication_rating": 4,
            "is_anonymous": False
        }
        
        # Create expected result
        review = VeterinarianReview(
            id=uuid.uuid4(),
            veterinarian_id=sample_veterinarian.id,
            reviewer_id=uuid.uuid4(),
            rating=5,
            title="Excellent vet!",
            review_text="Very knowledgeable and caring.",
            bedside_manner_rating=5,
            expertise_rating=5,
            communication_rating=4,
            is_anonymous=False
        )
        
        # Mock service response
        with patch.object(clinic_controller.service, 'create_veterinarian_review') as mock_create:
            mock_create.return_value = review
            
            # Test
            result = await clinic_controller.create_veterinarian_review(
                sample_veterinarian.id,
                review_data,
                reviewer_id=uuid.uuid4()
            )
            
            # Assertions
            assert result == review
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_clinic_reviews_success(self, clinic_controller, sample_clinic):
        """Test successful clinic reviews retrieval."""
        # Create sample review
        review = ClinicReview(
            id=uuid.uuid4(),
            clinic_id=sample_clinic.id,
            reviewer_id=uuid.uuid4(),
            rating=5,
            title="Great clinic!",
            review_text="Excellent service."
        )
        
        # Mock service response
        with patch.object(clinic_controller.service, 'get_clinic_reviews') as mock_get:
            mock_get.return_value = ([review], 1)
            
            # Test
            reviews, total = await clinic_controller.get_clinic_reviews(sample_clinic.id)
            
            # Assertions
            assert len(reviews) == 1
            assert total == 1
            assert reviews[0] == review
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_veterinarian_reviews_success(self, clinic_controller, sample_veterinarian):
        """Test successful veterinarian reviews retrieval."""
        # Create sample review
        review = VeterinarianReview(
            id=uuid.uuid4(),
            veterinarian_id=sample_veterinarian.id,
            reviewer_id=uuid.uuid4(),
            rating=5,
            title="Excellent vet!",
            review_text="Very professional."
        )
        
        # Mock service response
        with patch.object(clinic_controller.service, 'get_veterinarian_reviews') as mock_get:
            mock_get.return_value = ([review], 1)
            
            # Test
            reviews, total = await clinic_controller.get_veterinarian_reviews(sample_veterinarian.id)
            
            # Assertions
            assert len(reviews) == 1
            assert total == 1
            assert reviews[0] == review
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_veterinarians_by_location_success(self, clinic_controller, sample_veterinarian):
        """Test successful location-based veterinarian search."""
        # Mock service response
        with patch.object(clinic_controller.service, 'search_veterinarians_by_location') as mock_search:
            mock_search.return_value = ([sample_veterinarian], 1)
            
            # Test
            veterinarians, total = await clinic_controller.search_veterinarians_by_location(
                latitude=40.7128,
                longitude=-74.0060,
                radius_miles=25
            )
            
            # Assertions
            assert len(veterinarians) == 1
            assert total == 1
            assert veterinarians[0] == sample_veterinarian
            mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_veterinarians_by_location_invalid_params(self, clinic_controller):
        """Test location-based veterinarian search with invalid parameters."""
        # Test invalid latitude
        with pytest.raises(HTTPException) as exc_info:
            await clinic_controller.search_veterinarians_by_location(
                latitude=91.0,
                longitude=-74.0060,
                radius_miles=25
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Latitude must be between -90 and 90" in str(exc_info.value.detail)
        
        # Test invalid longitude
        with pytest.raises(HTTPException) as exc_info:
            await clinic_controller.search_veterinarians_by_location(
                latitude=40.7128,
                longitude=181.0,
                radius_miles=25
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Longitude must be between -180 and 180" in str(exc_info.value.detail)
        
        # Test invalid radius
        with pytest.raises(HTTPException) as exc_info:
            await clinic_controller.search_veterinarians_by_location(
                latitude=40.7128,
                longitude=-74.0060,
                radius_miles=501
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Radius must be between 0 and 500 miles" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_veterinarian_specialties_success(self, clinic_controller, sample_veterinarian):
        """Test successful veterinarian specialties retrieval."""
        # Create sample specialties
        specialties = [
            {
                "specialty": VeterinarianSpecialty.GENERAL_PRACTICE,
                "certification_date": "2020-01-01",
                "certification_body": "Test Board"
            }
        ]
        
        # Mock service response
        with patch.object(clinic_controller.service, 'get_veterinarian_specialties') as mock_get:
            mock_get.return_value = specialties
            
            # Test
            result = await clinic_controller.get_veterinarian_specialties(sample_veterinarian.id)
            
            # Assertions
            assert len(result) == 1
            assert result[0]["specialty"] == VeterinarianSpecialty.GENERAL_PRACTICE
            mock_get.assert_called_once()