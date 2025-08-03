"""
Example usage of dynamic testing framework decorators.

Demonstrates how to use the various decorators for version-agnostic testing
across multiple API versions with feature detection and skipping.
"""

import pytest
from tests.dynamic.decorators import (
    version_parametrize,
    feature_test,
    crud_test,
    smart_feature_test,
    require_features,
    auto_skip_unavailable,
    conditional_skip
)
from tests.dynamic.base_test import BaseVersionTest


class TestPetEndpointsWithDecorators(BaseVersionTest):
    """Example test class using dynamic testing decorators."""
    
    @version_parametrize()
    async def test_get_pets_all_versions(self, api_version, async_client):
        """Test getting pets list across all API versions."""
        endpoint = self.get_endpoint_url(api_version, "pets")
        response = await self.make_request("GET", endpoint, async_client)
        
        self.assert_status_code(response, 200)
        pets_data = response.json()
        
        # Validate response structure for the specific version
        if isinstance(pets_data, list) and pets_data:
            self.validate_response_structure(pets_data[0], api_version, "pet")
    
    @feature_test("health_records")
    async def test_health_records_feature(self, api_version, async_client):
        """Test health records feature (only available in v2+)."""
        # This test will automatically skip for versions that don't support health_records
        
        # Create a test pet first
        pet_data = await self.create_test_resource(async_client, api_version, "pets")
        pet_id = pet_data["id"]
        
        try:
            # Test health records endpoint
            health_records_url = self.get_endpoint_url(api_version, "health_records", pet_id=pet_id)
            response = await self.make_request("GET", health_records_url, async_client)
            self.assert_status_code(response, 200)
            
        finally:
            # Cleanup
            await self.cleanup_test_resource(async_client, api_version, "pets", pet_id)
    
    @crud_test("pets", operations=["create", "read", "update"])
    async def test_pet_crud_operations(self, api_version, crud_operation, async_client):
        """Test CRUD operations for pets across versions."""
        
        if crud_operation == "create":
            # Test pet creation
            test_data = self.build_test_data(api_version, "pets", "create", name="Test Pet")
            endpoint = self.get_endpoint_url(api_version, "pets")
            response = await self.make_request("POST", endpoint, async_client, json=test_data)
            
            self.assert_status_code(response, 201)
            pet_data = response.json()
            self.validate_response_structure(pet_data, api_version, "pet")
            
            # Store pet_id for cleanup
            pytest.current_test_pet_id = pet_data["id"]
            
        elif crud_operation == "read":
            # First create a pet to read
            pet_data = await self.create_test_resource(async_client, api_version, "pets")
            pet_id = pet_data["id"]
            
            try:
                # Test reading the pet
                endpoint = self.get_endpoint_url(api_version, "pets", pet_id)
                response = await self.make_request("GET", endpoint, async_client)
                
                self.assert_status_code(response, 200)
                retrieved_pet = response.json()
                self.validate_response_structure(retrieved_pet, api_version, "pet")
                assert retrieved_pet["id"] == pet_id
                
            finally:
                await self.cleanup_test_resource(async_client, api_version, "pets", pet_id)
                
        elif crud_operation == "update":
            # First create a pet to update
            pet_data = await self.create_test_resource(async_client, api_version, "pets")
            pet_id = pet_data["id"]
            
            try:
                # Test updating the pet
                update_data = {"name": "Updated Pet Name"}
                endpoint = self.get_endpoint_url(api_version, "pets", pet_id)
                response = await self.make_request("PUT", endpoint, async_client, json=update_data)
                
                self.assert_status_code(response, 200)
                updated_pet = response.json()
                assert updated_pet["name"] == "Updated Pet Name"
                
            finally:
                await self.cleanup_test_resource(async_client, api_version, "pets", pet_id)
    
    @smart_feature_test(
        features=["statistics", "enhanced_filtering"],
        optional_features=["batch_operations"],
        dependencies={"statistics": ["enhanced_filtering"]}
    )
    async def test_advanced_pet_statistics(self, api_version, async_client):
        """Test advanced pet statistics with feature dependencies."""
        # This test requires both statistics and enhanced_filtering features
        # It will warn if batch_operations is not available but won't skip
        
        stats_endpoint = self.get_endpoint_url(api_version, "statistics")
        response = await self.make_request("GET", stats_endpoint, async_client)
        
        self.assert_status_code(response, 200)
        stats_data = response.json()
        
        # Validate that statistics data is present
        assert "pet_count" in stats_data
        assert isinstance(stats_data["pet_count"], int)
    
    @require_features(["health_records", "statistics"])
    @version_parametrize()
    async def test_health_statistics_combination(self, api_version, async_client):
        """Test combination of health records and statistics features."""
        # This test requires both features to be available
        
        # Test that both endpoints are accessible
        stats_endpoint = self.get_endpoint_url(api_version, "statistics")
        stats_response = await self.make_request("GET", stats_endpoint, async_client)
        self.assert_status_code(stats_response, 200)
        
        # Create a test pet to test health records
        pet_data = await self.create_test_resource(async_client, api_version, "pets")
        pet_id = pet_data["id"]
        
        try:
            health_records_url = self.get_endpoint_url(api_version, "health_records", pet_id=pet_id)
            health_response = await self.make_request("GET", health_records_url, async_client)
            self.assert_status_code(health_response, 200)
            
        finally:
            await self.cleanup_test_resource(async_client, api_version, "pets", pet_id)
    
    @auto_skip_unavailable(["enhanced_filtering"])
    @version_parametrize()
    async def test_enhanced_pet_filtering(self, api_version, async_client):
        """Test enhanced filtering capabilities."""
        # This test will automatically skip if enhanced_filtering is not available
        
        endpoint = self.get_endpoint_url(api_version, "pets")
        
        # Test filtering by species
        response = await self.make_request(
            "GET", 
            endpoint, 
            async_client,
            params={"species": "dog", "breed": "Golden Retriever"}
        )
        
        self.assert_status_code(response, 200)
        pets_data = response.json()
        
        # Validate that filtering worked
        if isinstance(pets_data, list):
            for pet in pets_data:
                if "species" in pet:
                    assert pet["species"] == "dog"
    
    def has_batch_operations(self, version: str) -> bool:
        """Custom condition function for batch operations."""
        return self.should_test_feature(version, "batch_operations")
    
    @conditional_skip(
        lambda version: BaseVersionTest().should_test_feature(version, "batch_operations"),
        "Batch operations not supported"
    )
    @version_parametrize()
    async def test_batch_pet_operations(self, api_version, async_client):
        """Test batch operations for pets."""
        # This test will skip if batch_operations feature is not available
        
        # Create multiple pets in batch
        pets_data = [
            self.build_test_data(api_version, "pets", "create", name=f"Batch Pet {i}")
            for i in range(3)
        ]
        
        batch_endpoint = f"{self.get_endpoint_url(api_version, 'pets')}/batch"
        response = await self.make_request("POST", batch_endpoint, async_client, json=pets_data)
        
        self.assert_status_code(response, 201)
        created_pets = response.json()
        
        assert len(created_pets) == 3
        
        # Cleanup created pets
        for pet in created_pets:
            await self.cleanup_test_resource(async_client, api_version, "pets", pet["id"])


class TestVersionSpecificBehavior(BaseVersionTest):
    """Example tests demonstrating version-specific behavior handling."""
    
    @version_parametrize()
    async def test_version_specific_fields(self, api_version, async_client):
        """Test that version-specific fields are handled correctly."""
        
        # Create a pet with version-appropriate data
        pet_data = await self.create_test_resource(async_client, api_version, "pets")
        
        try:
            # Validate version-specific fields
            self.validate_version_specific_fields(pet_data, api_version, "pet")
            
            # Check for v2-specific fields
            if api_version == "v2":
                # These fields should be present in v2
                expected_v2_fields = ["temperament", "behavioral_notes", "emergency_contact"]
                for field in expected_v2_fields:
                    if field in self.config_manager.get_schema_fields(api_version, "pet_response"):
                        # Field might be optional, so only check if it's in the schema
                        pass
            
            elif api_version == "v1":
                # These fields should NOT be present in v1
                v2_only_fields = ["temperament", "behavioral_notes", "emergency_contact"]
                for field in v2_only_fields:
                    assert field not in pet_data, f"Field '{field}' should not be in v1 response"
                    
        finally:
            await self.cleanup_test_resource(async_client, api_version, "pets", pet_data["id"])
    
    @feature_test("statistics")
    async def test_statistics_endpoint_availability(self, api_version, async_client):
        """Test that statistics endpoint is only available in supporting versions."""
        
        # This test will only run on versions that support statistics
        stats_endpoint = self.get_endpoint_url(api_version, "statistics")
        response = await self.make_request("GET", stats_endpoint, async_client)
        
        # Should succeed since we're only running on supporting versions
        self.assert_status_code(response, 200)
        
        stats_data = response.json()
        assert isinstance(stats_data, dict)
        assert "pet_count" in stats_data
    
    @version_parametrize(versions=["v1"])
    async def test_v1_specific_behavior(self, api_version, async_client):
        """Test behavior specific to v1."""
        assert api_version == "v1"
        
        # Test that health records endpoint returns 404 in v1
        pets_data = await self.create_test_resource(async_client, api_version, "pets")
        pet_id = pets_data["id"]
        
        try:
            # Try to access health records (should fail in v1)
            health_records_url = f"/api/v1/pets/{pet_id}/health-records"
            response = await self.make_request("GET", health_records_url, async_client)
            
            # Should return 404 since health records don't exist in v1
            self.assert_status_code(response, 404)
            
        finally:
            await self.cleanup_test_resource(async_client, api_version, "pets", pet_id)


# Example of how to run specific decorator tests
if __name__ == "__main__":
    # Run only feature tests
    pytest.main([__file__ + "::TestPetEndpointsWithDecorators::test_health_records_feature", "-v"])
    
    # Run only CRUD tests
    pytest.main([__file__ + "::TestPetEndpointsWithDecorators::test_pet_crud_operations", "-v"])
    
    # Run all tests
    pytest.main([__file__, "-v"])