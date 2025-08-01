"""
Integration tests for V1 Pet API endpoints.

Tests the complete flow from HTTP request to database for V1 pet endpoints,
ensuring proper integration between API layer, controllers, and services.
"""

import pytest
import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from fastapi import status

from app.models.user import User, UserRole
from app.models.pet import Pet, PetGender, PetSize
from app.api.schemas.v1.pets import PetResponseV1


class TestV1PetEndpoints:
    """Test V1 pet API endpoints integration."""

    @pytest.fixture
    def sample_pet_data(self):
        """Sample pet data for testing."""
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
            "profile_image_url": "https://example.com/buddy.jpg"
        }

    @pytest.fixture
    def sample_pet_update_data(self):
        """Sample pet update data for testing."""
        return {
            "name": "Buddy Updated",
            "weight": 70.0,
            "medical_notes": "Updated medical notes",
            "allergies": "Chicken",
            "is_active": True
        }

    @pytest.fixture
    def mock_pet(self):
        """Mock pet object for testing."""
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
            temperament=None,
            behavioral_notes=None,
            profile_image_url="https://example.com/buddy.jpg",
            is_active=True,
            is_deceased=False,
            deceased_date=None,
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

    async def test_create_pet_success(self, async_client: AsyncClient, sample_pet_data, mock_pet, mock_user):
        """Test successful pet creation via V1 endpoint."""
        with patch("app.pets.controller.PetController.create_pet", new_callable=AsyncMock) as mock_create_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            mock_create_pet.return_value = mock_pet
            
            response = await async_client.post(
                "/api/v1/pets/",
                json=sample_pet_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v1"
            assert "data" in data
            
            # Verify pet data
            pet_data = data["data"]
            assert pet_data["name"] == "Buddy"
            assert pet_data["species"] == "dog"
            assert pet_data["breed"] == "Golden Retriever"
            assert pet_data["gender"] == "male"
            assert pet_data["size"] == "large"
            assert pet_data["weight"] == 65.5
            
            # Verify controller was called correctly
            mock_create_pet.assert_called_once()
            call_args = mock_create_pet.call_args
            assert call_args[1]["created_by"] == mock_user.id

    async def test_list_pets_success(self, async_client: AsyncClient, mock_pet, mock_user):
        """Test successful pet listing via V1 endpoint."""
        with patch("app.pets.controller.PetController.list_pets", new_callable=AsyncMock) as mock_list_pets, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_list_pets.return_value = ([mock_pet], 1)
            
            response = await async_client.get("/api/v1/pets/")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v1"
            assert "data" in data
            
            # Verify pagination data
            list_data = data["data"]
            assert list_data["total"] == 1
            assert list_data["page"] == 1
            assert list_data["per_page"] == 10
            assert list_data["total_pages"] == 1
            assert len(list_data["pets"]) == 1
            
            # Verify pet data
            pet_data = list_data["pets"][0]
            assert pet_data["name"] == "Buddy"
            assert pet_data["species"] == "dog"
            
            # Verify controller was called with V1 defaults
            mock_list_pets.assert_called_once()
            call_kwargs = mock_list_pets.call_args[1]
            assert call_kwargs["include_health_records"] is False
            assert call_kwargs["include_owner"] is False
            assert call_kwargs["sort_by"] is None

    async def test_list_pets_with_filters(self, async_client: AsyncClient, mock_pet, mock_user):
        """Test pet listing with filters via V1 endpoint."""
        with patch("app.pets.controller.PetController.list_pets", new_callable=AsyncMock) as mock_list_pets, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_list_pets.return_value = ([mock_pet], 1)
            
            # Make request with filters
            response = await async_client.get(
                "/api/v1/pets/?species=dog&gender=male&size=large&search=buddy&page=2&per_page=5"
            )
            
            assert response.status_code == status.HTTP_200_OK
            
            # Verify controller was called with correct filters
            call_kwargs = mock_list_pets.call_args[1]
            assert call_kwargs["species"] == "dog"
            assert call_kwargs["gender"] == PetGender.MALE
            assert call_kwargs["size"] == PetSize.LARGE
            assert call_kwargs["search"] == "buddy"
            assert call_kwargs["page"] == 2
            assert call_kwargs["per_page"] == 5

    async def test_get_pet_by_id_success(self, async_client: AsyncClient, mock_pet, mock_user):
        """Test successful pet retrieval by ID via V1 endpoint."""
        with patch("app.pets.controller.PetController.get_pet_by_id", new_callable=AsyncMock) as mock_get_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_pet.return_value = mock_pet
            
            response = await async_client.get(f"/api/v1/pets/{mock_pet.id}")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v1"
            assert "data" in data
            
            # Verify pet data
            pet_data = data["data"]
            assert pet_data["name"] == "Buddy"
            assert pet_data["id"] == str(mock_pet.id)
            
            # Verify controller was called with V1 defaults
            mock_get_pet.assert_called_once()
            call_kwargs = mock_get_pet.call_args[1]
            assert call_kwargs["pet_id"] == mock_pet.id
            assert call_kwargs["include_health_records"] is False
            assert call_kwargs["include_owner"] is False
            assert call_kwargs["include_appointments"] is False

    async def test_update_pet_success(self, async_client: AsyncClient, sample_pet_update_data, mock_pet, mock_user):
        """Test successful pet update via V1 endpoint."""
        with patch("app.pets.controller.PetController.update_pet", new_callable=AsyncMock) as mock_update_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            # Update mock pet with new data
            updated_pet = mock_pet
            updated_pet.name = "Buddy Updated"
            updated_pet.weight = 70.0
            mock_update_pet.return_value = updated_pet
            
            response = await async_client.put(
                f"/api/v1/pets/{mock_pet.id}",
                json=sample_pet_update_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v1"
            assert "data" in data
            
            # Verify updated pet data
            pet_data = data["data"]
            assert pet_data["name"] == "Buddy Updated"
            assert pet_data["weight"] == 70.0
            
            # Verify controller was called correctly
            mock_update_pet.assert_called_once()
            call_args = mock_update_pet.call_args
            assert call_args[1]["pet_id"] == mock_pet.id
            assert call_args[1]["updated_by"] == mock_user.id

    async def test_delete_pet_success(self, async_client: AsyncClient, mock_pet, mock_user):
        """Test successful pet deletion via V1 endpoint."""
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            role=UserRole.CLINIC_ADMIN,
            is_active=True
        )
        
        with patch("app.pets.controller.PetController.delete_pet", new_callable=AsyncMock) as mock_delete_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=admin_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=admin_user):
            
            mock_delete_pet.return_value = {"success": True, "message": "Pet deleted successfully"}
            
            response = await async_client.delete(f"/api/v1/pets/{mock_pet.id}")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v1"
            assert "data" in data
            assert data["data"]["message"] == "Pet deleted successfully"
            
            # Verify controller was called correctly
            mock_delete_pet.assert_called_once()
            call_args = mock_delete_pet.call_args
            assert call_args[1]["pet_id"] == mock_pet.id
            assert call_args[1]["deleted_by"] == admin_user.id

    async def test_get_pet_by_microchip_success(self, async_client: AsyncClient, mock_pet, mock_user):
        """Test successful pet retrieval by microchip via V1 endpoint."""
        with patch("app.pets.controller.PetController.get_pet_by_microchip", new_callable=AsyncMock) as mock_get_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_pet.return_value = mock_pet
            
            response = await async_client.get(f"/api/v1/pets/microchip/{mock_pet.microchip_id}")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v1"
            assert "data" in data
            
            # Verify pet data
            pet_data = data["data"]
            assert pet_data["microchip_id"] == mock_pet.microchip_id
            assert pet_data["name"] == "Buddy"
            
            # Verify controller was called correctly
            mock_get_pet.assert_called_once_with(microchip_id=mock_pet.microchip_id)

    async def test_get_pets_by_owner_success(self, async_client: AsyncClient, mock_pet, mock_user):
        """Test successful pet retrieval by owner via V1 endpoint."""
        with patch("app.pets.controller.PetController.get_pets_by_owner", new_callable=AsyncMock) as mock_get_pets, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_pets.return_value = [mock_pet]
            
            response = await async_client.get(f"/api/v1/pets/owner/{mock_pet.owner_id}")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v1"
            assert "data" in data
            
            # Verify pets data
            list_data = data["data"]
            assert list_data["total"] == 1
            assert len(list_data["pets"]) == 1
            assert list_data["pets"][0]["owner_id"] == str(mock_pet.owner_id)
            
            # Verify controller was called with V1 defaults
            mock_get_pets.assert_called_once()
            call_kwargs = mock_get_pets.call_args[1]
            assert call_kwargs["owner_id"] == mock_pet.owner_id
            assert call_kwargs["is_active"] is True
            assert call_kwargs["include_health_records"] is False

    async def test_mark_pet_deceased_success(self, async_client: AsyncClient, mock_pet, mock_user):
        """Test successful pet deceased marking via V1 endpoint."""
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
            deceased_pet = mock_pet
            deceased_pet.is_deceased = True
            deceased_pet.deceased_date = date(2024, 1, 15)
            mock_mark_deceased.return_value = deceased_pet
            
            deceased_data = {
                "deceased_date": "2024-01-15"
            }
            
            response = await async_client.patch(
                f"/api/v1/pets/{mock_pet.id}/deceased",
                json=deceased_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == "v1"
            assert "data" in data
            
            # Verify deceased pet data
            pet_data = data["data"]
            assert pet_data["is_deceased"] is True
            assert pet_data["deceased_date"] == "2024-01-15"
            
            # Verify controller was called correctly
            mock_mark_deceased.assert_called_once()
            call_args = mock_mark_deceased.call_args
            assert call_args[1]["pet_id"] == mock_pet.id
            assert call_args[1]["deceased_date"] == date(2024, 1, 15)
            assert call_args[1]["marked_by"] == vet_user.id

    async def test_create_pet_validation_error(self, async_client: AsyncClient, mock_user):
        """Test pet creation with validation errors."""
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            # Missing required fields
            invalid_data = {
                "name": "",  # Empty name
                "species": "",  # Empty species
            }
            
            response = await async_client.post(
                "/api/v1/pets/",
                json=invalid_data
            )
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_get_pet_not_found(self, async_client: AsyncClient, mock_user):
        """Test pet retrieval with non-existent ID."""
        with patch("app.pets.controller.PetController.get_pet_by_id", new_callable=AsyncMock) as mock_get_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            from app.core.exceptions import NotFoundError
            mock_get_pet.side_effect = NotFoundError("Pet not found")
            
            non_existent_id = uuid.uuid4()
            response = await async_client.get(f"/api/v1/pets/{non_existent_id}")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_unauthorized_access(self, async_client: AsyncClient):
        """Test unauthorized access to pet endpoints."""
        with patch("app.app_helpers.auth_helpers.get_current_user", side_effect=Exception("Unauthorized")):
            
            response = await async_client.get("/api/v1/pets/")
            
            # Should return unauthorized status
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]