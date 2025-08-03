"""
Dynamic Health Records Feature Tests - Version-Agnostic API Testing.

Tests health records functionality across API versions using the dynamic testing framework.
Health records are only available in v2+, so v1 tests verify 404 responses.
"""

import pytest
import uuid
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from fastapi import status

from app.models.user import User, UserRole
from app.models.pet import Pet, PetGender, PetSize, HealthRecordType
from tests.dynamic.base_test import BaseVersionTest
from tests.dynamic.decorators import version_parametrize, feature_test
from tests.dynamic.data_factory import TestDataFactory


class TestHealthRecordsDynamic(BaseVersionTest):
    """Dynamic health records tests across all API versions."""

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
        """Mock pet for health records testing."""
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

    def create_mock_health_record(self, pet_id: uuid.UUID, test_data_factory: TestDataFactory):
        """Create a mock health record object."""
        from app.models.pet import HealthRecord
        
        health_record_data = test_data_factory.build_health_record_data("v2")
        
        return HealthRecord(
            id=uuid.uuid4(),
            pet_id=pet_id,
            record_type=HealthRecordType.VACCINATION,
            title="Annual Vaccination",
            record_date=datetime.strptime(health_record_data["date"], "%Y-%m-%d").date(),
            description=health_record_data["description"],
            cost=health_record_data.get("cost", 75.0),
            notes=health_record_data.get("notes", "No adverse reactions"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    # Health Record Creation Tests
    @feature_test("health_records")
    @pytest.mark.asyncio
    async def test_create_health_record_success(self, api_version: str, async_client: AsyncClient,
                                              test_data_factory: TestDataFactory, mock_user, mock_pet):
        """Test successful health record creation (v2+ only)."""
        # Generate version-appropriate test data
        health_record_data = test_data_factory.build_health_record_data(api_version)
        mock_health_record = self.create_mock_health_record(mock_pet.id, test_data_factory)
        
        # Get endpoint URL for health records
        endpoint_url = f"/api/{api_version}/pets/{mock_pet.id}/health-records"
        
        with patch("app.pets.controller.PetController.add_health_record", new_callable=AsyncMock) as mock_add_record, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            mock_add_record.return_value = mock_health_record
            
            response = await async_client.post(endpoint_url, json=health_record_data)
            
            # Assert successful creation
            self.assert_status_code(response, 201, f"Creating health record in {api_version}")
            
            data = response.json()
            
            # Verify response structure
            assert data["success"] is True
            assert data["version"] == api_version
            assert "data" in data
            
            # Validate health record response fields
            health_record_response = data["data"]
            self.validate_response_structure(health_record_response, api_version, "health_record", "response")
            
            # Verify required fields are present
            assert health_record_response["record_type"] == health_record_data["record_type"]
            assert health_record_response["date"] == health_record_data["date"]
            assert health_record_response["description"] == health_record_data["description"]
            
            # Verify controller was called correctly
            mock_add_record.assert_called_once()
            call_args = mock_add_record.call_args
            assert call_args[1]["pet_id"] == mock_pet.id
            assert call_args[1]["created_by"] == mock_user.id

    @feature_test("health_records")
    async def test_create_health_record_validation_error(self, api_version: str, async_client: AsyncClient,
                                                       mock_user, mock_pet):
        """Test health record creation with validation errors (v2+ only)."""
        endpoint_url = f"/api/{api_version}/pets/{mock_pet.id}/health-records"
        
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            # Test with missing required fields
            invalid_data = {
                "record_type": "",  # Empty record type should fail validation
                "date": "",  # Empty date should fail validation
                "description": ""  # Empty description should fail validation
            }
            
            response = await self.make_request("POST", endpoint_url, async_client, json=invalid_data)
            
            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Health Record Retrieval Tests
    @feature_test("health_records")
    async def test_get_pet_health_records_success(self, api_version: str, async_client: AsyncClient,
                                                test_data_factory: TestDataFactory, mock_user, mock_pet):
        """Test successful health records retrieval (v2+ only)."""
        mock_health_record = self.create_mock_health_record(mock_pet.id, test_data_factory)
        endpoint_url = f"/api/{api_version}/pets/{mock_pet.id}/health-records"
        
        with patch("app.pets.controller.PetController.get_pet_health_records", new_callable=AsyncMock) as mock_get_records, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_records.return_value = [mock_health_record]
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Assert successful retrieval
            self.assert_status_code(response, 200, f"Getting health records in {api_version}")
            
            data = response.json()
            
            # Verify response is a list
            assert isinstance(data, list)
            assert len(data) == 1
            
            # Validate health record response structure
            health_record_response = data[0]
            self.validate_response_structure(health_record_response, api_version, "health_record", "response")
            
            # Verify health record data
            assert health_record_response["id"] == str(mock_health_record.id)
            assert health_record_response["pet_id"] == str(mock_health_record.pet_id)
            assert health_record_response["record_type"] == mock_health_record.record_type.value
            
            # Verify controller was called correctly
            mock_get_records.assert_called_once()
            call_args = mock_get_records.call_args
            assert call_args[1]["pet_id"] == mock_pet.id

    @feature_test("health_records")
    async def test_get_health_records_with_filters(self, api_version: str, async_client: AsyncClient,
                                                 test_data_factory: TestDataFactory, mock_user, mock_pet):
        """Test health records retrieval with filtering (v2+ only)."""
        mock_health_record = self.create_mock_health_record(mock_pet.id, test_data_factory)
        endpoint_url = f"/api/{api_version}/pets/{mock_pet.id}/health-records"
        
        with patch("app.pets.controller.PetController.get_pet_health_records", new_callable=AsyncMock) as mock_get_records, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_records.return_value = [mock_health_record]
            
            # Test with filters
            query_params = "?record_type=VACCINATION&start_date=2024-01-01&end_date=2024-12-31"
            response = await self.make_request("GET", f"{endpoint_url}{query_params}", async_client)
            
            # Assert successful retrieval with filters
            self.assert_status_code(response, 200, f"Getting filtered health records in {api_version}")
            
            # Verify controller was called with correct filters
            mock_get_records.assert_called_once()
            call_args = mock_get_records.call_args
            assert call_args[1]["pet_id"] == mock_pet.id
            assert call_args[1]["record_type"] == HealthRecordType.VACCINATION
            assert call_args[1]["start_date"] == date(2024, 1, 1)
            assert call_args[1]["end_date"] == date(2024, 12, 31)

    @feature_test("health_records")
    async def test_get_health_records_empty_result(self, api_version: str, async_client: AsyncClient,
                                                 mock_user, mock_pet):
        """Test health records retrieval with no records (v2+ only)."""
        endpoint_url = f"/api/{api_version}/pets/{mock_pet.id}/health-records"
        
        with patch("app.pets.controller.PetController.get_pet_health_records", new_callable=AsyncMock) as mock_get_records, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            mock_get_records.return_value = []
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Assert successful retrieval with empty result
            self.assert_status_code(response, 200, f"Getting empty health records in {api_version}")
            
            data = response.json()
            
            # Verify response is empty list
            assert isinstance(data, list)
            assert len(data) == 0

    # Health Record Validation Tests
    @feature_test("health_records")
    async def test_health_record_data_validation(self, api_version: str, async_client: AsyncClient,
                                               test_data_factory: TestDataFactory, mock_user, mock_pet):
        """Test health record data validation (v2+ only)."""
        endpoint_url = f"/api/{api_version}/pets/{mock_pet.id}/health-records"
        
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            # Test with invalid record type
            invalid_data = test_data_factory.build_health_record_data(api_version)
            invalid_data["record_type"] = "INVALID_TYPE"
            
            response = await self.make_request("POST", endpoint_url, async_client, json=invalid_data)
            
            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            
            # Test with invalid date format
            invalid_data = test_data_factory.build_health_record_data(api_version)
            invalid_data["date"] = "invalid-date"
            
            response = await self.make_request("POST", endpoint_url, async_client, json=invalid_data)
            
            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            
            # Test with negative cost
            invalid_data = test_data_factory.build_health_record_data(api_version)
            invalid_data["cost"] = -50.0
            
            response = await self.make_request("POST", endpoint_url, async_client, json=invalid_data)
            
            # Should return validation error
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # V1 Compatibility Tests - Health Records Not Supported
    @version_parametrize(versions=["v1"])
    async def test_v1_health_records_not_found(self, api_version: str, async_client: AsyncClient,
                                             mock_user, mock_pet):
        """Test that v1 returns 404 for health record endpoints."""
        # Test health record creation endpoint
        create_endpoint = f"/api/{api_version}/pets/{mock_pet.id}/health-records"
        
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            health_record_data = {
                "record_type": "VACCINATION",
                "date": "2024-01-15",
                "description": "Annual vaccination"
            }
            
            response = await self.make_request("POST", create_endpoint, async_client, json=health_record_data)
            
            # Should return 404 for v1
            self.assert_status_code(response, 404, f"Health record creation in {api_version} should return 404")
        
        # Test health record retrieval endpoint
        get_endpoint = f"/api/{api_version}/pets/{mock_pet.id}/health-records"
        
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            response = await self.make_request("GET", get_endpoint, async_client)
            
            # Should return 404 for v1
            self.assert_status_code(response, 404, f"Health record retrieval in {api_version} should return 404")

    # Authorization Tests
    @feature_test("health_records")
    async def test_health_records_unauthorized_access(self, async_client: AsyncClient, mock_pet, request):
        """Test unauthorized access to health record endpoints (v2+ only)."""
        # Get api_version from the test node
        api_version = request.node.callspec.params.get('api_version', 'v2')
        
        endpoint_url = f"/api/{api_version}/pets/{mock_pet.id}/health-records"
        
        with patch("app.app_helpers.auth_helpers.get_current_user", side_effect=Exception("Unauthorized")):
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Should return unauthorized status
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]

    @feature_test("health_records")
    async def test_health_records_insufficient_permissions(self, async_client: AsyncClient,
                                                         test_data_factory: TestDataFactory, mock_pet, request):
        """Test insufficient permissions for health record creation (v2+ only)."""
        # Get api_version from the test node
        api_version = request.node.callspec.params.get('api_version', 'v2')
        
        # Create a user with insufficient permissions (PET_OWNER role)
        pet_owner_user = User(
            id=uuid.uuid4(),
            clerk_id="owner_clerk_123",
            email="owner@example.com",
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_verified=True
        )
        
        endpoint_url = f"/api/{api_version}/pets/{mock_pet.id}/health-records"
        health_record_data = test_data_factory.build_health_record_data(api_version)
        
        with patch("app.app_helpers.auth_helpers.get_current_user", return_value=pet_owner_user), \
             patch("app.app_helpers.auth_helpers.require_role", side_effect=Exception("Insufficient permissions")):
            
            response = await self.make_request("POST", endpoint_url, async_client, json=health_record_data)
            
            # Should return forbidden or internal server error
            assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_500_INTERNAL_SERVER_ERROR]

    # Pet Not Found Tests
    @feature_test("health_records")
    async def test_health_records_pet_not_found(self, api_version: str, async_client: AsyncClient,
                                              test_data_factory: TestDataFactory, mock_user):
        """Test health record operations with non-existent pet (v2+ only)."""
        non_existent_pet_id = uuid.uuid4()
        endpoint_url = f"/api/{api_version}/pets/{non_existent_pet_id}/health-records"
        
        with patch("app.pets.controller.PetController.get_pet_health_records", new_callable=AsyncMock) as mock_get_records, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user):
            
            from app.core.exceptions import NotFoundError
            mock_get_records.side_effect = NotFoundError("Pet not found")
            
            response = await self.make_request("GET", endpoint_url, async_client)
            
            # Should return 404
            self.assert_status_code(response, 404, f"Getting health records for non-existent pet in {api_version}")

    # Comprehensive Health Records Workflow Test
    @feature_test("health_records")
    async def test_complete_health_records_workflow(self, api_version: str, async_client: AsyncClient,
                                                  test_data_factory: TestDataFactory, mock_user, mock_pet):
        """Test complete health records workflow (v2+ only)."""
        # 1. Create health record
        health_record_data = test_data_factory.build_health_record_data(api_version)
        mock_health_record = self.create_mock_health_record(mock_pet.id, test_data_factory)
        
        create_url = f"/api/{api_version}/pets/{mock_pet.id}/health-records"
        get_url = f"/api/{api_version}/pets/{mock_pet.id}/health-records"
        
        with patch("app.pets.controller.PetController.add_health_record", new_callable=AsyncMock) as mock_add, \
             patch("app.pets.controller.PetController.get_pet_health_records", new_callable=AsyncMock) as mock_get, \
             patch("app.app_helpers.auth_helpers.get_current_user", return_value=mock_user), \
             patch("app.app_helpers.auth_helpers.require_role", return_value=mock_user):
            
            mock_add.return_value = mock_health_record
            mock_get.return_value = [mock_health_record]
            
            # Create health record
            create_response = await self.make_request("POST", create_url, async_client, json=health_record_data)
            self.assert_status_code(create_response, 201, f"Health record creation in {api_version}")
            created_record = create_response.json()["data"]
            
            # Retrieve health records
            get_response = await self.make_request("GET", get_url, async_client)
            self.assert_status_code(get_response, 200, f"Health record retrieval in {api_version}")
            retrieved_records = get_response.json()
            
            # Verify workflow
            assert len(retrieved_records) == 1
            assert retrieved_records[0]["id"] == created_record["id"]
            assert retrieved_records[0]["record_type"] == health_record_data["record_type"]
            
            # Verify all operations were called
            mock_add.assert_called_once()
            mock_get.assert_called_once()

    # Data Factory Integration Tests
    @feature_test("health_records")
    async def test_health_record_data_factory_integration(self, test_data_factory: TestDataFactory, request):
        """Test health record data factory integration (v2+ only)."""
        # Get api_version from the test node
        api_version = request.node.callspec.params.get('api_version', 'v2')
        
        # Test basic health record data generation
        health_record_data = test_data_factory.build_health_record_data(api_version)
        
        # Verify required fields are present
        required_fields = self.get_required_fields(api_version, "health_record", "create")
        for field in required_fields:
            assert field in health_record_data, f"Required field '{field}' missing from generated data"
        
        # Verify data types and constraints
        assert isinstance(health_record_data["record_type"], str)
        assert health_record_data["record_type"] in ["VACCINATION", "CHECKUP", "SURGERY", "MEDICATION", "INJURY", "ILLNESS"]
        assert isinstance(health_record_data["date"], str)
        assert isinstance(health_record_data["description"], str)
        
        if "cost" in health_record_data:
            assert isinstance(health_record_data["cost"], (int, float))
            assert health_record_data["cost"] >= 0
        
        # Test data validation
        validation_errors = test_data_factory.validate_data_against_schema(
            health_record_data, api_version, "health_record", "create"
        )
        assert len(validation_errors) == 0, f"Data validation errors: {validation_errors}"

    # Expected Response Fields Tests
    @feature_test("health_records")
    async def test_health_record_response_fields(self, test_data_factory: TestDataFactory, request):
        """Test health record response field expectations (v2+ only)."""
        # Get api_version from the test node
        api_version = request.node.callspec.params.get('api_version', 'v2')
        
        # Get expected response fields
        expected_fields = test_data_factory.get_expected_response_fields(api_version, "health_record")
        
        # Verify expected fields are defined
        assert len(expected_fields) > 0, f"No expected response fields defined for health_record in {api_version}"
        
        # Verify essential fields are included
        essential_fields = ["id", "pet_id", "record_type", "date", "description", "created_at", "updated_at"]
        for field in essential_fields:
            assert field in expected_fields, f"Essential field '{field}' missing from expected response fields"
        
        # Verify version-specific fields
        if api_version == "v2":
            v2_specific_fields = ["veterinarian", "cost", "notes"]
            for field in v2_specific_fields:
                assert field in expected_fields, f"V2-specific field '{field}' missing from expected response fields"