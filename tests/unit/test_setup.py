"""
Setup and integration tests for the dynamic testing framework.

Tests that the configuration system integrates properly with the framework components.
"""

import pytest
from pathlib import Path

from tests.dynamic.config_manager import VersionConfigManager, get_config_manager, reset_config_manager


class TestFrameworkSetup:
    """Test framework setup and integration."""
    
    def setup_method(self):
        """Reset global config manager before each test."""
        reset_config_manager()
    
    def test_default_config_file_exists(self):
        """Test that the default configuration file exists and is valid."""
        # The default config should be at tests/config/version_config.yaml
        config_path = Path("tests/config/version_config.yaml")
        assert config_path.exists(), "Default configuration file should exist"
        
        # Should be able to load it without errors
        manager = VersionConfigManager(str(config_path))
        
        # Should have v1 and v2 versions
        versions = manager.get_supported_versions()
        assert "v1" in versions
        assert "v2" in versions
    
    def test_config_manager_with_default_path(self):
        """Test that config manager works with default path resolution."""
        # This should use the default path resolution
        manager = VersionConfigManager()
        
        # Should be able to access basic functionality
        versions = manager.get_supported_versions()
        assert len(versions) >= 2
        
        # Should have basic endpoints
        pets_url_v1 = manager.get_endpoint_url("v1", "pets")
        pets_url_v2 = manager.get_endpoint_url("v2", "pets")
        
        assert pets_url_v1 == "/api/v1/pets"
        assert pets_url_v2 == "/api/v2/pets"
    
    def test_version_specific_features(self):
        """Test that version-specific features are configured correctly."""
        manager = VersionConfigManager()
        
        # V1 should not have advanced features
        assert manager.get_feature_availability("v1", "health_records") is False
        assert manager.get_feature_availability("v1", "statistics") is False
        assert manager.get_feature_availability("v1", "enhanced_filtering") is False
        
        # V2 should have advanced features
        assert manager.get_feature_availability("v2", "health_records") is True
        assert manager.get_feature_availability("v2", "statistics") is True
        assert manager.get_feature_availability("v2", "enhanced_filtering") is True
    
    def test_schema_field_differences(self):
        """Test that schema fields are different between versions."""
        manager = VersionConfigManager()
        
        # Pet create fields should be different
        v1_pet_fields = set(manager.get_schema_fields("v1", "pet_create"))
        v2_pet_fields = set(manager.get_schema_fields("v2", "pet_create"))
        
        # V2 should have more fields than V1
        assert len(v2_pet_fields) > len(v1_pet_fields)
        
        # V1 fields should be a subset of V2 fields (mostly)
        common_fields = {"name", "species", "breed", "owner_id", "gender", "weight"}
        assert common_fields.issubset(v1_pet_fields)
        assert common_fields.issubset(v2_pet_fields)
        
        # V2 should have additional fields
        v2_only_fields = {"temperament", "behavioral_notes", "emergency_contact"}
        assert v2_only_fields.issubset(v2_pet_fields)
        assert not v2_only_fields.issubset(v1_pet_fields)
    
    def test_default_values_configuration(self):
        """Test that default values are configured properly."""
        manager = VersionConfigManager()
        
        # Both versions should have default values for pet creation
        v1_defaults = manager.get_default_values("v1", "pet_create")
        v2_defaults = manager.get_default_values("v2", "pet_create")
        
        # Should have common defaults
        assert v1_defaults["name"] == "Buddy"
        assert v1_defaults["species"] == "dog"
        assert v2_defaults["name"] == "Buddy"
        assert v2_defaults["species"] == "dog"
        
        # V2 should have additional defaults
        assert "temperament" not in v1_defaults
        assert "temperament" in v2_defaults
        assert v2_defaults["temperament"] == "Friendly"
    
    def test_endpoint_parameterization(self):
        """Test that parameterized endpoints work correctly."""
        manager = VersionConfigManager()
        
        # Health records endpoint should work with parameter
        pet_id = "test-pet-123"
        health_url = manager.get_endpoint_url("v2", "health_records", pet_id=pet_id)
        expected_url = f"/api/v2/pets/{pet_id}/health-records"
        assert health_url == expected_url
        
        # Should raise error if parameter is missing
        with pytest.raises(Exception):  # ConfigurationError
            manager.get_endpoint_url("v2", "health_records")
    
    def test_global_settings(self):
        """Test that global settings are accessible."""
        manager = VersionConfigManager()
        
        settings = manager.get_global_settings()
        
        # Should have some basic settings
        assert "default_timeout" in settings
        assert "max_retries" in settings
        assert isinstance(settings["default_timeout"], int)
        assert isinstance(settings["max_retries"], int)
    
    def test_global_config_manager_instance(self):
        """Test that global config manager instance works."""
        # Should be able to get global instance
        manager = get_config_manager()
        
        # Should work with basic operations
        versions = manager.get_supported_versions()
        assert len(versions) >= 2
        
        # Should be singleton
        manager2 = get_config_manager()
        assert manager is manager2