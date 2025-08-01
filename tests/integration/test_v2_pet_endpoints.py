"""
Integration tests for V2 Pet API endpoints.

Tests the complete flow from HTTP request to database for V2 pet endpoints,
ensuring proper integration between API layer, controllers, and services.
Includes enhanced V2 features like health records, statistics, and batch operations.
"""

import pytest
import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from fastapi import status

from app.models.user import User, UserRole
from app.models.pet import Pet, PetGender, PetSize, HealthRecord, HealthRecordType
from app.api.schemas.v2.pets import PetResponseV2, HealthRecordResponseV2


class TestV2PetEndpoints:
    """Test V2 pet API endpoints integration."""

    @pytest.fixture
    def sample_pet_data_v2(self):
        """Sample V2 pet data for testing."""
        return {
            "owner_id": str(uuid.uuid4()),
            "name": "Buddy",
            "species": "dog",
            "breed": "Golden Retriever",
            "mixed_breed": False,
            "gender": "male",
            "size": "large",
            "weight": 65.5,
            "color": "golden",
            "birth_date": "2020-01-15",
            "age_years": 4,
            "age_months": 0,
            "is_age_estimated": False,
            "microchip_id": "123456789012345",
            "medical_notes": "No known allergies",
            "allergies": None,
            "current_medications": None,
            "special_needs": None,
            "temperament": "Friendly and energetic",
            "behavioral_notes": "Good with children",
            "profile_image_url": "https://example.com/buddy.jpg",
            # V2 enhanced features
            "additional_photos": [
                "https://example.com/buddy1.jpg",
                "https://example.com/buddy2.jpg"
            ],
            "emergency_contact": {
                "name": "John Doe",
                "phone": "555-0123",
                "relationship": "Owner"
            },
            "insurance_info": {
                "provider": "Pet Insurance Co",
                "policy_number": "PI123456",
                "coverage_type": "comprehensive"
            },
            "preferred_vet_id": str(uuid.uuid4())
        }

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
            "cost": 45.00,
            "notes": "No adverse reactions observed"
        }

    @pytest.fixture
    def mock_pet_v2(self):
        """Mock pet object with V2 features for testing."""
        pet_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        
        return Pet(
            id=pet_id,
            owner_id=owner_id,
            name="Buddy",
            species="dog",
            breed="Golden Retriever",
            mixed_breed=False,
            gender=PetGender.MALE,
            size=PetSize.LARGE,
            weight=65.5,
            color="golden",
            birth_date=date(2020, 1, 15),
            age_years=4,
            age_months=0,
            is_age_estimated=False,
            microchip_id="123456789012345",
            medical_notes="No known allergies",
            allergies=None,
            current_medications=None,
            special_needs=None,
            temperament="Friendly and energetic",
            behavioral_notes="Good with children",
            profile_image_url="https://example.com/buddy.jpg",
            # V2 enhanced features
            additional_photos=["https://example.com/buddy1.jpg", "https://example.com/buddy2.jpg"],
            is_active=True,
            is_deceased=False,
            deceased_date=None,
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
            cost=45.00,
            notes="No adverse reactions observed",
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

    async def test_create_pet_v2_success(self, async_client: AsyncClient, sample_pet_data_v2, mock_pet_v2, mock_user):
        """Test successful pet creation via V2 endpoint with enhanced features."""
        with patch("app.pets.controller.PetController.create_pet", new_callable=AsyncMock) as mock_create_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            mock_create_pet.return_value = mock_pet_v2
            
            response = await async_client.post(
                "/api/v2/pets/",
                json=sample_pet_data_v2
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v2"
            assert "data" in data
            
            # Verify pet data includes V2 features
            pet_data = data["data"]
            assert pet_data["name"] == "Buddy"
            assert pet_data["temperament"] == "Friendly and energetic"
            assert pet_data["behavioral_notes"] == "Good with children"
            assert "additional_photos" in pet_data
            
            # Verify controller was called correctly
            mock_create_pet.assert_called_once()

    async def test_list_pets_v2_with_enhanced_features(self, async_client: AsyncClient, mock_pet_v2, mock_user):
        """Test pet listing via V2 endpoint with enhanced features."""
        with patch("app.pets.controller.PetController.list_pets", new_callable=AsyncMock) as mock_list_pets, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_list_pets.return_value = ([mock_pet_v2], 1)
            
            # Test with V2 enhanced parameters
            response = await async_client.get(
                "/api/v2/pets/?include_health_records=true&include_owner=true&sort_by=name&include_statistics=true"
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v2"
            assert "data" in data
            
            # Verify V2 enhanced response features
            list_data = data["data"]
            assert "statistics" in list_data
            assert "filters_applied" in list_data
            assert list_data["statistics"] is not None
            
            # Verify controller was called with V2 parameters
            mock_list_pets.assert_called_once()
            call_kwargs = mock_list_pets.call_args[1]
            assert call_kwargs["include_health_records"] is True
            assert call_kwargs["include_owner"] is True
            assert call_kwargs["sort_by"] == "name"

    async def test_get_pet_v2_with_relationships(self, async_client: AsyncClient, mock_pet_v2, mock_user):
        """Test pet retrieval via V2 endpoint with relationship data."""
        with patch("app.pets.controller.PetController.get_pet_by_id", new_callable=AsyncMock) as mock_get_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_pet.return_value = mock_pet_v2
            
            # Test with V2 enhanced parameters
            response = await async_client.get(
                f"/api/v2/pets/{mock_pet_v2.id}?include_health_records=true&include_owner=true&include_appointments=true"
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v2"
            
            # Verify controller was called with V2 parameters
            mock_get_pet.assert_called_once()
            call_kwargs = mock_get_pet.call_args[1]
            assert call_kwargs["include_health_records"] is True
            assert call_kwargs["include_owner"] is True
            assert call_kwargs["include_appointments"] is True

    async def test_get_pet_statistics_v2(self, async_client: AsyncClient, mock_pet_v2, mock_user):
        """Test pet statistics endpoint (V2 specific)."""
        with patch("app.pets.controller.PetController.get_pet_by_id", new_callable=AsyncMock) as mock_get_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            # Mock pet with health records and appointments
            mock_pet_v2.health_records = []
            mock_pet_v2.appointments = []
            mock_get_pet.return_value = mock_pet_v2
            
            response = await async_client.get(f"/api/v2/pets/{mock_pet_v2.id}/stats")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v2"
            assert "data" in data
            
            # Verify statistics data
            stats_data = data["data"]
            assert "total_health_records" in stats_data
            assert "total_appointments" in stats_data
            assert "days_since_registration" in stats_data
            assert "last_checkup_date" in stats_data
            assert "next_due_vaccination" in stats_data

    async def test_add_health_record_v2(self, async_client: AsyncClient, sample_health_record_data, mock_pet_v2, mock_health_record, mock_user):
        """Test adding health record via V2 endpoint."""
        with patch("app.pets.controller.PetController.add_health_record", new_callable=AsyncMock) as mock_add_record, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            mock_add_record.return_value = mock_health_record
            
            response = await async_client.post(
                f"/api/v2/pets/{mock_pet_v2.id}/health-records",
                json=sample_health_record_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v2"
            assert "data" in data
            
            # Verify health record data
            record_data = data["data"]
            assert record_data["record_type"] == "vaccination"
            assert record_data["title"] == "Annual Rabies Vaccination"
            assert record_data["medication_name"] == "Rabies Vaccine"
            
            # Verify controller was called correctly
            mock_add_record.assert_called_once()
            call_args = mock_add_record.call_args
            assert call_args[1]["pet_id"] == mock_pet_v2.id
            assert call_args[1]["created_by"] == mock_user.id

    async def test_get_pet_health_records_v2(self, async_client: AsyncClient, mock_pet_v2, mock_health_record, mock_user):
        """Test retrieving pet health records via V2 endpoint."""
        with patch("app.pets.controller.PetController.get_pet_health_records", new_callable=AsyncMock) as mock_get_records, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_records.return_value = [mock_health_record]
            
            # Test with filters
            response = await async_client.get(
                f"/api/v2/pets/{mock_pet_v2.id}/health-records?record_type=vaccination&start_date=2024-01-01&end_date=2024-12-31"
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response is a list of health records
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["record_type"] == "vaccination"
            
            # Verify controller was called with filters
            mock_get_records.assert_called_once()
            call_kwargs = mock_get_records.call_args[1]
            assert call_kwargs["pet_id"] == mock_pet_v2.id
            assert call_kwargs["record_type"] == HealthRecordType.VACCINATION
            assert call_kwargs["start_date"] == date(2024, 1, 1)
            assert call_kwargs["end_date"] == date(2024, 12, 31)

    async def test_mark_pet_deceased_v2_enhanced(self, async_client: AsyncClient, mock_pet_v2, mock_user):
        """Test marking pet as deceased via V2 endpoint with enhanced features."""
        vet_user = User(
            id=uuid.uuid4(),
            email="vet@example.com",
            first_name="Dr. Jane",
            last_name="Smith",
            role=UserRole.VETERINARIAN,
            is_active=True
        )
        
        with patch("app.pets.controller.PetController.mark_pet_deceased", new_callable=AsyncMock) as mock_mark_deceased, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=vet_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=vet_user):
            
            # Update mock pet to be deceased
            deceased_pet = mock_pet_v2
            deceased_pet.is_deceased = True
            deceased_pet.deceased_date = date(2024, 1, 15)
            mock_mark_deceased.return_value = deceased_pet
            
            # V2 enhanced deceased data
            deceased_data = {
                "deceased_date": "2024-01-15",
                "cause_of_death": "Natural causes",
                "notes": "Peaceful passing at home",
                "notify_owner": True
            }
            
            response = await async_client.patch(
                f"/api/v2/pets/{mock_pet_v2.id}/deceased",
                json=deceased_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v2"
            
            # Verify controller was called with V2 parameters
            mock_mark_deceased.assert_called_once()
            call_args = mock_mark_deceased.call_args
            assert call_args[1]["pet_id"] == mock_pet_v2.id
            assert call_args[1]["marked_by"] == vet_user.id

    async def test_batch_pet_operation_v2(self, async_client: AsyncClient, mock_user):
        """Test batch pet operations via V2 endpoint."""
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            role=UserRole.CLINIC_ADMIN,
            is_active=True
        )
        
        with patch("app.pets.controller.PetController.update_pet", new_callable=AsyncMock) as mock_update_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=admin_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=admin_user):
            
            mock_update_pet.return_value = mock_user  # Mock return value
            
            batch_data = {
                "pet_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
                "operation": "activate",
                "operation_data": None
            }
            
            response = await async_client.post(
                "/api/v2/pets/batch",
                json=batch_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v2"
            assert "data" in data
            
            # Verify batch operation results
            batch_result = data["data"]
            assert batch_result["operation"] == "activate"
            assert batch_result["total_requested"] == 2
            assert "successful" in batch_result
            assert "failed" in batch_result

    async def test_get_pet_by_microchip_v2_enhanced(self, async_client: AsyncClient, mock_pet_v2, mock_user):
        """Test pet retrieval by microchip via V2 endpoint with enhanced features."""
        with patch("app.pets.controller.PetController.get_pet_by_microchip", new_callable=AsyncMock) as mock_get_by_chip, \
             patch("app.pets.controller.PetController.get_pet_by_id", new_callable=AsyncMock) as mock_get_by_id, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_by_chip.return_value = mock_pet_v2
            mock_get_by_id.return_value = mock_pet_v2
            
            # Test with V2 enhanced parameters
            response = await async_client.get(
                f"/api/v2/pets/microchip/{mock_pet_v2.microchip_id}?include_health_records=true&include_owner=true"
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v2"
            
            # Verify both methods were called (first to find pet, then to get enhanced data)
            mock_get_by_chip.assert_called_once()
            mock_get_by_id.assert_called_once()

    async def test_update_pet_v2_enhanced_fields(self, async_client: AsyncClient, mock_pet_v2, mock_user):
        """Test pet update via V2 endpoint with enhanced fields."""
        with patch("app.pets.controller.PetController.update_pet", new_callable=AsyncMock) as mock_update_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            mock_update_pet.return_value = mock_pet_v2
            
            # V2 enhanced update data
            update_data = {
                "name": "Buddy Updated",
                "temperament": "Very friendly",
                "additional_photos": ["https://example.com/new_photo.jpg"],
                "emergency_contact": {
                    "name": "Jane Doe",
                    "phone": "555-0456",
                    "relationship": "Emergency Contact"
                },
                "insurance_info": {
                    "provider": "New Pet Insurance",
                    "policy_number": "NPI789012"
                }
            }
            
            response = await async_client.put(
                f"/api/v2/pets/{mock_pet_v2.id}",
                json=update_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v2"
            
            # Verify controller was called correctly
            mock_update_pet.assert_called_once()

    async def test_validation_errors_v2(self, async_client: AsyncClient, mock_user):
        """Test validation errors in V2 endpoints."""
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            # Test invalid health record data
            invalid_health_record = {
                "record_type": "invalid_type",
                "title": "",  # Empty title
                "record_date": "2025-01-01"  # Future date
            }
            
            response = await async_client.post(
                f"/api/v2/pets/{uuid.uuid4()}/health-records",
                json=invalid_health_record
            )
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_batch_operation_validation_v2(self, async_client: AsyncClient, mock_user):
        """Test batch operation validation in V2."""
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            role=UserRole.CLINIC_ADMIN,
            is_active=True
        )
        
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=admin_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=admin_user):
            
            # Test invalid batch operation
            invalid_batch_data = {
                "pet_ids": [],  # Empty list
                "operation": "invalid_operation"
            }
            
            response = await async_client.post(
                "/api/v2/pets/batch",
                json=invalid_batch_data
            )
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY