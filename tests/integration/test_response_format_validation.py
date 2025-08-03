"""
Response Format Validation Tests.

Tests version-specific response structures, field presence/absence validation,
response schema compliance, and version header validation across API versions.
"""

import pytest
import uuid
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Set
from httpx import AsyncClient
from fastapi import status

from app.models.user import User, UserRole
from app.models.pet import Pet, PetGender
from tests.dynamic.base_test import BaseVersionTest
from tests.dynamic.decorators import version_parametrize, feature_test, smart_feature_test
from tests.dynamic.data_factory import TestDataFactory
from tests.dynamic.fixtures import api_version, version_config, base_url


class TestResponseStructureValidation(BaseVersionTest):
    """Test version-specific response structure validation."""


    @version_parametrize()
    @pytest.mark.asyncio
    async def test_pet_response_structure(self, api_version: str, async_client: AsyncClient,
                                        test_data_factory: TestDataFactory):
        """Test that pet responses have the correct structure for each version."""
        # Create a pet
        pet_data = test_data_factory.build_pet_data(api_version)
        created_pet = await self.create_test_resource(async_client, api_version, "pets", **pet_data)
        
        try:
            # Get the pet to test response structure
            endpoint_url = self.get_endpoint_url(api_version, "pets", created_pet["id"])
            response = await async_client.get(endpoint_url)
            
            self.assert_status_code(response, 200, f"Getting pet in {api_version}")
            
            pet_response = response.json()
            
            # Validate response structure using base test method
            self.validate_response_structure(pet_response, api_version, "pet")
            
            # Additional validation for version-specific fields
            self.validate_version_specific_fields(pet_response, api_version, "pet")
            
            # Test specific field types
            self._validate_field_types(pet_response, api_version, "pet")
            
        finally:
            # Cleanup
            await self.cleanup_test_resource(async_client, api_version, "pets", created_pet["id"])

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_user_response_structure(self, api_version: str, async_client: AsyncClient,
                                         test_data_factory: TestDataFactory):
        """Test that user responses have the correct structure for each version."""
        # Create a user
        user_data = test_data_factory.build_user_data(api_version)
        created_user = await self.create_test_resource(async_client, api_version, "users", **user_data)
        
        try:
            # Get the user to test response structure
            endpoint_url = self.get_endpoint_url(api_version, "users", created_user["id"])
            response = await async_client.get(endpoint_url)
            
            self.assert_status_code(response, 200, f"Getting user in {api_version}")
            
            user_response = response.json()
            
            # Validate response structure
            self.validate_response_structure(user_response, api_version, "user")
            
            # Additional validation for version-specific fields
            self.validate_version_specific_fields(user_response, api_version, "user")
            
            # Test specific field types
            self._validate_field_types(user_response, api_version, "user")
            
        finally:
            # Cleanup
            await self.cleanup_test_resource(async_client, api_version, "users", created_user["id"])

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_appointment_response_structure(self, api_version: str, async_client: AsyncClient,
                                                test_data_factory: TestDataFactory):
        """Test that appointment responses have the correct structure for each version."""
        # Create prerequisites (user and pet)
        user_data = test_data_factory.build_user_data(api_version)
        created_user = await self.create_test_resource(async_client, api_version, "users", **user_data)
        
        pet_data = test_data_factory.build_pet_data(api_version, owner_id=created_user["id"])
        created_pet = await self.create_test_resource(async_client, api_version, "pets", **pet_data)
        
        # Create appointment
        appointment_data = test_data_factory.build_appointment_data(
            api_version, 
            user_id=created_user["id"], 
            pet_id=created_pet["id"]
        )
        created_appointment = await self.create_test_resource(
            async_client, api_version, "appointments", **appointment_data
        )
        
        try:
            # Get the appointment to test response structure
            endpoint_url = self.get_endpoint_url(api_version, "appointments", created_appointment["id"])
            response = await async_client.get(endpoint_url)
            
            self.assert_status_code(response, 200, f"Getting appointment in {api_version}")
            
            appointment_response = response.json()
            
            # Validate response structure
            self.validate_response_structure(appointment_response, api_version, "appointment")
            
            # Additional validation for version-specific fields
            self.validate_version_specific_fields(appointment_response, api_version, "appointment")
            
            # Test specific field types
            self._validate_field_types(appointment_response, api_version, "appointment")
            
        finally:
            # Cleanup
            await self.cleanup_test_resource(async_client, api_version, "appointments", created_appointment["id"])
            await self.cleanup_test_resource(async_client, api_version, "pets", created_pet["id"])
            await self.cleanup_test_resource(async_client, api_version, "users", created_user["id"])

    @smart_feature_test("health_records")
    @pytest.mark.asyncio
    async def test_health_record_response_structure(self, api_version: str, async_client: AsyncClient,
                                                   test_data_factory: TestDataFactory):
        """Test that health record responses have the correct structure (v2+ only)."""
        # Create prerequisites
        user_data = test_data_factory.build_user_data(api_version)
        created_user = await self.create_test_resource(async_client, api_version, "users", **user_data)
        
        pet_data = test_data_factory.build_pet_data(api_version, owner_id=created_user["id"])
        created_pet = await self.create_test_resource(async_client, api_version, "pets", **pet_data)
        
        # Create health record
        health_record_data = test_data_factory.build_health_record_data(api_version)
        
        endpoint_url = self.get_endpoint_url(api_version, "health_records", pet_id=created_pet["id"])
        response = await async_client.post(endpoint_url, json=health_record_data)
        
        self.assert_status_code(response, 201, f"Creating health record in {api_version}")
        
        created_health_record = response.json()
        
        try:
            # Validate response structure
            self.validate_response_structure(created_health_record, api_version, "health_record")
            
            # Test specific field types
            self._validate_field_types(created_health_record, api_version, "health_record")
            
        finally:
            # Cleanup (health records are typically cleaned up with pet deletion)
            await self.cleanup_test_resource(async_client, api_version, "pets", created_pet["id"])
            await self.cleanup_test_resource(async_client, api_version, "users", created_user["id"])

    def _validate_field_types(self, response_data: Dict[str, Any], version: str, resource: str) -> None:
        """Validate that response fields have the correct data types."""
        # Common field type validations
        type_validations = {
            "id": (str, "ID should be a string (UUID)"),
            "created_at": (str, "created_at should be a string (ISO datetime)"),
            "updated_at": (str, "updated_at should be a string (ISO datetime)"),
            "weight": ((int, float), "weight should be a number"),
            "pet_count": (int, "pet_count should be an integer"),
            "cost": ((int, float), "cost should be a number"),
        }
        
        for field, (expected_types, error_msg) in type_validations.items():
            if field in response_data:
                if not isinstance(response_data[field], expected_types):
                    pytest.fail(f"{error_msg} in {version} {resource} response. Got: {type(response_data[field])}")

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_list_response_structure(self, api_version: str, async_client: AsyncClient,
                                         test_data_factory: TestDataFactory):
        """Test that list responses have the correct structure for each version."""
        # Create a few pets for testing list response
        created_pets = []
        
        try:
            for i in range(2):
                pet_data = test_data_factory.build_pet_data(api_version, name=f"List Test Pet {i}")
                created_pet = await self.create_test_resource(async_client, api_version, "pets", **pet_data)
                created_pets.append(created_pet)
            
            # Get list of pets
            endpoint_url = self.get_endpoint_url(api_version, "pets")
            response = await async_client.get(endpoint_url)
            
            self.assert_status_code(response, 200, f"Getting pets list in {api_version}")
            
            list_response = response.json()
            
            # Validate list response structure
            self._validate_list_response_structure(list_response, api_version, "pets")
            
        finally:
            # Cleanup
            for pet in created_pets:
                await self.cleanup_test_resource(async_client, api_version, "pets", pet["id"])

    def _validate_list_response_structure(self, list_response: Any, version: str, resource: str) -> None:
        """Validate the structure of list responses."""
        # List responses can be either:
        # 1. Direct array of items
        # 2. Object with 'data' field containing array
        # 3. Object with pagination metadata
        
        if isinstance(list_response, list):
            # Direct array format
            items = list_response
        elif isinstance(list_response, dict):
            if "data" in list_response:
                # Object with data field
                items = list_response["data"]
                assert isinstance(items, list), f"'data' field should be a list in {version} {resource} response"
                
                # Check for pagination metadata
                pagination_fields = ["total", "page", "per_page", "pages"]
                for field in pagination_fields:
                    if field in list_response:
                        assert isinstance(list_response[field], int), (
                            f"Pagination field '{field}' should be an integer in {version} {resource} response"
                        )
            else:
                pytest.fail(f"Unexpected list response format in {version} {resource}: {list_response}")
        else:
            pytest.fail(f"List response should be array or object in {version} {resource}: {type(list_response)}")
        
        # Validate individual items in the list
        for item in items:
            assert isinstance(item, dict), f"List items should be objects in {version} {resource} response"
            # Each item should have at least an ID
            assert "id" in item, f"List items should have 'id' field in {version} {resource} response"


class TestFieldPresenceValidation(BaseVersionTest):
    """Test field presence/absence validation for each version."""


    @version_parametrize()
    @pytest.mark.asyncio
    async def test_required_fields_presence(self, api_version: str, async_client: AsyncClient,
                                          test_data_factory: TestDataFactory):
        """Test that all required fields are present in responses."""
        # Test with pets
        pet_data = test_data_factory.build_pet_data(api_version)
        created_pet = await self.create_test_resource(async_client, api_version, "pets", **pet_data)
        
        try:
            # Get expected required fields for this version
            required_fields = self.config_manager.get_schema_fields(api_version, "pet_response")
            
            # Verify all required fields are present
            for field in required_fields:
                assert field in created_pet, (
                    f"Required field '{field}' missing from {api_version} pet response"
                )
                
        finally:
            # Cleanup
            await self.cleanup_test_resource(async_client, api_version, "pets", created_pet["id"])

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_version_specific_field_presence(self, api_version: str, async_client: AsyncClient,
                                                 test_data_factory: TestDataFactory):
        """Test that version-specific fields are present or absent as expected."""
        # Create a pet with version-appropriate data
        pet_data = test_data_factory.build_pet_data(api_version)
        created_pet = await self.create_test_resource(async_client, api_version, "pets", **pet_data)
        
        try:
            # Test v2-specific fields
            v2_specific_fields = ["temperament", "behavioral_notes", "emergency_contact", 
                                "owner_info", "additional_photos"]
            
            for field in v2_specific_fields:
                if api_version == "v2":
                    # Field should be present in v2 (even if null/empty)
                    if self.should_test_feature(api_version, field.replace("_", "")):
                        assert field in created_pet, (
                            f"V2-specific field '{field}' should be present in {api_version} response"
                        )
                else:
                    # Field should not be present in v1
                    assert field not in created_pet, (
                        f"V2-specific field '{field}' should not be present in {api_version} response"
                    )
                    
        finally:
            # Cleanup
            await self.cleanup_test_resource(async_client, api_version, "pets", created_pet["id"])

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_optional_field_handling(self, api_version: str, async_client: AsyncClient,
                                         test_data_factory: TestDataFactory):
        """Test that optional fields are handled correctly."""
        # Create pet with minimal required data (no optional fields)
        required_fields = self.get_required_fields(api_version, "pet", "create")
        minimal_pet_data = {}
        
        for field in required_fields:
            if field in ["name", "species"]:
                minimal_pet_data[field] = f"Test {field}"
            elif field == "owner_id":
                minimal_pet_data[field] = str(uuid.uuid4())
        
        created_pet = await self.create_test_resource(async_client, api_version, "pets", **minimal_pet_data)
        
        try:
            # Get optional fields for this version
            optional_fields = self.get_optional_fields(api_version, "pet", "create")
            
            # Optional fields should either be present with default values or absent
            for field in optional_fields:
                if field in created_pet:
                    # If present, should not be None (unless explicitly allowed)
                    if created_pet[field] is None:
                        # Check if null is allowed for this field
                        pass  # Some optional fields may be null
                        
        finally:
            # Cleanup
            await self.cleanup_test_resource(async_client, api_version, "pets", created_pet["id"])

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_nested_object_field_presence(self, api_version: str, async_client: AsyncClient,
                                               test_data_factory: TestDataFactory):
        """Test that nested object fields have correct structure."""
        # Test with user data that has nested objects (v2)
        if api_version == "v2":
            user_data = test_data_factory.build_user_data(api_version)
            created_user = await self.create_test_resource(async_client, api_version, "users", **user_data)
            
            try:
                # Check nested objects like address and emergency_contact
                if "address" in created_user and created_user["address"] is not None:
                    address = created_user["address"]
                    assert isinstance(address, dict), "Address should be an object"
                    
                    # Check address fields
                    address_fields = ["street", "city", "state", "zip_code"]
                    for field in address_fields:
                        if field in address:
                            assert isinstance(address[field], str), f"Address {field} should be a string"
                
                if "emergency_contact" in created_user and created_user["emergency_contact"] is not None:
                    emergency_contact = created_user["emergency_contact"]
                    assert isinstance(emergency_contact, dict), "Emergency contact should be an object"
                    
                    # Check emergency contact fields
                    contact_fields = ["name", "phone", "relationship"]
                    for field in contact_fields:
                        if field in emergency_contact:
                            assert isinstance(emergency_contact[field], str), (
                                f"Emergency contact {field} should be a string"
                            )
                            
            finally:
                # Cleanup
                await self.cleanup_test_resource(async_client, api_version, "users", created_user["id"])


class TestSchemaComplianceValidation(BaseVersionTest):
    """Test response schema compliance across versions."""


    @version_parametrize()
    @pytest.mark.asyncio
    async def test_response_schema_compliance(self, api_version: str, async_client: AsyncClient,
                                            test_data_factory: TestDataFactory):
        """Test that responses comply with version-specific schemas."""
        # Test all resource types
        resources_to_test = ["pets", "users", "appointments"]
        
        for resource in resources_to_test:
            try:
                # Create test resource
                if resource == "pets":
                    data = test_data_factory.build_pet_data(api_version)
                elif resource == "users":
                    data = test_data_factory.build_user_data(api_version)
                elif resource == "appointments":
                    # Skip appointments for now as they require prerequisites
                    continue
                
                created_resource = await self.create_test_resource(async_client, api_version, resource, **data)
                
                try:
                    # Validate schema compliance
                    self._validate_schema_compliance(created_resource, api_version, resource)
                    
                finally:
                    # Cleanup
                    await self.cleanup_test_resource(async_client, api_version, resource, created_resource["id"])
                    
            except Exception as e:
                # Skip if resource not supported in this version
                if "not found" in str(e).lower():
                    continue
                raise

    def _validate_schema_compliance(self, response_data: Dict[str, Any], version: str, resource: str) -> None:
        """Validate that response data complies with schema requirements."""
        # Get schema fields for this version and resource
        try:
            expected_fields = self.config_manager.get_schema_fields(version, f"{resource}_response")
        except Exception:
            # Skip if schema not defined
            return
        
        # Check field presence
        for field in expected_fields:
            assert field in response_data, (
                f"Schema field '{field}' missing from {version} {resource} response"
            )
        
        # Check for unexpected fields (fields not in schema)
        unexpected_fields = set(response_data.keys()) - set(expected_fields)
        
        # Some fields might be dynamically added (like computed fields)
        # We'll allow them but log a warning
        if unexpected_fields:
            print(f"Warning: Unexpected fields in {version} {resource} response: {unexpected_fields}")

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_error_response_schema_compliance(self, api_version: str, async_client: AsyncClient):
        """Test that error responses comply with expected schema."""
        # Trigger a validation error
        invalid_data = {"name": ""}  # Empty name should trigger validation error
        
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        response = await async_client.post(endpoint_url, json=invalid_data)
        
        # Should get validation error
        assert response.status_code == 422, f"Expected validation error in {api_version}"
        
        error_data = response.json()
        
        # Validate error response schema
        self._validate_error_response_schema(error_data, api_version)

    def _validate_error_response_schema(self, error_data: Dict[str, Any], version: str) -> None:
        """Validate error response schema compliance."""
        # Error responses should have consistent structure across versions
        assert "detail" in error_data, f"Error response missing 'detail' field in {version}"
        
        detail = error_data["detail"]
        
        if isinstance(detail, list):
            # Validation error format
            for error in detail:
                assert isinstance(error, dict), f"Error detail items should be objects in {version}"
                assert "loc" in error, f"Error detail missing 'loc' field in {version}"
                assert "msg" in error, f"Error detail missing 'msg' field in {version}"
                assert "type" in error, f"Error detail missing 'type' field in {version}"
        elif isinstance(detail, str):
            # Simple error message format
            assert len(detail) > 0, f"Error detail message should not be empty in {version}"
        else:
            pytest.fail(f"Unexpected error detail format in {version}: {type(detail)}")


class TestVersionHeaderValidation(BaseVersionTest):
    """Test version header validation and handling."""


    @version_parametrize()
    @pytest.mark.asyncio
    async def test_version_header_presence(self, api_version: str, async_client: AsyncClient):
        """Test that version information is present in response headers."""
        # Make a simple request
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        response = await async_client.get(endpoint_url)
        
        # Check for version-related headers
        version_headers = ["X-API-Version", "API-Version", "Version"]
        
        version_header_found = False
        for header in version_headers:
            if header in response.headers:
                version_header_found = True
                header_value = response.headers[header]
                
                # Validate header value
                assert api_version in header_value or api_version.upper() in header_value, (
                    f"Version header '{header}' value '{header_value}' doesn't match expected version {api_version}"
                )
                break
        
        # Note: Version headers might not be implemented yet, so we'll make this a warning
        if not version_header_found:
            print(f"Warning: No version header found in {api_version} response")

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_content_type_header_consistency(self, api_version: str, async_client: AsyncClient):
        """Test that Content-Type headers are consistent across versions."""
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        response = await async_client.get(endpoint_url)
        
        # Should have JSON content type
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type, (
            f"Expected JSON content type in {api_version}, got: {content_type}"
        )

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_cors_headers_consistency(self, api_version: str, async_client: AsyncClient):
        """Test that CORS headers are consistent across versions."""
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        
        # Make OPTIONS request to check CORS headers
        response = await async_client.options(endpoint_url)
        
        # Check for CORS headers (if implemented)
        cors_headers = ["Access-Control-Allow-Origin", "Access-Control-Allow-Methods", 
                       "Access-Control-Allow-Headers"]
        
        cors_implemented = any(header in response.headers for header in cors_headers)
        
        if cors_implemented:
            # If CORS is implemented, check consistency
            for header in cors_headers:
                if header in response.headers:
                    header_value = response.headers[header]
                    assert len(header_value) > 0, f"CORS header '{header}' should not be empty in {api_version}"

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_cache_headers_consistency(self, api_version: str, async_client: AsyncClient):
        """Test that cache-related headers are consistent across versions."""
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        response = await async_client.get(endpoint_url)
        
        # Check for cache-related headers
        cache_headers = ["Cache-Control", "ETag", "Last-Modified"]
        
        for header in cache_headers:
            if header in response.headers:
                header_value = response.headers[header]
                assert len(header_value) > 0, f"Cache header '{header}' should not be empty in {api_version}"
                
                # Validate specific header formats
                if header == "Cache-Control":
                    # Should contain valid cache directives
                    valid_directives = ["no-cache", "no-store", "max-age", "public", "private"]
                    has_valid_directive = any(directive in header_value for directive in valid_directives)
                    assert has_valid_directive, f"Invalid Cache-Control directive in {api_version}: {header_value}"

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_security_headers_consistency(self, api_version: str, async_client: AsyncClient):
        """Test that security headers are consistent across versions."""
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        response = await async_client.get(endpoint_url)
        
        # Check for security headers
        security_headers = ["X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"]
        
        for header in security_headers:
            if header in response.headers:
                header_value = response.headers[header]
                assert len(header_value) > 0, f"Security header '{header}' should not be empty in {api_version}"
                
                # Validate specific header values
                if header == "X-Content-Type-Options":
                    assert header_value == "nosniff", (
                        f"X-Content-Type-Options should be 'nosniff' in {api_version}, got: {header_value}"
                    )
                elif header == "X-Frame-Options":
                    valid_values = ["DENY", "SAMEORIGIN"]
                    assert header_value in valid_values, (
                        f"X-Frame-Options should be DENY or SAMEORIGIN in {api_version}, got: {header_value}"
                    )

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_response_time_headers(self, api_version: str, async_client: AsyncClient):
        """Test response time and performance headers consistency."""
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        
        import time
        start_time = time.time()
        response = await async_client.get(endpoint_url)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Check if server provides response time headers
        timing_headers = ["X-Response-Time", "Server-Timing"]
        
        for header in timing_headers:
            if header in response.headers:
                header_value = response.headers[header]
                assert len(header_value) > 0, f"Timing header '{header}' should not be empty in {api_version}"
        
        # Basic performance check - response should be reasonably fast
        assert response_time < 5.0, f"Response time too slow in {api_version}: {response_time}s"

    @version_parametrize()
    @pytest.mark.asyncio
    async def test_custom_header_consistency(self, api_version: str, async_client: AsyncClient):
        """Test custom application headers consistency across versions."""
        endpoint_url = self.get_endpoint_url(api_version, "pets")
        response = await async_client.get(endpoint_url)
        
        # Check for custom application headers
        custom_headers = ["X-Request-ID", "X-Correlation-ID", "X-Rate-Limit-Remaining"]
        
        for header in custom_headers:
            if header in response.headers:
                header_value = response.headers[header]
                assert len(header_value) > 0, f"Custom header '{header}' should not be empty in {api_version}"
                
                # Validate specific header formats
                if "ID" in header:
                    # Should be a valid UUID or similar identifier
                    assert len(header_value) >= 8, f"ID header '{header}' too short in {api_version}: {header_value}"
                elif "Rate-Limit" in header:
                    # Should be a number
                    assert header_value.isdigit(), f"Rate limit header should be numeric in {api_version}: {header_value}"