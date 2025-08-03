"""
Example test demonstrating the dynamic testing framework.

Shows how to use the BaseVersionTest class and version-aware fixtures
to create tests that work across multiple API versions.
"""

import pytest
from tests.dynamic.fixtures import parametrize_versions, parametrize_feature_versions
from tests.dynamic.base_test import BaseVersionTest


@parametrize_versions()
class TestDynamicFrameworkExample:
    """Example test class showing dynamic framework usage."""
    
    def test_endpoint_url_building(self, api_version: str, base_test: BaseVersionTest):
        """Test that endpoint URLs are built correctly for each version."""
        # Test basic endpoint building
        pets_url = base_test.get_endpoint_url(api_version, "pets")
        expected_base = f"/api/{api_version}/pets"
        assert expected_base in pets_url
        
        # Test endpoint building with resource ID
        pet_url = base_test.get_endpoint_url(api_version, "pets", "123")
        expected_with_id = f"/api/{api_version}/pets/123"
        assert expected_with_id in pet_url
    
    def test_feature_availability_checking(self, api_version: str, base_test: BaseVersionTest):
        """Test that feature availability is checked correctly."""
        # Health records should only be available in v2
        has_health_records = base_test.should_test_feature(api_version, "health_records")
        
        if api_version == "v1":
            assert not has_health_records, "V1 should not have health records"
        elif api_version == "v2":
            assert has_health_records, "V2 should have health records"
    
    def test_version_specific_data_generation(self, api_version: str, base_test: BaseVersionTest):
        """Test that test data is generated appropriately for each version."""
        # Generate pet creation data
        pet_data = base_test.build_test_data(api_version, "pet", "create", name="TestPet")
        
        # All versions should have basic fields
        assert "name" in pet_data
        assert "species" in pet_data
        assert pet_data["name"] == "TestPet"
        
        # Check version-specific fields
        if api_version == "v1":
            assert "temperament" not in pet_data
            assert "behavioral_notes" not in pet_data
        elif api_version == "v2":
            assert "temperament" in pet_data
            assert "behavioral_notes" in pet_data
    
    def test_required_and_optional_fields(self, api_version: str, base_test: BaseVersionTest):
        """Test that required and optional fields are identified correctly."""
        # Get required fields for pet creation
        required_fields = base_test.get_required_fields(api_version, "pet", "create")
        optional_fields = base_test.get_optional_fields(api_version, "pet", "create")
        
        # Basic required fields should be present in all versions
        assert "name" in required_fields
        assert "species" in required_fields
        assert "owner_id" in required_fields
        
        # Optional fields should include breed and gender
        assert "breed" in optional_fields
        assert "gender" in optional_fields
        
        # Version-specific optional fields
        if api_version == "v2":
            assert "temperament" in optional_fields
            assert "behavioral_notes" in optional_fields


@parametrize_feature_versions("health_records")
class TestHealthRecordsFeature:
    """Example test class for feature-specific testing."""
    
    def test_health_records_endpoint_available(self, api_version: str, base_test: BaseVersionTest):
        """Test that health records endpoints are available in supporting versions."""
        # This test only runs on versions that support health_records
        assert base_test.should_test_feature(api_version, "health_records")
        
        # Should be able to build health records endpoint URL
        health_records_url = base_test.get_endpoint_url(api_version, "health_records", pet_id="123")
        expected = f"/api/{api_version}/pets/123/health-records"
        assert expected in health_records_url
    
    def test_health_record_data_generation(self, api_version: str, base_test: BaseVersionTest):
        """Test health record data generation for supporting versions."""
        # Generate health record creation data
        health_record_data = base_test.build_test_data(api_version, "health_record", "create")
        
        # Should have required fields
        required_fields = base_test.get_required_fields(api_version, "health_record", "create")
        for field in required_fields:
            assert field in health_record_data, f"Required field '{field}' missing"


class TestFixtureUsageExamples:
    """Examples of using fixtures directly without inheriting from BaseVersionTest."""
    
    @parametrize_versions()
    def test_using_endpoint_builder_fixture(self, api_version: str, endpoint_builder):
        """Example using the endpoint_builder fixture."""
        pets_url = endpoint_builder("pets")
        assert f"/api/{api_version}/pets" in pets_url
        
        pet_url = endpoint_builder("pets", "456")
        assert f"/api/{api_version}/pets/456" in pet_url
    
    @parametrize_versions()
    def test_using_test_data_builder_fixture(self, api_version: str, test_data_builder):
        """Example using the test_data_builder fixture."""
        pet_data = test_data_builder("pet", "create", name="FixturePet")
        
        assert pet_data["name"] == "FixturePet"
        assert "species" in pet_data
        
        # Version-specific assertions
        if api_version == "v2":
            assert "temperament" in pet_data
        else:
            assert "temperament" not in pet_data
    
    @parametrize_versions()
    def test_using_feature_checker_fixture(self, api_version: str, feature_checker):
        """Example using the feature_checker fixture."""
        # Check various features
        has_health_records = feature_checker("health_records")
        has_statistics = feature_checker("statistics")
        
        if api_version == "v1":
            assert not has_health_records
            assert not has_statistics
        elif api_version == "v2":
            assert has_health_records
            assert has_statistics
    
    @parametrize_versions()
    def test_conditional_feature_testing(self, api_version: str, feature_checker, skip_if_feature_unavailable):
        """Example of conditional feature testing."""
        # Skip this test if batch operations are not supported
        skip_if_feature_unavailable("batch_operations")
        
        # If we get here, batch operations are supported
        assert feature_checker("batch_operations")
        assert api_version == "v2"  # Only v2 supports batch operations


# Example of using parametrization helpers directly
@pytest.mark.parametrize("resource", ["pets", "users", "appointments"])
@parametrize_versions()
class TestResourceEndpoints:
    """Example of testing multiple resources across versions."""
    
    def test_resource_endpoint_building(self, api_version: str, resource: str, base_test: BaseVersionTest):
        """Test endpoint building for different resources."""
        endpoint_url = base_test.get_endpoint_url(api_version, resource)
        expected = f"/api/{api_version}/{resource}"
        assert expected in endpoint_url
    
    def test_resource_data_generation(self, api_version: str, resource: str, base_test: BaseVersionTest):
        """Test data generation for different resources."""
        # Convert resource name to singular for schema lookup
        resource_singular = resource.rstrip('s')  # Simple pluralization removal
        
        try:
            test_data = base_test.build_test_data(api_version, resource_singular, "create")
            assert isinstance(test_data, dict)
            assert len(test_data) > 0
        except Exception:
            # Some resources might not have create schemas configured
            pytest.skip(f"No create schema configured for {resource_singular} in {api_version}")