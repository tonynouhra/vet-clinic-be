"""
Migrated Dynamic Pet CRUD Tests - Complete Version-Agnostic API Testing.

This file replaces test_v1_pet_endpoints.py and test_v2_pet_endpoints.py with
a unified dynamic testing approach that automatically adapts to version-specific
features, fields, and behaviors while maintaining equivalent test coverage.

This migration demonstrates how the dynamic testing framework eliminates code
duplication while providing equivalent test coverage across API versions.
"""

import pytest
import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from fastapi import status

from app.models.user import User
from app.models.pet import Pet, PetGender, PetSize, HealthRecord, HealthRecordType
from tests.dynamic.base_test import BaseVersionTest
from tests.dynamic.decorators import version_parametrize, feature_test, crud_test
from tests.dynamic.data_factory import TestDataFactory


class TestPetsDynamicMigrated(BaseVersionTest):
    """
    Comprehensive dynamic pet CRUD tests that replace both v1 and v2 specific tests.
    
    This class provides equivalent coverage to the original test_v1_pet_endpoints.py
    and test_v2_pet_endpoints.py files while using the dynamic testing framework
    to eliminate code duplication and automatically handle version differences.
    """

    @pytest.fixture
    async def async_client(self):
        """Async HTTP client fixture."""
        from app.main import app
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            yield client
    @pytest.fixture
    def test_data_factory(self):
        """Test data factory fixture."""
        return TestDataFactory()



    @pytest.fixture
    def mock_user(self):
        """Mock user for authentication (veterinarian role)."""
        return User(
            id=uuid.uuid4(),
            clerk_id="vet_clerk_123",
            email="vet@example.com",
            first_name="Dr. Jane",
            last_name="Smith",
            is_active=True,
            is_verified=True
        )

    @pytest.fixture
    def admin_user(self):
        """Mock admin user for privileged operations."""
        return User(
            id=uuid.uuid4(),
            clerk_id="admin_clerk_123",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_verified=True
        )

    @pytest.fixture
    def vet_user(self):
        """Mock veterinarian user for specific operations."""
        return User(
            id=uuid.uuid4(),
            clerk_id="vet_clerk_456",
            email="vet2@example.com",
            first_name="Dr. John",
            last_name="Doe",
            is_active=True,
            is_verified=True
        )

    def create_mock_pet(self, api_version: str, test_data_factory: TestDataFactory, **overrides) -> Pet:
        """Create a mock pet object with version-appropriate data."""
        pet_data = test_data_factory.build_pet_data(api_version, **overrides)
        
        # Create base pet object
        pet = Pet(
            id=uuid.uuid4(),
            owner_id=uuid.UUID(pet_data["owner_id"]),
            name=pet_data["name"],
            species=pet_data["species"],
            breed=pet_data.get("breed", "Mixed"),
            mixed_breed=pet_data.get("mixed_breed", False),
            gender=PetGender.MALE if pet_data.get("gender", "male").upper() == "MALE" else PetGender.FEMALE,
            size=PetSize.LARGE,
            weight=pet_data.get("weight", 50.0),
            color=pet_data.get("color", "Brown"),
            birth_date=date(2020, 1, 15),
            age_years=pet_data.get("age_years", 4),
            age_months=pet_data.get("age_months", 0),
            is_age_estimated=pet_data.get("is_age_estimated", False),
            microchip_id=pet_data.get("microchip_id", "123456789012345"),
            medical_notes=pet_data.get("medical_notes", "No known allergies"),
            allergies=pet_data.get("allergies"),
            current_medications=pet_data.get("current_medications"),
            special_needs=pet_data.get("special_needs"),
            profile_image_url=pet_data.get("profile_image_url", "https://example.com/pet.jpg"),
            is_active=True,
            is_deceased=False,
            deceased_date=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Add version-specific fields
        if api_version == "v2":
            pet.temperament = pet_data.get("temperament", "Friendly")
            pet.behavioral_notes = pet_data.get("behavioral_notes", "Good with children")
            pet.additional_photos = pet_data.get("additional_photos", ["https://example.com/photo1.jpg"])
        
        return pet

    def create_mock_health_record(self) -> HealthRecord:
        """Create a mock health record for v2 testing."""
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

    # ========================================
    # Pet Creation Tests
    # ========================================

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_create_pet_success(self, api_version: str, async_client: AsyncClient, 
                                    test_data_factory: TestDataFactory, mock_user):
        """Test successful pet creation across all versions."""
        # Generate version-appropriate test data
        pet_data = test_data_factory.build_pet_data(api_version)
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        
        # Get endpoint URL for this version
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        
        with patch("app.pets.controller.PetController.create_pet", new_callable=AsyncMock) as mock_create_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            mock_create_pet.return_value = mock_pet
            
            response = await self.make_request("POST", endpoint_url, async_client, json=pet_data)
            
            # Assert successful creation
            self.assert_status_code(response, 201, f"Creating pet in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Validate version-specific response fields
            pet_response = data["data"]
            self.validate_response_structure(pet_response, api_version, "pet", "response")
            
            # Verify required fields are present
            assert pet_response["name"] == pet_data["name"]
            assert pet_response["species"] == pet_data["species"]
            assert pet_response["owner_id"] == pet_data["owner_id"]
            
            # Verify version-specific fields
            if api_version == "v2":
                if "temperament" in pet_data:
                    assert "temperament" in pet_response
                if "behavioral_notes" in pet_data:
                    assert "behavioral_notes" in pet_response
                if "emergency_contact" in pet_data:
                    assert "emergency_contact" in pet_response
                if "additional_photos" in pet_data:
                    assert "additional_photos" in pet_response
            else:
                # v1 should not have v2-specific fields
                assert "temperament" not in pet_response
                assert "behavioral_notes" not in pet_response
                assert "emergency_contact" not in pet_response
                assert "additional_photos" not in pet_response
            
            # Verify controller was called correctly
            mock_create_pet.assert_called_once()
            call_args = mock_create_pet.call_args
            assert call_args[1]["created_by"] == mock_user.id

    @version_parametrize()
    async def test_create_pet_validation_error(self, api_version: str, async_client: AsyncClient, 
                                             test_data_factory: TestDataFactory, mock_user):
        """Test pet creation with validation errors across all versions."""
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            # Test with missing required fields
            invalid_data = {
                "name": "",  # Empty name should fail validation
                "species": "",  # Empty species should fail validation
            }
            
            response = await self.make_request("POST", endpoint_url, async_client, json=invalid_data)
            
            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # ========================================
    # Pet Retrieval Tests
    # ========================================

    @version_parametrize()
    async def test_get_pet_by_id_success(self, api_version: str, async_client: AsyncClient,
                                       test_data_factory: TestDataFactory, mock_user):
        """Test successful pet retrieval by ID across all versions."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        endpoint_url = self.get_endpoint_url(api_version, "pets", str(mock_pet.id))
        
        with patch("app.pets.controller.PetController.get_pet_by_id", new_callable=AsyncMock) as mock_get_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_pet.return_value = mock_pet
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Assert successful retrieval
            self.assert_status_code(response, 200, f"Getting pet by ID in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Validate version-specific response fields
            pet_response = data["data"]
            self.validate_response_structure(pet_response, api_version, "pet", "response")
            self.validate_version_specific_fields(pet_response, api_version, "pet")
            
            # Verify pet data
            assert pet_response["id"] == str(mock_pet.id)
            assert pet_response["name"] == mock_pet.name
            assert pet_response["species"] == mock_pet.species
            
            # Verify controller was called with version-appropriate parameters
            mock_get_pet.assert_called_once()
            call_kwargs = mock_get_pet.call_args[1]
            assert call_kwargs["pet_id"] == mock_pet.id
            
            # Check version-specific parameters
            if api_version == "v1":
                assert call_kwargs.get("include_health_records", True) is False
                assert call_kwargs.get("include_owner", True) is False
                assert call_kwargs.get("include_appointments", True) is False
            elif api_version == "v2":
                # v2 might have different defaults or support these parameters
                pass

    @version_parametrize()
    async def test_get_pet_not_found(self, api_version: str, async_client: AsyncClient, mock_user):
        """Test pet retrieval with non-existent ID across all versions."""
        non_existent_id = uuid.uuid4()
        endpoint_url = self.get_endpoint_url(api_version, "pets", str(non_existent_id))
        
        with patch("app.pets.controller.PetController.get_pet_by_id", new_callable=AsyncMock) as mock_get_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            from app.core.exceptions import NotFoundError
            mock_get_pet.side_effect = NotFoundError("Pet not found")
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Should return 404
            self.assert_status_code(response, 404, f"Getting non-existent pet in {api_version}")

    # ========================================
    # Pet Listing Tests
    # ========================================

    @version_parametrize()
    async def test_list_pets_success(self, api_version: str, async_client: AsyncClient,
                                   test_data_factory: TestDataFactory, mock_user):
        """Test successful pet listing across all versions."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        
        with patch("app.pets.controller.PetController.list_pets", new_callable=AsyncMock) as mock_list_pets, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_list_pets.return_value = ([mock_pet], 1)
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Assert successful listing
            self.assert_status_code(response, 200, f"Listing pets in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Verify pagination data
            list_data = data["data"]
            assert list_data["total"] == 1
            assert list_data["page"] == 1
            assert list_data["per_page"] == 10
            assert list_data["total_pages"] == 1
            assert len(list_data["pets"]) == 1
            
            # Validate pet response structure
            pet_response = list_data["pets"][0]
            self.validate_response_structure(pet_response, api_version, "pet", "response")
            self.validate_version_specific_fields(pet_response, api_version, "pet")
            
            # Verify controller was called with version-appropriate defaults
            mock_list_pets.assert_called_once()
            call_kwargs = mock_list_pets.call_args[1]
            
            if api_version == "v1":
                assert call_kwargs.get("include_health_records", True) is False
                assert call_kwargs.get("include_owner", True) is False
                assert call_kwargs.get("sort_by") is None
            elif api_version == "v2":
                # v2 might have different defaults
                pass

    @version_parametrize()
    async def test_list_pets_with_filters(self, api_version: str, async_client: AsyncClient,
                                        test_data_factory: TestDataFactory, mock_user):
        """Test pet listing with filters across all versions."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        
        with patch("app.pets.controller.PetController.list_pets", new_callable=AsyncMock) as mock_list_pets, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_list_pets.return_value = ([mock_pet], 1)
            
            # Test with common filters available in all versions
            query_params = "?species=dog&gender=male&size=large&search=buddy&page=2&per_page=5"
            response = await self.make_request("GET", f"{endpoint_url}{query_params}", async_client)
            
            # Assert successful listing with filters
            self.assert_status_code(response, 200, f"Listing pets with filters in {api_version}")
            
            # Verify controller was called with correct filters
            mock_list_pets.assert_called_once()
            call_kwargs = mock_list_pets.call_args[1]
            assert call_kwargs["species"] == "dog"
            assert call_kwargs["gender"] == PetGender.MALE
            assert call_kwargs["size"] == PetSize.LARGE
            assert call_kwargs["search"] == "buddy"
            assert call_kwargs["page"] == 2
            assert call_kwargs["per_page"] == 5

    # ========================================
    # Pet Update Tests
    # ========================================

    @version_parametrize()
    async def test_update_pet_success(self, api_version: str, async_client: AsyncClient,
                                    test_data_factory: TestDataFactory, mock_user):
        """Test successful pet update across all versions."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        endpoint_url = self.get_endpoint_url(api_version, "pets", str(mock_pet.id))
        
        # Generate version-appropriate update data
        update_data = test_data_factory.build_update_data(api_version, "pet", 
                                                        name="Updated Pet Name",
                                                        weight=75.0,
                                                        medical_notes="Updated medical notes",
                                                        allergies="Chicken",
                                                        is_active=True)
        
        with patch("app.pets.controller.PetController.update_pet", new_callable=AsyncMock) as mock_update_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            # Update mock pet with new data
            updated_pet = mock_pet
            updated_pet.name = "Updated Pet Name"
            updated_pet.weight = 75.0
            mock_update_pet.return_value = updated_pet
            
            response = await self.make_request("PUT", endpoint_url, async_client, json=update_data)
            
            # Assert successful update
            self.assert_status_code(response, 200, f"Updating pet in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Validate updated pet response
            pet_response = data["data"]
            self.validate_response_structure(pet_response, api_version, "pet", "response")
            
            # Verify updated fields
            assert pet_response["name"] == "Updated Pet Name"
            assert pet_response["weight"] == 75.0
            
            # Verify controller was called correctly
            mock_update_pet.assert_called_once()
            call_args = mock_update_pet.call_args
            assert call_args[1]["pet_id"] == mock_pet.id
            assert call_args[1]["updated_by"] == mock_user.id

    # ========================================
    # Pet Deletion Tests
    # ========================================

    @version_parametrize()
    async def test_delete_pet_success(self, api_version: str, async_client: AsyncClient,
                                    test_data_factory: TestDataFactory, admin_user):
        """Test successful pet deletion across all versions."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        endpoint_url = self.get_endpoint_url(api_version, "pets", str(mock_pet.id))
        
        with patch("app.pets.controller.PetController.delete_pet", new_callable=AsyncMock) as mock_delete_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=admin_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=admin_user):
            
            mock_delete_pet.return_value = {"success": True, "message": "Pet deleted successfully"}
            
            response = await self.make_request("DELETE", endpoint_url, async_client)
            
            # Assert successful deletion
            self.assert_status_code(response, 200, f"Deleting pet in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            assert data["data"]["message"] == "Pet deleted successfully"
            
            # Verify controller was called correctly
            mock_delete_pet.assert_called_once()
            call_args = mock_delete_pet.call_args
            assert call_args[1]["pet_id"] == mock_pet.id
            assert call_args[1]["deleted_by"] == admin_user.id

    # ========================================
    # Microchip-based Retrieval Tests
    # ========================================

    @version_parametrize()
    async def test_get_pet_by_microchip_success(self, api_version: str, async_client: AsyncClient,
                                              test_data_factory: TestDataFactory, mock_user):
        """Test successful pet retrieval by microchip across all versions."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        microchip_id = "123456789012345"
        endpoint_url = self.get_endpoint_url(api_version, "pets") + f"/microchip/{microchip_id}"
        
        with patch("app.pets.controller.PetController.get_pet_by_microchip", new_callable=AsyncMock) as mock_get_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_pet.return_value = mock_pet
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Assert successful retrieval
            self.assert_status_code(response, 200, f"Getting pet by microchip in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Validate pet response
            pet_response = data["data"]
            self.validate_response_structure(pet_response, api_version, "pet", "response")
            assert pet_response["microchip_id"] == microchip_id
            
            # Verify controller was called correctly
            mock_get_pet.assert_called_once_with(microchip_id=microchip_id)

    # ========================================
    # Owner-based Retrieval Tests
    # ========================================

    @version_parametrize()
    async def test_get_pets_by_owner_success(self, api_version: str, async_client: AsyncClient,
                                           test_data_factory: TestDataFactory, mock_user):
        """Test successful pet retrieval by owner across all versions."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        owner_id = mock_pet.owner_id
        endpoint_url = self.get_endpoint_url(api_version, "pets") + f"/owner/{owner_id}"
        
        with patch("app.pets.controller.PetController.get_pets_by_owner", new_callable=AsyncMock) as mock_get_pets, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_pets.return_value = [mock_pet]
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Assert successful retrieval
            self.assert_status_code(response, 200, f"Getting pets by owner in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Verify pets data
            list_data = data["data"]
            assert list_data["total"] == 1
            assert len(list_data["pets"]) == 1
            assert list_data["pets"][0]["owner_id"] == str(owner_id)
            
            # Verify controller was called with version-appropriate parameters
            mock_get_pets.assert_called_once()
            call_kwargs = mock_get_pets.call_args[1]
            assert call_kwargs["owner_id"] == owner_id
            assert call_kwargs["is_active"] is True
            
            if api_version == "v1":
                assert call_kwargs.get("include_health_records", True) is False

    # ========================================
    # Pet Deceased Marking Tests
    # ========================================

    @version_parametrize()
    async def test_mark_pet_deceased_success(self, api_version: str, async_client: AsyncClient,
                                           test_data_factory: TestDataFactory, vet_user):
        """Test successful pet deceased marking across all versions."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        endpoint_url = self.get_endpoint_url(api_version, "pets", str(mock_pet.id)) + "/deceased"
        
        with patch("app.pets.controller.PetController.mark_pet_deceased", new_callable=AsyncMock) as mock_mark_deceased, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=vet_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=vet_user):
            
            # Update mock pet to be deceased
            deceased_pet = mock_pet
            deceased_pet.is_deceased = True
            deceased_pet.deceased_date = date(2024, 1, 15)
            mock_mark_deceased.return_value = deceased_pet
            
            # Base deceased data (common to all versions)
            deceased_data = {
                "deceased_date": "2024-01-15"
            }
            
            # Add version-specific fields for v2
            if api_version == "v2":
                deceased_data.update({
                    "cause_of_death": "Natural causes",
                    "notes": "Peaceful passing at home",
                    "notify_owner": True
                })
            
            response = await self.make_request("PATCH", endpoint_url, async_client, json=deceased_data)
            
            # Assert successful deceased marking
            self.assert_status_code(response, 200, f"Marking pet deceased in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
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

    # ========================================
    # Authorization Tests
    # ========================================

    @version_parametrize()
    async def test_unauthorized_access(self, api_version: str, async_client: AsyncClient):
        """Test unauthorized access to pet endpoints across all versions."""
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        
        with patch("app.app_helpers.auth_helpers.get_current_user", side_effect=Exception("Unauthorized")):
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Should return unauthorized status
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]

    # ========================================
    # V2-Specific Feature Tests
    # ========================================

    @feature_test("enhanced_filtering")
    async def test_list_pets_with_enhanced_filters(self, api_version: str, async_client: AsyncClient,
                                                  test_data_factory: TestDataFactory, mock_user):
        """Test pet listing with enhanced filters (v2+ only)."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        
        with patch("app.pets.controller.PetController.list_pets", new_callable=AsyncMock) as mock_list_pets, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_list_pets.return_value = ([mock_pet], 1)
            
            # Test with enhanced filters only available in v2+
            query_params = "?include_health_records=true&include_owner=true&sort_by=name&include_statistics=true"
            response = await self.make_request("GET", f"{endpoint_url}{query_params}", async_client)
            
            # Assert successful listing with enhanced filters
            self.assert_status_code(response, 200, f"Listing pets with enhanced filters in {api_version}")
            
            data = response.json()
            
            # Verify V2 enhanced response features
            list_data = data["data"]
            if api_version == "v2":
                assert "statistics" in list_data
                assert "filters_applied" in list_data
                assert list_data["statistics"] is not None
            
            # Verify controller was called with enhanced parameters
            mock_list_pets.assert_called_once()
            call_kwargs = mock_list_pets.call_args[1]
            assert call_kwargs.get("include_health_records") is True
            assert call_kwargs.get("include_owner") is True
            assert call_kwargs.get("sort_by") == "name"

    @feature_test("statistics")
    async def test_get_pet_statistics(self, api_version: str, async_client: AsyncClient,
                                    test_data_factory: TestDataFactory, mock_user):
        """Test pet statistics endpoint (v2+ only)."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        endpoint_url = self.get_endpoint_url(api_version, "pets", str(mock_pet.id)) + "/stats"
        
        with patch("app.pets.controller.PetController.get_pet_by_id", new_callable=AsyncMock) as mock_get_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            # Mock pet with health records and appointments for statistics
            mock_pet.health_records = []
            mock_pet.appointments = []
            mock_get_pet.return_value = mock_pet
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Assert successful statistics retrieval
            self.assert_status_code(response, 200, f"Getting pet statistics in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Verify statistics data
            stats_data = data["data"]
            assert "total_health_records" in stats_data
            assert "total_appointments" in stats_data
            assert "days_since_registration" in stats_data
            assert "last_checkup_date" in stats_data
            assert "next_due_vaccination" in stats_data

    @feature_test("health_records")
    async def test_add_health_record(self, api_version: str, async_client: AsyncClient,
                                   test_data_factory: TestDataFactory, mock_user):
        """Test adding health record (v2+ only)."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        mock_health_record = self.create_mock_health_record()
        endpoint_url = self.get_endpoint_url(api_version, "pets", str(mock_pet.id)) + "/health-records"
        
        health_record_data = test_data_factory.build_health_record_data(api_version)
        
        with patch("app.pets.controller.PetController.add_health_record", new_callable=AsyncMock) as mock_add_record, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            mock_add_record.return_value = mock_health_record
            
            response = await self.make_request("POST", endpoint_url, async_client, json=health_record_data)
            
            # Assert successful health record creation
            self.assert_status_code(response, 201, f"Adding health record in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Verify health record data
            record_data = data["data"]
            assert record_data["record_type"] == "vaccination"
            assert record_data["title"] == "Annual Rabies Vaccination"
            assert record_data["medication_name"] == "Rabies Vaccine"
            
            # Verify controller was called correctly
            mock_add_record.assert_called_once()
            call_args = mock_add_record.call_args
            assert call_args[1]["pet_id"] == mock_pet.id
            assert call_args[1]["created_by"] == mock_user.id

    @feature_test("health_records")
    async def test_get_pet_health_records(self, api_version: str, async_client: AsyncClient,
                                        test_data_factory: TestDataFactory, mock_user):
        """Test retrieving pet health records (v2+ only)."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        mock_health_record = self.create_mock_health_record()
        endpoint_url = self.get_endpoint_url(api_version, "pets", str(mock_pet.id)) + "/health-records"
        
        with patch("app.pets.controller.PetController.get_pet_health_records", new_callable=AsyncMock) as mock_get_records, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_records.return_value = [mock_health_record]
            
            # Test with filters
            query_params = "?record_type=vaccination&start_date=2024-01-01&end_date=2024-12-31"
            response = await self.make_request("GET", f"{endpoint_url}{query_params}", async_client)
            
            # Assert successful health records retrieval
            self.assert_status_code(response, 200, f"Getting pet health records in {api_version}")
            
            data = response.json()
            
            # Verify response is a list of health records
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["record_type"] == "vaccination"
            
            # Verify controller was called with filters
            mock_get_records.assert_called_once()
            call_kwargs = mock_get_records.call_args[1]
            assert call_kwargs["pet_id"] == mock_pet.id
            assert call_kwargs["record_type"] == HealthRecordType.VACCINATION
            assert call_kwargs["start_date"] == date(2024, 1, 1)
            assert call_kwargs["end_date"] == date(2024, 12, 31)

    @feature_test("batch_operations")
    async def test_batch_pet_operation(self, api_version: str, async_client: AsyncClient, admin_user):
        """Test batch pet operations (v2+ only)."""
        endpoint_url = self.get_endpoint_url(api_version, "pets") + "/batch"
        
        with patch("app.pets.controller.PetController.update_pet", new_callable=AsyncMock) as mock_update_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=admin_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=admin_user):
            
            mock_update_pet.return_value = admin_user  # Mock return value
            
            batch_data = {
                "pet_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
                "operation": "activate",
                "operation_data": None
            }
            
            response = await self.make_request("POST", endpoint_url, async_client, json=batch_data)
            
            # Assert successful batch operation
            self.assert_status_code(response, 200, f"Batch pet operation in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Verify batch operation results
            batch_result = data["data"]
            assert batch_result["operation"] == "activate"
            assert batch_result["total_requested"] == 2
            assert "successful" in batch_result
            assert "failed" in batch_result

    # ========================================
    # Enhanced V2 Retrieval Tests
    # ========================================

    @feature_test("enhanced_filtering")
    async def test_get_pet_with_relationships(self, api_version: str, async_client: AsyncClient,
                                            test_data_factory: TestDataFactory, mock_user):
        """Test pet retrieval with relationship data (v2+ only)."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        endpoint_url = self.get_endpoint_url(api_version, "pets", str(mock_pet.id))
        
        with patch("app.pets.controller.PetController.get_pet_by_id", new_callable=AsyncMock) as mock_get_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_pet.return_value = mock_pet
            
            # Test with V2 enhanced parameters
            query_params = "?include_health_records=true&include_owner=true&include_appointments=true"
            response = await self.make_request("GET", f"{endpoint_url}{query_params}", async_client)
            
            # Assert successful retrieval
            self.assert_status_code(response, 200, f"Getting pet with relationships in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            
            # Verify controller was called with V2 parameters
            mock_get_pet.assert_called_once()
            call_kwargs = mock_get_pet.call_args[1]
            assert call_kwargs["include_health_records"] is True
            assert call_kwargs["include_owner"] is True
            assert call_kwargs["include_appointments"] is True

    @feature_test("enhanced_filtering")
    async def test_get_pet_by_microchip_enhanced(self, api_version: str, async_client: AsyncClient,
                                               test_data_factory: TestDataFactory, mock_user):
        """Test pet retrieval by microchip with enhanced features (v2+ only)."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        microchip_id = "123456789012345"
        endpoint_url = self.get_endpoint_url(api_version, "pets") + f"/microchip/{microchip_id}"
        
        with patch("app.pets.controller.PetController.get_pet_by_microchip", new_callable=AsyncMock) as mock_get_by_chip, \
             patch("app.pets.controller.PetController.get_pet_by_id", new_callable=AsyncMock) as mock_get_by_id, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_by_chip.return_value = mock_pet
            mock_get_by_id.return_value = mock_pet
            
            # Test with V2 enhanced parameters
            query_params = "?include_health_records=true&include_owner=true"
            response = await self.make_request("GET", f"{endpoint_url}{query_params}", async_client)
            
            # Assert successful retrieval
            self.assert_status_code(response, 200, f"Getting pet by microchip enhanced in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            
            # Verify both methods were called (first to find pet, then to get enhanced data)
            mock_get_by_chip.assert_called_once()
            mock_get_by_id.assert_called_once()

    # ========================================
    # Enhanced V2 Update Tests
    # ========================================

    @feature_test("enhanced_filtering")
    async def test_update_pet_enhanced_fields(self, api_version: str, async_client: AsyncClient,
                                            test_data_factory: TestDataFactory, mock_user):
        """Test pet update with enhanced fields (v2+ only)."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        endpoint_url = self.get_endpoint_url(api_version, "pets", str(mock_pet.id))
        
        with patch("app.pets.controller.PetController.update_pet", new_callable=AsyncMock) as mock_update_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            mock_update_pet.return_value = mock_pet
            
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
            
            response = await self.make_request("PUT", endpoint_url, async_client, json=update_data)
            
            # Assert successful update
            self.assert_status_code(response, 200, f"Updating pet with enhanced fields in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            
            # Verify controller was called correctly
            mock_update_pet.assert_called_once()

    # ========================================
    # Validation Error Tests
    # ========================================

    @feature_test("health_records")
    async def test_health_record_validation_errors(self, api_version: str, async_client: AsyncClient,
                                                  test_data_factory: TestDataFactory, mock_user):
        """Test validation errors in health record endpoints (v2+ only)."""
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        endpoint_url = self.get_endpoint_url(api_version, "pets", str(mock_pet.id)) + "/health-records"
        
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            # Test invalid health record data
            invalid_health_record = {
                "record_type": "invalid_type",
                "title": "",  # Empty title
                "record_date": "2025-01-01"  # Future date
            }
            
            response = await self.make_request("POST", endpoint_url, async_client, json=invalid_health_record)
            
            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @feature_test("batch_operations")
    async def test_batch_operation_validation(self, api_version: str, async_client: AsyncClient, admin_user):
        """Test batch operation validation (v2+ only)."""
        endpoint_url = self.get_endpoint_url(api_version, "pets") + "/batch"
        
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=admin_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=admin_user):
            
            # Test invalid batch operation
            invalid_batch_data = {
                "pet_ids": [],  # Empty list
                "operation": "invalid_operation"
            }
            
            response = await self.make_request("POST", endpoint_url, async_client, json=invalid_batch_data)
            
            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # ========================================
    # Comprehensive CRUD Workflow Test
    # ========================================

    @version_parametrize()
    async def test_complete_pet_crud_workflow(self, api_version: str, async_client: AsyncClient,
                                            test_data_factory: TestDataFactory, mock_user, admin_user):
        """Test complete CRUD workflow for pets across all versions."""
        # 1. Create pet
        pet_data = test_data_factory.build_pet_data(api_version)
        mock_pet = self.create_mock_pet(api_version, test_data_factory)
        
        create_url = self.get_endpoint_url(api_version, "pets")
        
        with patch("app.pets.controller.PetController.create_pet", new_callable=AsyncMock) as mock_create, \
             patch("app.pets.controller.PetController.get_pet_by_id", new_callable=AsyncMock) as mock_get, \
             patch("app.pets.controller.PetController.update_pet", new_callable=AsyncMock) as mock_update, \
             patch("app.pets.controller.PetController.delete_pet", new_callable=AsyncMock) as mock_delete, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            mock_create.return_value = mock_pet
            mock_get.return_value = mock_pet
            mock_update.return_value = mock_pet
            mock_delete.return_value = {"success": True, "message": "Pet deleted successfully"}
            
            # Create
            create_response = await self.make_request("POST", create_url, async_client, json=pet_data)
            self.assert_status_code(create_response, 201, f"CRUD Create in {api_version}")
            created_pet = create_response.json()["data"]
            pet_id = created_pet["id"]
            
            # Read
            read_url = self.get_endpoint_url(api_version, "pets", pet_id)
            read_response = await self.make_request("GET", read_url, async_client)
            self.assert_status_code(read_response, 200, f"CRUD Read in {api_version}")
            
            # Update
            update_data = test_data_factory.build_update_data(api_version, "pet", name="Updated Name")
            update_response = await self.make_request("PUT", read_url, async_client, json=update_data)
            self.assert_status_code(update_response, 200, f"CRUD Update in {api_version}")
            
            # Delete (requires admin user)
            with patch("app.app_helpers.auth_helpers.get_current_user", return_value=admin_user), \
                 patch("app.app_helpers.auth_helpers.require_role", return_value=admin_user):
                delete_response = await self.make_request("DELETE", read_url, async_client)
                self.assert_status_code(delete_response, 200, f"CRUD Delete in {api_version}")
            
            # Verify all operations were called
            mock_create.assert_called_once()
            mock_get.assert_called_once()
            mock_update.assert_called_once()
            mock_delete.assert_called_once()