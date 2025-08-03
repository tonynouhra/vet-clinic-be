"""
Unit tests for the VersionConfigManager.

Tests configuration loading, validation, and access methods.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from tests.dynamic.config_manager import (
    VersionConfigManager,
    ConfigurationError,
    get_config_manager,
    reset_config_manager
)


class TestVersionConfigManager:
    """Test cases for VersionConfigManager class."""
    
    def setup_method(self):
        """Reset global config manager before each test."""
        reset_config_manager()
    
    def create_test_config(self) -> dict:
        """Create a minimal valid test configuration."""
        return {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {
                        "health_records": False,
                        "statistics": False
                    },
                    "endpoints": {
                        "pets": "/api/v1/pets",
                        "users": "/api/v1/users"
                    },
                    "schema_fields": {
                        "pet_create": ["name", "species", "owner_id"],
                        "pet_response": ["id", "name", "species", "created_at"]
                    },
                    "required_fields": {
                        "pet_create": ["name", "species", "owner_id"]
                    },
                    "optional_fields": {
                        "pet_create": []
                    },
                    "default_values": {
                        "pet_create": {
                            "name": "Buddy",
                            "species": "dog"
                        }
                    }
                },
                "v2": {
                    "base_url": "/api/v2",
                    "features": {
                        "health_records": True,
                        "statistics": True
                    },
                    "endpoints": {
                        "pets": "/api/v2/pets",
                        "users": "/api/v2/users",
                        "health_records": "/api/v2/pets/{pet_id}/health-records"
                    },
                    "schema_fields": {
                        "pet_create": ["name", "species", "owner_id", "temperament"],
                        "pet_response": ["id", "name", "species", "temperament", "created_at"]
                    },
                    "required_fields": {
                        "pet_create": ["name", "species", "owner_id"]
                    },
                    "optional_fields": {
                        "pet_create": ["temperament"]
                    },
                    "default_values": {
                        "pet_create": {
                            "name": "Buddy",
                            "species": "dog",
                            "temperament": "Friendly"
                        }
                    }
                }
            },
            "global_settings": {
                "default_timeout": 30,
                "max_retries": 3
            }
        }
    
    def test_init_with_valid_config_file(self):
        """Test initialization with a valid configuration file."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            assert manager.get_supported_versions() == ["v1", "v2"]
        finally:
            Path(config_path).unlink()
    
    def test_init_with_nonexistent_file(self):
        """Test initialization with non-existent configuration file."""
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            VersionConfigManager("/nonexistent/path/config.yaml")
    
    def test_init_with_invalid_yaml(self):
        """Test initialization with invalid YAML content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name
        
        try:
            with pytest.raises(ConfigurationError, match="Invalid YAML"):
                VersionConfigManager(config_path)
        finally:
            Path(config_path).unlink()
    
    def test_init_with_empty_config(self):
        """Test initialization with empty configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({}, f)
            config_path = f.name
        
        try:
            with pytest.raises(ConfigurationError, match="Configuration is empty"):
                VersionConfigManager(config_path)
        finally:
            Path(config_path).unlink()
    
    def test_init_with_missing_required_sections(self):
        """Test initialization with missing required sections."""
        invalid_config = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1"
                    # Missing required sections: features, endpoints, schema_fields
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            config_path = f.name
        
        try:
            with pytest.raises(ConfigurationError, match="missing required section"):
                VersionConfigManager(config_path)
        finally:
            Path(config_path).unlink()
    
    def test_get_version_config(self):
        """Test getting configuration for a specific version."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            
            v1_config = manager.get_version_config("v1")
            assert v1_config["base_url"] == "/api/v1"
            assert v1_config["features"]["health_records"] is False
            
            v2_config = manager.get_version_config("v2")
            assert v2_config["base_url"] == "/api/v2"
            assert v2_config["features"]["health_records"] is True
        finally:
            Path(config_path).unlink()
    
    def test_get_version_config_invalid_version(self):
        """Test getting configuration for non-existent version."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            
            with pytest.raises(ConfigurationError, match="Version 'v3' not found"):
                manager.get_version_config("v3")
        finally:
            Path(config_path).unlink()
    
    def test_get_supported_versions(self):
        """Test getting list of supported versions."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            versions = manager.get_supported_versions()
            assert set(versions) == {"v1", "v2"}
        finally:
            Path(config_path).unlink()
    
    def test_get_feature_availability(self):
        """Test checking feature availability."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            
            # V1 should not have health_records
            assert manager.get_feature_availability("v1", "health_records") is False
            assert manager.get_feature_availability("v1", "statistics") is False
            
            # V2 should have health_records
            assert manager.get_feature_availability("v2", "health_records") is True
            assert manager.get_feature_availability("v2", "statistics") is True
            
            # Non-existent feature should return False
            assert manager.get_feature_availability("v1", "nonexistent") is False
            
            # Non-existent version should return False
            assert manager.get_feature_availability("v99", "health_records") is False
        finally:
            Path(config_path).unlink()
    
    def test_get_endpoint_url(self):
        """Test getting endpoint URLs."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            
            # Basic endpoint
            assert manager.get_endpoint_url("v1", "pets") == "/api/v1/pets"
            assert manager.get_endpoint_url("v2", "pets") == "/api/v2/pets"
            
            # Parameterized endpoint
            pet_id = "123"
            health_url = manager.get_endpoint_url("v2", "health_records", pet_id=pet_id)
            assert health_url == f"/api/v2/pets/{pet_id}/health-records"
            
            # Non-existent resource should raise error
            with pytest.raises(ConfigurationError, match="Resource 'nonexistent' not found"):
                manager.get_endpoint_url("v1", "nonexistent")
        finally:
            Path(config_path).unlink()
    
    def test_get_endpoint_url_missing_parameter(self):
        """Test getting endpoint URL with missing required parameter."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            
            # Missing pet_id parameter should raise error
            with pytest.raises(ConfigurationError, match="Missing required parameter"):
                manager.get_endpoint_url("v2", "health_records")
        finally:
            Path(config_path).unlink()
    
    def test_get_schema_fields(self):
        """Test getting schema fields."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            
            # V1 pet create fields
            v1_fields = manager.get_schema_fields("v1", "pet_create")
            assert set(v1_fields) == {"name", "species", "owner_id"}
            
            # V2 pet create fields (should include temperament)
            v2_fields = manager.get_schema_fields("v2", "pet_create")
            assert set(v2_fields) == {"name", "species", "owner_id", "temperament"}
            
            # Non-existent schema should raise error
            with pytest.raises(ConfigurationError, match="Schema type 'nonexistent' not found"):
                manager.get_schema_fields("v1", "nonexistent")
        finally:
            Path(config_path).unlink()
    
    def test_get_required_fields(self):
        """Test getting required fields."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            
            required_fields = manager.get_required_fields("v1", "pet_create")
            assert set(required_fields) == {"name", "species", "owner_id"}
            
            # Non-existent schema should return empty list
            empty_fields = manager.get_required_fields("v1", "nonexistent")
            assert empty_fields == []
        finally:
            Path(config_path).unlink()
    
    def test_get_optional_fields(self):
        """Test getting optional fields."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            
            # V1 has no optional fields
            v1_optional = manager.get_optional_fields("v1", "pet_create")
            assert v1_optional == []
            
            # V2 has temperament as optional
            v2_optional = manager.get_optional_fields("v2", "pet_create")
            assert "temperament" in v2_optional
        finally:
            Path(config_path).unlink()
    
    def test_get_default_values(self):
        """Test getting default values."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            
            v1_defaults = manager.get_default_values("v1", "pet_create")
            assert v1_defaults["name"] == "Buddy"
            assert v1_defaults["species"] == "dog"
            assert "temperament" not in v1_defaults
            
            v2_defaults = manager.get_default_values("v2", "pet_create")
            assert v2_defaults["name"] == "Buddy"
            assert v2_defaults["species"] == "dog"
            assert v2_defaults["temperament"] == "Friendly"
        finally:
            Path(config_path).unlink()
    
    def test_get_base_url(self):
        """Test getting base URL."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            
            assert manager.get_base_url("v1") == "/api/v1"
            assert manager.get_base_url("v2") == "/api/v2"
        finally:
            Path(config_path).unlink()
    
    def test_get_global_settings(self):
        """Test getting global settings."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            
            settings = manager.get_global_settings()
            assert settings["default_timeout"] == 30
            assert settings["max_retries"] == 3
        finally:
            Path(config_path).unlink()
    
    def test_has_schema_type(self):
        """Test checking if schema type exists."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            
            assert manager.has_schema_type("v1", "pet_create") is True
            assert manager.has_schema_type("v1", "pet_response") is True
            assert manager.has_schema_type("v1", "nonexistent") is False
            assert manager.has_schema_type("v99", "pet_create") is False
        finally:
            Path(config_path).unlink()
    
    def test_get_features_for_version(self):
        """Test getting all features for a version."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            
            v1_features = manager.get_features_for_version("v1")
            assert v1_features["health_records"] is False
            assert v1_features["statistics"] is False
            
            v2_features = manager.get_features_for_version("v2")
            assert v2_features["health_records"] is True
            assert v2_features["statistics"] is True
        finally:
            Path(config_path).unlink()
    
    def test_get_versions_supporting_feature(self):
        """Test getting versions that support a feature."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            
            # health_records only supported in v2
            health_versions = manager.get_versions_supporting_feature("health_records")
            assert health_versions == ["v2"]
            
            # statistics only supported in v2
            stats_versions = manager.get_versions_supporting_feature("statistics")
            assert stats_versions == ["v2"]
            
            # Non-existent feature should return empty list
            none_versions = manager.get_versions_supporting_feature("nonexistent")
            assert none_versions == []
        finally:
            Path(config_path).unlink()
    
    def test_reload_config(self):
        """Test reloading configuration."""
        config_data = self.create_test_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = VersionConfigManager(config_path)
            
            # Initial state
            assert manager.get_feature_availability("v1", "health_records") is False
            
            # Modify config file
            config_data["versions"]["v1"]["features"]["health_records"] = True
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            # Should still be False until reload
            assert manager.get_feature_availability("v1", "health_records") is False
            
            # After reload, should be True
            manager.reload_config()
            assert manager.get_feature_availability("v1", "health_records") is True
        finally:
            Path(config_path).unlink()


class TestGlobalConfigManager:
    """Test cases for global configuration manager functions."""
    
    def setup_method(self):
        """Reset global config manager before each test."""
        reset_config_manager()
    
    def test_get_config_manager_singleton(self):
        """Test that get_config_manager returns singleton instance."""
        # Create a temporary config file
        config_data = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {},
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name"]}
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            # First call should create instance
            manager1 = get_config_manager(config_path)
            
            # Second call should return same instance
            manager2 = get_config_manager()
            
            assert manager1 is manager2
        finally:
            Path(config_path).unlink()
    
    def test_reset_config_manager(self):
        """Test resetting global configuration manager."""
        # Create a temporary config file
        config_data = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {},
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name"]}
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            # Create instance
            manager1 = get_config_manager(config_path)
            
            # Reset
            reset_config_manager()
            
            # New instance should be different
            manager2 = get_config_manager(config_path)
            
            assert manager1 is not manager2
        finally:
            Path(config_path).unlink()