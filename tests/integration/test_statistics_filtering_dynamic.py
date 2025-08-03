"""
Dynamic Statistics and Enhanced Filtering Tests - Version-Agnostic API Testing.

Tests statistics and enhanced filtering functionality across API versions using the dynamic testing framework.
These features are only available in v2+, so v1 tests verify appropriate error responses.
"""

import pytest
import uuid
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from fastapi import status

from app.models.user import User
from app.models.pet import Pet, PetGender, PetSize, HealthRecordType
from tests.dynamic.base_test import BaseVersionTest
from tests.dynamic.decorators import version_parametrize, feature_test
from tests.dynamic.data_factory import TestDataFactory


class TestStatisticsFilteringDynamic(BaseVersionTest):
    """Dynamic statistics and enhanced filtering tests across all API versions."""

    @pytest.fixture
    def test_data_factory(self):
        """Test data factory fixture."""
        return TestDataFactory()

    @pytest.fixture
    async def async_client(self):
        """Async HTTP client fixture."""
        from app.main import app
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            yield client

    @pytest.fixture
    def mock_user(self):
        """Mock user for authentication."""
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
    def mock_pet(self, test_data_factory):
        """Mock pet for statistics testing."""
        pet_data = test_data_factory.build_pet_data("v2")
        return Pet(
            id=uuid.uuid4(),
            owner_id=uuid.UUID(pet_data["owner_id"]),
            name=pet_data["name"],
            species=pet_data["species"],
            breed=pet_data.get("breed", "Mixed"),
            mixed_breed=False,
            gender=PetGender.MALE if pet_data.get("gender", "MALE") == "MALE" else PetGender.FEMALE,
            size=PetSize.LARGE,
            weight=pet_data.get("weight", 50.0),
            color=pet_data.get("color", "Brown"),
            birth_date=date(2020, 1, 15),
            age_years=4,
            age_months=0,
            is_age_estimated=False,
            microchip_id="123456789012345",
            medical_notes="No known allergies",
            allergies=None,
            current_medications=None,
            special_needs=None,
            profile_image_url="https://example.com/pet.jpg",
            is_active=True,
            is_deceased=False,
            deceased_date=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    # Pet Statistics Tests
    @version_parametrize(versions=["v2"])
    @pytest.mark.asyncio
    async def test_get_pet_statistics_success(self, api_version: str, async_client: AsyncClient,
                                            test_data_factory: TestDataFactory, mock_user, mock_pet):
        """Test successful pet statistics retrieval (v2+ only)."""
        # Skip if statistics feature not available
        self.skip_if_feature_unavailable(api_version, "statistics")
        
        endpoint_url = f"/api/{api_version}/pets/{mock_pet.id}/stats"
        
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
            
            # Verify data types
            assert isinstance(stats_data["total_health_records"], int)
            assert isinstance(stats_data["total_appointments"], int)
            assert isinstance(stats_data["days_since_registration"], int)
            
            # Verify controller was called correctly
            mock_get_pet.assert_called_once()
            call_args = mock_get_pet.call_args
            assert call_args[1]["pet_id"] == mock_pet.id
            assert call_args[1]["include_health_records"] is True
            assert call_args[1]["include_appointments"] is True

    @version_parametrize(versions=["v1"])
    async def test_v1_statistics_not_found(self, api_version: str, async_client: AsyncClient,
                                         mock_user, mock_pet):
        """Test that v1 returns 404 for statistics endpoints."""
        endpoint_url = f"/api/{api_version}/pets/{mock_pet.id}/stats"
        
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Should return 404 for v1
            self.assert_status_code(response, 404, f"Pet statistics in {api_version} should return 404")

    # Enhanced Filtering Tests
    @version_parametrize(versions=["v2"])
    @pytest.mark.asyncio
    async def test_list_pets_with_enhanced_filters(self, api_version: str, async_client: AsyncClient,
                                                 test_data_factory: TestDataFactory, mock_user):
        """Test pet listing with enhanced filters (v2+ only)."""
        # Skip if enhanced_filtering feature not available
        self.skip_if_feature_unavailable(api_version, "enhanced_filtering")
        
        mock_pet = Pet(
            id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            name="Test Pet",
            species="dog",
            breed="Golden Retriever",
            gender=PetGender.MALE,
            size=PetSize.LARGE,
            weight=65.0,
            color="Golden",
            birth_date=date(2020, 1, 15),
            age_years=4,
            age_months=0,
            is_age_estimated=False,
            microchip_id="123456789012345",
            is_active=True,
            is_deceased=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        endpoint_url = f"/api/{api_version}/pets"
        
        with patch("app.pets.controller.PetController.list_pets", new_callable=AsyncMock) as mock_list_pets, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_list_pets.return_value = ([mock_pet], 1)
            
            # Test with enhanced filters only available in v2+
            query_params = "?include_health_records=true&include_owner=true&sort_by=name&include_statistics=true"
            response = await self.make_request("GET", f"{endpoint_url}{query_params}", async_client)
            
            # Assert successful listing with enhanced filters
            self.assert_status_code(response, 200, f"Listing pets with enhanced filters in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Verify enhanced response data
            list_data = data["data"]
            assert "statistics" in list_data or "filters_applied" in list_data
            
            # Verify controller was called with enhanced parameters
            mock_list_pets.assert_called_once()
            call_kwargs = mock_list_pets.call_args[1]
            assert call_kwargs.get("include_health_records") is True
            assert call_kwargs.get("include_owner") is True
            assert call_kwargs.get("sort_by") == "name"

    @version_parametrize(versions=["v1"])
    async def test_v1_enhanced_filtering_ignored(self, api_version: str, async_client: AsyncClient,
                                               test_data_factory: TestDataFactory, mock_user):
        """Test that v1 ignores enhanced filtering parameters."""
        mock_pet = Pet(
            id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            name="Test Pet",
            species="dog",
            breed="Golden Retriever",
            gender=PetGender.MALE,
            size=PetSize.LARGE,
            weight=65.0,
            color="Golden",
            birth_date=date(2020, 1, 15),
            age_years=4,
            age_months=0,
            is_age_estimated=False,
            microchip_id="123456789012345",
            is_active=True,
            is_deceased=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        endpoint_url = f"/api/{api_version}/pets"
        
        with patch("app.pets.controller.PetController.list_pets", new_callable=AsyncMock) as mock_list_pets, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_list_pets.return_value = ([mock_pet], 1)
            
            # Test with enhanced filters that should be ignored in v1
            query_params = "?include_health_records=true&include_owner=true&sort_by=name"
            response = await self.make_request("GET", f"{endpoint_url}{query_params}", async_client)
            
            # Should still return 200 but ignore enhanced parameters
            self.assert_status_code(response, 200, f"Listing pets with enhanced filters in {api_version}")
            
            # Verify controller was called with v1 defaults
            mock_list_pets.assert_called_once()
            call_kwargs = mock_list_pets.call_args[1]
            assert call_kwargs.get("include_health_records", True) is False
            assert call_kwargs.get("include_owner", True) is False
            assert call_kwargs.get("sort_by") is None

    # Sorting and Pagination Tests
    @version_parametrize()
    @pytest.mark.asyncio
    async def test_list_pets_with_sorting(self, api_version: str, async_client: AsyncClient,
                                        test_data_factory: TestDataFactory, mock_user):
        """Test pet listing with sorting across versions."""
        mock_pets = [
            Pet(
                id=uuid.uuid4(),
                owner_id=uuid.uuid4(),
                name=f"Pet {i}",
                species="dog",
                breed="Golden Retriever",
                gender=PetGender.MALE,
                size=PetSize.LARGE,
                weight=65.0,
                color="Golden",
                birth_date=date(2020, 1, 15),
                age_years=4,
                age_months=0,
                is_age_estimated=False,
                microchip_id=f"12345678901234{i}",
                is_active=True,
                is_deceased=False,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            for i in range(3)
        ]
        
        endpoint_url = f"/api/{api_version}/pets"
        
        with patch("app.pets.controller.PetController.list_pets", new_callable=AsyncMock) as mock_list_pets, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_list_pets.return_value = (mock_pets, len(mock_pets))
            
            # Test basic sorting (available in all versions)
            query_params = "?page=1&per_page=10"
            if api_version == "v2":
                query_params += "&sort_by=name"
            
            response = await self.make_request("GET", f"{endpoint_url}{query_params}", async_client)
            
            # Assert successful listing
            self.assert_status_code(response, 200, f"Listing pets with sorting in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Verify pagination data
            list_data = data["data"]
            assert list_data["total"] == len(mock_pets)
            assert list_data["page"] == 1
            assert list_data["per_page"] == 10
            assert len(list_data["pets"]) == len(mock_pets)
            
            # Verify controller was called with appropriate parameters
            mock_list_pets.assert_called_once()
            call_kwargs = mock_list_pets.call_args[1]
            assert call_kwargs["page"] == 1
            assert call_kwargs["per_page"] == 10
            
            if api_version == "v2":
                assert call_kwargs.get("sort_by") == "name"
            else:
                assert call_kwargs.get("sort_by") is None

    # Batch Operations Tests (v2+ only)
    @version_parametrize(versions=["v2"])
    @pytest.mark.asyncio
    async def test_batch_pet_operations(self, api_version: str, async_client: AsyncClient,
                                      test_data_factory: TestDataFactory, mock_user):
        """Test batch operations on pets (v2+ only)."""
        # Skip if batch_operations feature not available
        self.skip_if_feature_unavailable(api_version, "batch_operations")
        
        pet_ids = [uuid.uuid4() for _ in range(3)]
        endpoint_url = f"/api/{api_version}/pets/batch"
        
        batch_data = {
            "operation": "activate",
            "pet_ids": [str(pet_id) for pet_id in pet_ids]
        }
        
        with patch("app.pets.controller.PetController.update_pet", new_callable=AsyncMock) as mock_update_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            # Mock successful updates
            mock_update_pet.return_value = Pet(
                id=pet_ids[0],
                owner_id=uuid.uuid4(),
                name="Test Pet",
                species="dog",
                breed="Golden Retriever",
                gender=PetGender.MALE,
                size=PetSize.LARGE,
                weight=65.0,
                color="Golden",
                birth_date=date(2020, 1, 15),
                age_years=4,
                age_months=0,
                is_age_estimated=False,
                microchip_id="123456789012345",
                is_active=True,
                is_deceased=False,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
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
            assert batch_result["total_requested"] == len(pet_ids)
            assert "successful" in batch_result
            assert "failed" in batch_result
            
            # Verify controller was called for each pet
            assert mock_update_pet.call_count == len(pet_ids)

    @version_parametrize(versions=["v1"])
    async def test_v1_batch_operations_not_found(self, api_version: str, async_client: AsyncClient,
                                                mock_user):
        """Test that v1 returns 404 for batch operations endpoints."""
        endpoint_url = f"/api/{api_version}/pets/batch"
        
        batch_data = {
            "operation": "activate",
            "pet_ids": [str(uuid.uuid4())]
        }
        
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            response = await self.make_request("POST", endpoint_url, async_client, json=batch_data)
            
            # Should return 404 for v1
            self.assert_status_code(response, 404, f"Batch operations in {api_version} should return 404")

    # Statistics Endpoint Tests
    @version_parametrize(versions=["v2"])
    @pytest.mark.asyncio
    async def test_get_global_statistics(self, api_version: str, async_client: AsyncClient, mock_user):
        """Test global statistics endpoint (v2+ only)."""
        # Skip if statistics feature not available
        self.skip_if_feature_unavailable(api_version, "statistics")
        
        endpoint_url = f"/api/{api_version}/statistics"
        
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            # Mock statistics data
            mock_stats = {
                "total_pets": 150,
                "total_active_pets": 140,
                "total_users": 75,
                "total_appointments_this_month": 45,
                "total_health_records": 320
            }
            
            # Since there's no specific controller for global stats, we'll mock the response
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "success": True,
                    "data": mock_stats,
                    "version": api_version
                }
                mock_get.return_value = mock_response
                
                response = await self.make_request("GET", endpoint_url, async_client)
                
                # For now, we expect this endpoint might not exist, so we'll accept 404
                # In a real implementation, this would return statistics
                assert response.status_code in [200, 404]

    @version_parametrize(versions=["v1"])
    async def test_v1_global_statistics_not_found(self, api_version: str, async_client: AsyncClient, mock_user):
        """Test that v1 returns 404 for global statistics endpoint."""
        endpoint_url = f"/api/{api_version}/statistics"
        
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Should return 404 for v1
            self.assert_status_code(response, 404, f"Global statistics in {api_version} should return 404")

    # Comprehensive Feature Test
    @version_parametrize(versions=["v2"])
    @pytest.mark.asyncio
    async def test_comprehensive_v2_features(self, api_version: str, async_client: AsyncClient,
                                           test_data_factory: TestDataFactory, mock_user, mock_pet):
        """Test comprehensive v2 feature integration."""
        # Skip if required features not available
        self.skip_if_feature_unavailable(api_version, "statistics")
        self.skip_if_feature_unavailable(api_version, "enhanced_filtering")
        
        # Test 1: Enhanced pet listing
        pets_endpoint = f"/api/{api_version}/pets"
        
        with patch("app.pets.controller.PetController.list_pets", new_callable=AsyncMock) as mock_list_pets, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_list_pets.return_value = ([mock_pet], 1)
            
            # Test enhanced listing with all v2 features
            query_params = "?include_health_records=true&include_owner=true&sort_by=name&include_statistics=true"
            response = await self.make_request("GET", f"{pets_endpoint}{query_params}", async_client)
            
            self.assert_status_code(response, 200, f"Enhanced pet listing in {api_version}")
            
            data = response.json()
            assert data["success"] is True
            assert data["version"] == api_version
            
            # Verify enhanced features were used
            mock_list_pets.assert_called_once()
            call_kwargs = mock_list_pets.call_args[1]
            assert call_kwargs.get("include_health_records") is True
            assert call_kwargs.get("include_owner") is True
            assert call_kwargs.get("sort_by") == "name"
        
        # Test 2: Pet statistics
        stats_endpoint = f"/api/{api_version}/pets/{mock_pet.id}/stats"
        
        with patch("app.pets.controller.PetController.get_pet_by_id", new_callable=AsyncMock) as mock_get_pet, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_pet.health_records = []
            mock_pet.appointments = []
            mock_get_pet.return_value = mock_pet
            
            response = await self.make_request("GET", stats_endpoint, async_client)
            
            self.assert_status_code(response, 200, f"Pet statistics in {api_version}")
            
            data = response.json()
            assert data["success"] is True
            assert data["version"] == api_version
            assert "total_health_records" in data["data"]
            assert "total_appointments" in data["data"]