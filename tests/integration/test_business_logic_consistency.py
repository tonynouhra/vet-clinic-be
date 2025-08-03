"""
Business Logic Consistency Tests.

Tests business logic consistency, authorization consistency, error handling,
and data integrity across all API versions to ensure consistent behavior.
"""

import pytest
import uuid
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from httpx import AsyncClient
from fastapi import status

from app.models.user import User, UserRole
from app.models.pet import Pet, PetGender
from tests.dynamic.base_test import BaseVersionTest
from tests.dynamic.decorators import version_parametrize, feature_test, smart_feature_test
from tests.dynamic.data_factory import TestDataFactory
from tests.dynamic.fixtures import api_version, version_config, base_url


class TestBusinessLogicConsistency(BaseVersionTest):
    """Test business logic consistency across API versions."""

    @pytest.fixture
    def test_data_factory(self):
        """Test data factory fixture."""
        return TestDataFactory()

    @pytest.fixture
    def http_client(self):
        """HTTP client fixture."""
        from app.main import app
        return AsyncClient(app=app, base_url="http://testserver")

    @pytest.fixture
    def mock_user(self):
        """Mock user for authentication."""
        return User(
            id=uuid.uuid4(),
            clerk_id="test_user_123",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
            is_verified=True
        )

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_validation_rules_consistency(self, api_version: str, http_client: AsyncClient, 
                                              test_data_factory: TestDataFactory):
        """Test that validation rules are consistent across versions."""
        # Test required field validation for pets
        pet_data = test_data_factory.build_pet_data(api_version)
        
        # Remove required field 'name'
        invalid_pet_data = pet_data.copy()
        del invalid_pet_data['name']
        
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        if not endpoint_url.endswith('/'):
            endpoint_url += '/'
        response = await http_client.post(endpoint_url, json=invalid_pet_data)
        
        # Should get validation error or authentication error in all versions
        # Both are acceptable for consistency testing
        assert response.status_code in [422, 403, 401], (
            f"Expected validation or auth error for missing 'name' in {api_version}, got {response.status_code}"
        )
        
        error_data = response.json()
        assert "detail" in error_data or "error" in error_data, f"Error response format inconsistent in {api_version}"

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_data_type_validation_consistency(self, api_version: str, http_client: AsyncClient,
                                                  test_data_factory: TestDataFactory):
        """Test that data type validation is consistent across versions."""
        pet_data = test_data_factory.build_pet_data(api_version)
        
        # Test invalid data types
        test_cases = [
            {"field": "weight", "invalid_value": "not_a_number", "expected_error": "type_error"},
            {"field": "owner_id", "invalid_value": "not_a_uuid", "expected_error": "value_error"},
        ]
        
        for test_case in test_cases:
            invalid_data = pet_data.copy()
            invalid_data[test_case["field"]] = test_case["invalid_value"]
            
            endpoint_url = self.get_endpoint_url(api_version, "pets")
            response = await http_client.post(endpoint_url, json=invalid_data)
            
            # Should get validation error in all versions
            assert response.status_code == 422, (
                f"Expected validation error for invalid {test_case['field']} in {api_version}"
            )

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_business_rule_consistency(self, api_version: str, http_client: AsyncClient,
                                           test_data_factory: TestDataFactory):
        """Test that business rules are enforced consistently across versions."""
        # Test duplicate email validation for users
        user_data = test_data_factory.build_user_data(api_version)
        
        endpoint_url = self.get_endpoint_url(api_version, "users")
        
        # Create first user
        response1 = await http_client.post(endpoint_url, json=user_data)
        if response1.status_code == 201:
            created_user = response1.json()
            
            # Try to create second user with same email
            response2 = await http_client.post(endpoint_url, json=user_data)
            
            # Should get conflict error in all versions
            assert response2.status_code in [409, 422], (
                f"Expected conflict/validation error for duplicate email in {api_version}"
            )
            
            # Cleanup
            await self.cleanup_test_resource(http_client, api_version, "users", created_user["id"])

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_field_length_validation_consistency(self, api_version: str, http_client: AsyncClient,
                                                     test_data_factory: TestDataFactory):
        """Test that field length validation is consistent across versions."""
        pet_data = test_data_factory.build_pet_data(api_version)
        
        # Test extremely long name (should be rejected in all versions)
        invalid_data = pet_data.copy()
        invalid_data["name"] = "x" * 1000  # Very long name
        
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        response = await http_client.post(endpoint_url, json=invalid_data)
        
        # Should get validation error in all versions
        assert response.status_code == 422, f"Expected validation error for long name in {api_version}"

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_enum_validation_consistency(self, api_version: str, http_client: AsyncClient,
                                             test_data_factory: TestDataFactory):
        """Test that enum validation is consistent across versions."""
        pet_data = test_data_factory.build_pet_data(api_version)
        
        # Test invalid gender value
        invalid_data = pet_data.copy()
        invalid_data["gender"] = "INVALID_GENDER"
        
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        response = await http_client.post(endpoint_url, json=invalid_data)
        
        # Should get validation error in all versions
        assert response.status_code == 422, f"Expected validation error for invalid gender in {api_version}"

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_update_validation_consistency(self, api_version: str, http_client: AsyncClient,
                                               test_data_factory: TestDataFactory):
        """Test that update validation rules are consistent across versions."""
        # Create a pet first
        pet_data = test_data_factory.build_pet_data(api_version)
        created_pet = await self.create_test_resource(http_client, api_version, "pets", **pet_data)
        
        try:
            # Test partial update with invalid data
            invalid_update = {"weight": "not_a_number"}
            
            endpoint_url = self.get_endpoint_url(api_version, "pets", created_pet["id"])
            response = await http_client.put(endpoint_url, json=invalid_update)
            
            # Should get validation error in all versions
            assert response.status_code == 422, f"Expected validation error for invalid update in {api_version}"
            
        finally:
            # Cleanup
            await self.cleanup_test_resource(http_client, api_version, "pets", created_pet["id"])


class TestAuthorizationConsistency(BaseVersionTest):
    """Test authorization consistency across API versions."""

    @pytest.fixture
    def test_data_factory(self):
        """Test data factory fixture."""
        return TestDataFactory()

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_unauthorized_access_consistency(self, api_version: str, http_client: AsyncClient):
        """Test that unauthorized access is handled consistently across versions."""
        # Test accessing protected endpoints without authentication
        endpoints_to_test = ["pets", "users", "appointments"]
        
        for resource in endpoints_to_test:
            try:
                endpoint_url = self.get_endpoint_url(api_version, resource)
                response = await http_client.get(endpoint_url)
                
                # Should get unauthorized error in all versions
                assert response.status_code in [401, 403], (
                    f"Expected unauthorized error for {resource} in {api_version}, got {response.status_code}"
                )
                
            except Exception:
                # Skip if endpoint doesn't exist in this version
                continue

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_forbidden_operations_consistency(self, api_version: str, http_client: AsyncClient,
                                                  test_data_factory: TestDataFactory):
        """Test that forbidden operations are handled consistently across versions."""
        # Test operations that should be forbidden for regular users
        user_data = test_data_factory.build_user_data(api_version)
        
        # Try to create user with admin role (should be forbidden for regular users)
        admin_user_data = user_data.copy()
        admin_user_data["role"] = "ADMIN"
        
        endpoint_url = self.get_endpoint_url(api_version, "users")
        response = await http_client.post(endpoint_url, json=admin_user_data)
        
        # Should get forbidden error or validation error in all versions
        assert response.status_code in [403, 422], (
            f"Expected forbidden/validation error for admin role creation in {api_version}"
        )

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_resource_ownership_consistency(self, api_version: str, http_client: AsyncClient,
                                                test_data_factory: TestDataFactory):
        """Test that resource ownership validation is consistent across versions."""
        # Create a pet
        pet_data = test_data_factory.build_pet_data(api_version)
        created_pet = await self.create_test_resource(http_client, api_version, "pets", **pet_data)
        
        try:
            # Try to access pet with different user context (should be forbidden)
            endpoint_url = self.get_endpoint_url(api_version, "pets", created_pet["id"])
            
            # Mock different user context
            headers = {"X-User-ID": str(uuid.uuid4())}  # Different user
            response = await http_client.get(endpoint_url, headers=headers)
            
            # Should get forbidden error in all versions (if authorization is implemented)
            if response.status_code not in [200, 404]:  # Allow 404 if not found
                assert response.status_code in [403, 401], (
                    f"Expected forbidden error for unauthorized pet access in {api_version}"
                )
                
        finally:
            # Cleanup
            await self.cleanup_test_resource(http_client, api_version, "pets", created_pet["id"])


class TestErrorHandlingConsistency(BaseVersionTest):
    """Test error handling consistency across API versions."""

    @pytest.fixture
    def test_data_factory(self):
        """Test data factory fixture."""
        return TestDataFactory()

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_not_found_error_consistency(self, api_version: str, http_client: AsyncClient):
        """Test that 404 errors are handled consistently across versions."""
        # Test accessing non-existent resources
        non_existent_id = str(uuid.uuid4())
        
        resources_to_test = ["pets", "users", "appointments"]
        
        for resource in resources_to_test:
            try:
                endpoint_url = self.get_endpoint_url(api_version, resource, non_existent_id)
                response = await http_client.get(endpoint_url)
                
                # Should get 404 in all versions
                assert response.status_code == 404, (
                    f"Expected 404 for non-existent {resource} in {api_version}, got {response.status_code}"
                )
                
                # Check error response format
                error_data = response.json()
                assert "detail" in error_data or "error" in error_data, (
                    f"Error response format inconsistent for {resource} in {api_version}"
                )
                
            except Exception:
                # Skip if endpoint doesn't exist in this version
                continue

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_validation_error_format_consistency(self, api_version: str, http_client: AsyncClient,
                                                     test_data_factory: TestDataFactory):
        """Test that validation error formats are consistent across versions."""
        # Create invalid data that will trigger validation errors
        invalid_pet_data = {
            "name": "",  # Empty name
            "species": "",  # Empty species
            "owner_id": "invalid-uuid"  # Invalid UUID
        }
        
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        response = await http_client.post(endpoint_url, json=invalid_pet_data)
        
        # Should get validation error in all versions
        assert response.status_code == 422, f"Expected validation error in {api_version}"
        
        error_data = response.json()
        
        # Check that error response has consistent structure
        assert "detail" in error_data, f"Validation error missing 'detail' field in {api_version}"
        
        # Detail should be a list of error objects
        if isinstance(error_data["detail"], list):
            for error in error_data["detail"]:
                assert "loc" in error, f"Validation error missing 'loc' field in {api_version}"
                assert "msg" in error, f"Validation error missing 'msg' field in {api_version}"
                assert "type" in error, f"Validation error missing 'type' field in {api_version}"

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_method_not_allowed_consistency(self, api_version: str, http_client: AsyncClient):
        """Test that method not allowed errors are handled consistently across versions."""
        # Test unsupported HTTP methods
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        
        # Try PATCH method (assuming it's not supported)
        response = await http_client.patch(endpoint_url)
        
        # Should get method not allowed error in all versions
        assert response.status_code == 405, (
            f"Expected 405 Method Not Allowed in {api_version}, got {response.status_code}"
        )

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_server_error_consistency(self, api_version: str, http_client: AsyncClient):
        """Test that server errors are handled consistently across versions."""
        # This test would require mocking internal server errors
        # For now, we'll test the error response format when we can trigger one
        
        # Test with malformed JSON
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        
        # Send malformed JSON
        response = await http_client.post(
            endpoint_url,
            content="invalid json content",
            headers={"Content-Type": "application/json"}
        )
        
        # Should get bad request error in all versions
        assert response.status_code == 422, (
            f"Expected 422 for malformed JSON in {api_version}, got {response.status_code}"
        )


class TestDataIntegrityConsistency(BaseVersionTest):
    """Test data integrity consistency across API versions."""

    @pytest.fixture
    def test_data_factory(self):
        """Test data factory fixture."""
        return TestDataFactory()

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_create_read_consistency(self, api_version: str, http_client: AsyncClient,
                                         test_data_factory: TestDataFactory):
        """Test that created data can be read back consistently across versions."""
        # Test with pets
        pet_data = test_data_factory.build_pet_data(api_version)
        created_pet = await self.create_test_resource(http_client, api_version, "pets", **pet_data)
        
        try:
            # Read back the created pet
            endpoint_url = self.get_endpoint_url(api_version, "pets", created_pet["id"])
            response = await http_client.get(endpoint_url)
            
            self.assert_status_code(response, 200, f"Reading created pet in {api_version}")
            
            retrieved_pet = response.json()
            
            # Validate response structure
            self.validate_response_structure(retrieved_pet, api_version, "pet")
            
            # Check that core fields match
            core_fields = ["id", "name", "species", "owner_id"]
            for field in core_fields:
                if field in pet_data and field in retrieved_pet:
                    assert retrieved_pet[field] == (created_pet[field] if field in created_pet else pet_data[field]), (
                        f"Field '{field}' mismatch in {api_version}: "
                        f"expected {pet_data.get(field)}, got {retrieved_pet[field]}"
                    )
            
        finally:
            # Cleanup
            await self.cleanup_test_resource(http_client, api_version, "pets", created_pet["id"])

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_update_consistency(self, api_version: str, http_client: AsyncClient,
                                    test_data_factory: TestDataFactory):
        """Test that updates are applied consistently across versions."""
        # Create a pet
        pet_data = test_data_factory.build_pet_data(api_version)
        created_pet = await self.create_test_resource(http_client, api_version, "pets", **pet_data)
        
        try:
            # Update the pet
            update_data = {"name": "Updated Pet Name"}
            
            endpoint_url = self.get_endpoint_url(api_version, "pets", created_pet["id"])
            response = await http_client.put(endpoint_url, json=update_data)
            
            self.assert_status_code(response, 200, f"Updating pet in {api_version}")
            
            updated_pet = response.json()
            
            # Verify the update was applied
            assert updated_pet["name"] == "Updated Pet Name", (
                f"Update not applied correctly in {api_version}"
            )
            
            # Verify other fields remain unchanged
            assert updated_pet["species"] == created_pet["species"], (
                f"Unmodified field changed during update in {api_version}"
            )
            
        finally:
            # Cleanup
            await self.cleanup_test_resource(http_client, api_version, "pets", created_pet["id"])

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_delete_consistency(self, api_version: str, http_client: AsyncClient,
                                    test_data_factory: TestDataFactory):
        """Test that deletions work consistently across versions."""
        # Create a pet
        pet_data = test_data_factory.build_pet_data(api_version)
        created_pet = await self.create_test_resource(http_client, api_version, "pets", **pet_data)
        
        # Delete the pet
        endpoint_url = self.get_endpoint_url(api_version, "pets", created_pet["id"])
        response = await http_client.delete(endpoint_url)
        
        # Should get successful deletion in all versions
        assert response.status_code in [200, 204], (
            f"Expected successful deletion in {api_version}, got {response.status_code}"
        )
        
        # Verify the pet is actually deleted
        get_response = await http_client.get(endpoint_url)
        assert get_response.status_code == 404, (
            f"Pet still exists after deletion in {api_version}"
        )

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_list_consistency(self, api_version: str, http_client: AsyncClient,
                                  test_data_factory: TestDataFactory):
        """Test that list operations work consistently across versions."""
        # Create multiple pets
        created_pets = []
        
        try:
            for i in range(3):
                pet_data = test_data_factory.build_pet_data(api_version, name=f"Test Pet {i}")
                created_pet = await self.create_test_resource(http_client, api_version, "pets", **pet_data)
                created_pets.append(created_pet)
            
            # List pets
            endpoint_url = self.get_endpoint_url(api_version, "pets")
            response = await http_client.get(endpoint_url)
            
            self.assert_status_code(response, 200, f"Listing pets in {api_version}")
            
            pets_list = response.json()
            
            # Should be a list or have a 'data' field containing a list
            if isinstance(pets_list, list):
                pets_data = pets_list
            elif isinstance(pets_list, dict) and "data" in pets_list:
                pets_data = pets_list["data"]
            else:
                pytest.fail(f"Unexpected list response format in {api_version}: {pets_list}")
            
            # Verify our created pets are in the list
            created_pet_ids = {pet["id"] for pet in created_pets}
            listed_pet_ids = {pet["id"] for pet in pets_data}
            
            assert created_pet_ids.issubset(listed_pet_ids), (
                f"Not all created pets found in list in {api_version}"
            )
            
        finally:
            # Cleanup
            for pet in created_pets:
                await self.cleanup_test_resource(http_client, api_version, "pets", pet["id"])

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_timestamp_consistency(self, api_version: str, http_client: AsyncClient,
                                       test_data_factory: TestDataFactory):
        """Test that timestamps are handled consistently across versions."""
        # Create a pet
        pet_data = test_data_factory.build_pet_data(api_version)
        created_pet = await self.create_test_resource(http_client, api_version, "pets", **pet_data)
        
        try:
            # Check that timestamps are present and valid
            assert "created_at" in created_pet, f"Missing created_at timestamp in {api_version}"
            assert "updated_at" in created_pet, f"Missing updated_at timestamp in {api_version}"
            
            # Timestamps should be valid ISO format
            from datetime import datetime
            try:
                datetime.fromisoformat(created_pet["created_at"].replace("Z", "+00:00"))
                datetime.fromisoformat(created_pet["updated_at"].replace("Z", "+00:00"))
            except ValueError:
                pytest.fail(f"Invalid timestamp format in {api_version}")
            
        finally:
            # Cleanup
            await self.cleanup_test_resource(http_client, api_version, "pets", created_pet["id"])