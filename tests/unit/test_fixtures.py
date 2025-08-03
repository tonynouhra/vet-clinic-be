"""
Unit tests for dynamic testing fixtures.

Tests the version-aware pytest fixtures to ensure they work correctly
with the configuration system.
"""

import pytest
from typing import Dict, Any, List

from tests.dynamic.fixtures import (
    parametrize_versions,
    parametrize_feature_versions,
    parametrize_resources,
    parametrize_crud_operations
)
from tests.dynamic.config_manager import get_config_manager, VersionConfigManager
from tests.dynamic.base_test import BaseVersionTest


class TestVersionFixtures:
    """Test version-aware fixtures."""
    
    def test_config_manager_fixture(self, config_manager: VersionConfigManager):
        """Test that config_manager fixture provides valid instance."""
        assert isinstance(config_manager, VersionConfigManager)
        assert len(config_manager.get_supported_versions()) > 0
    
    def test_supported_versions_fixture(self, supported_versions: List[str]):
        """Test that supported_versions fixture provides version list."""
        assert isinstance(supported_versions, list)
        assert len(supported_versions) > 0
        assert "v1" in supported_versions
        assert "v2" in supported_versions
    
    @parametrize_versions()
    def test_api_version_fixture(self, api_version: str):
        """Test that api_version fixture provides valid versions."""
        assert isinstance(api_version, str)
        assert api_version in ["v1", "v2"]
    
    @parametrize_versions()
    def test_version_config_fixture(self, api_version: str, version_config: Dict[str, Any]):
        """Test that version_config fixture provides valid configuration."""
        assert isinstance(version_config, dict)
        assert "base_url" in version_config
        assert "features" in version_config
        assert "endpoints" in version_config
        assert "schema_fields" in version_config
        
        # Verify base_url format
        assert version_config["base_url"].startswith("/api/")
        assert api_version in version_config["base_url"]
    
    @parametrize_versions()
    def test_base_url_fixture(self, api_version: str, base_url: str):
        """Test that base_url fixture provides correct URL."""
        assert isinstance(base_url, str)
        assert base_url.startswith("/api/")
        assert api_version in base_url
    
    @parametrize_versions()
    def test_version_features_fixture(self, api_version: str, version_features: Dict[str, bool]):
        """Test that version_features fixture provides feature mapping."""
        assert isinstance(version_features, dict)
        
        # Check that common features are present
        expected_features = [
            "health_records", "statistics", "enhanced_filtering", 
            "batch_operations", "temperament", "behavioral_notes"
        ]
        
        for feature in expected_features:
            assert feature in version_features
            assert isinstance(version_features[feature], bool)
        
        # Verify version-specific feature availability
        if api_version == "v1":
            assert not version_features["health_records"]
            assert not version_features["statistics"]
        elif api_version == "v2":
            assert version_features["health_records"]
            assert version_features["statistics"]
    
    def test_base_test_fixture(self, base_test: BaseVersionTest):
        """Test that base_test fixture provides BaseVersionTest instance."""
        assert isinstance(base_test, BaseVersionTest)
        assert hasattr(base_test, "get_endpoint_url")
        assert hasattr(base_test, "should_test_feature")
        assert hasattr(base_test, "validate_response_structure")
    
    @parametrize_versions()
    def test_endpoint_builder_fixture(self, api_version: str, endpoint_builder):
        """Test that endpoint_builder fixture provides working function."""
        assert callable(endpoint_builder)
        
        # Test building pet endpoint
        pets_url = endpoint_builder("pets")
        assert isinstance(pets_url, str)
        assert f"/api/{api_version}/pets" in pets_url
        
        # Test building endpoint with resource ID
        pet_url = endpoint_builder("pets", "123")
        assert isinstance(pet_url, str)
        assert f"/api/{api_version}/pets/123" in pet_url
    
    @parametrize_versions()
    def test_test_data_builder_fixture(self, api_version: str, test_data_builder):
        """Test that test_data_builder fixture provides working function."""
        assert callable(test_data_builder)
        
        # Test building pet create data
        pet_data = test_data_builder("pet", "create")
        assert isinstance(pet_data, dict)
        
        # Test with overrides
        pet_data_override = test_data_builder("pet", "create", name="TestPet")
        assert isinstance(pet_data_override, dict)
        assert pet_data_override.get("name") == "TestPet"
    
    @parametrize_versions()
    def test_feature_checker_fixture(self, api_version: str, feature_checker):
        """Test that feature_checker fixture provides working function."""
        assert callable(feature_checker)
        
        # Test checking known features
        health_records_available = feature_checker("health_records")
        assert isinstance(health_records_available, bool)
        
        if api_version == "v1":
            assert not health_records_available
        elif api_version == "v2":
            assert health_records_available
    
    @parametrize_versions()
    def test_skip_if_feature_unavailable_fixture(self, api_version: str, skip_if_feature_unavailable):
        """Test that skip_if_feature_unavailable fixture provides working function."""
        assert callable(skip_if_feature_unavailable)
        
        # This test should not skip for any version since we're not calling the function
        # with an unavailable feature
        pass


class TestParametrizationHelpers:
    """Test parametrization helper functions."""
    
    def test_parametrize_versions_default(self):
        """Test parametrize_versions with default parameters."""
        decorator = parametrize_versions()
        assert hasattr(decorator, 'mark')
        
        # Check that it includes all supported versions
        config_manager = get_config_manager()
        supported_versions = config_manager.get_supported_versions()
        
        # The decorator should parametrize over all supported versions
        assert len(supported_versions) > 0
    
    def test_parametrize_versions_specific(self):
        """Test parametrize_versions with specific versions."""
        decorator = parametrize_versions(["v1"])
        assert hasattr(decorator, 'mark')
    
    def test_parametrize_feature_versions(self):
        """Test parametrize_feature_versions."""
        # Test with a feature that exists in some versions
        decorator = parametrize_feature_versions("health_records")
        assert hasattr(decorator, 'mark')
        
        # Test with a feature that doesn't exist
        decorator_nonexistent = parametrize_feature_versions("nonexistent_feature")
        # Should return a skip marker
        assert hasattr(decorator_nonexistent, 'mark')
    
    def test_parametrize_resources(self):
        """Test parametrize_resources."""
        resources = ["pets", "users", "appointments"]
        decorator = parametrize_resources(resources)
        assert hasattr(decorator, 'mark')
    
    def test_parametrize_crud_operations_default(self):
        """Test parametrize_crud_operations with default operations."""
        decorator = parametrize_crud_operations()
        assert hasattr(decorator, 'mark')
    
    def test_parametrize_crud_operations_specific(self):
        """Test parametrize_crud_operations with specific operations."""
        operations = ["create", "read"]
        decorator = parametrize_crud_operations(operations)
        assert hasattr(decorator, 'mark')


# Example test using the fixtures
@parametrize_versions()
class TestExampleUsage:
    """Example test class showing fixture usage."""
    
    def test_version_aware_endpoint_building(self, api_version: str, endpoint_builder):
        """Example test using version-aware endpoint building."""
        pets_endpoint = endpoint_builder("pets")
        expected_base = f"/api/{api_version}/pets"
        assert expected_base in pets_endpoint
    
    def test_feature_conditional_logic(self, api_version: str, feature_checker):
        """Example test using feature-conditional logic."""
        if feature_checker("health_records"):
            # This logic only runs for versions that support health records
            assert api_version == "v2"
        else:
            # This logic runs for versions without health records
            assert api_version == "v1"
    
    def test_version_specific_data_generation(self, api_version: str, test_data_builder):
        """Example test using version-specific data generation."""
        pet_data = test_data_builder("pet", "create")
        
        # All versions should have basic fields
        assert "name" in pet_data
        assert "species" in pet_data
        
        # V2 should have additional fields
        if api_version == "v2":
            assert "temperament" in pet_data
            assert "behavioral_notes" in pet_data