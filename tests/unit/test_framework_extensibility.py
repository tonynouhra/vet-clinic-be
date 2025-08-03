"""
Tests for framework extensibility features.

Tests the framework's ability to handle unknown versions, graceful degradation,
configuration validation, and backward compatibility maintenance.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, MagicMock

from tests.dynamic.config_manager import VersionConfigManager, ConfigurationError, reset_config_manager
from tests.dynamic.base_test import BaseVersionTest
from tests.dynamic.data_factory import TestDataFactory


class TestFrameworkExtensibility:
    """Test framework extensibility and future version support."""
    
    def setup_method(self):
        """Reset configuration manager before each test."""
        reset_config_manager()
    
    def create_test_config(self, config_data: Dict[str, Any]) -> str:
        """Create a temporary configuration file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            return f.name
    
    def test_unknown_version_parameter_handling(self):
        """Test framework handles unknown version parameters gracefully."""
        # Create config with unknown version
        config_data = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {"basic": True},
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name", "species"]}
                },
                "v_unknown": {
                    "base_url": "/api/v_unknown",
                    "features": {"experimental": True, "unknown_feature": True},
                    "endpoints": {"pets": "/api/v_unknown/pets", "unknown_resource": "/api/v_unknown/unknown"},
                    "schema_fields": {
                        "pet_create": ["name", "species", "unknown_field"],
                        "unknown_schema": ["field1", "field2"]
                    }
                }
            }
        }
        
        config_path = self.create_test_config(config_data)
        config_manager = VersionConfigManager(config_path)
        
        # Test that unknown version is recognized
        versions = config_manager.get_supported_versions()
        assert "v_unknown" in versions
        
        # Test that unknown version configuration can be retrieved
        unknown_config = config_manager.get_version_config("v_unknown")
        assert unknown_config["base_url"] == "/api/v_unknown"
        assert unknown_config["features"]["unknown_feature"] is True
        
        # Test that unknown features are handled
        assert config_manager.get_feature_availability("v_unknown", "unknown_feature") is True
        assert config_manager.get_feature_availability("v1", "unknown_feature") is False
        
        # Test that unknown endpoints are accessible
        unknown_endpoint = config_manager.get_endpoint_url("v_unknown", "unknown_resource")
        assert unknown_endpoint == "/api/v_unknown/unknown"
        
        # Test that unknown schema fields are handled
        unknown_fields = config_manager.get_schema_fields("v_unknown", "unknown_schema")
        assert unknown_fields == ["field1", "field2"]
        
        # Cleanup
        Path(config_path).unlink()
    
    def test_graceful_degradation_missing_features(self):
        """Test graceful degradation when features are missing from configuration."""
        # Create minimal config missing some standard features
        config_data = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {},  # Empty features
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name"]}
                },
                "v2": {
                    "base_url": "/api/v2",
                    "features": {"health_records": True},  # Only one feature
                    "endpoints": {"pets": "/api/v2/pets"},
                    "schema_fields": {"pet_create": ["name", "health_info"]}
                }
            }
        }
        
        config_path = self.create_test_config(config_data)
        config_manager = VersionConfigManager(config_path)
        
        # Test that missing features default to False
        assert config_manager.get_feature_availability("v1", "health_records") is False
        assert config_manager.get_feature_availability("v1", "statistics") is False
        assert config_manager.get_feature_availability("v1", "nonexistent_feature") is False
        
        # Test that existing features work normally
        assert config_manager.get_feature_availability("v2", "health_records") is True
        assert config_manager.get_feature_availability("v2", "statistics") is False
        
        # Test BaseVersionTest graceful handling
        base_test = BaseVersionTest()
        base_test._config_manager = config_manager
        
        # Should not raise exception, should return False
        assert base_test.should_test_feature("v1", "nonexistent_feature") is False
        
        # Should skip test gracefully
        with pytest.raises(pytest.skip.Exception):
            base_test.skip_if_feature_unavailable("v1", "health_records")
        
        # Cleanup
        Path(config_path).unlink()
    
    def test_graceful_degradation_missing_schema_fields(self):
        """Test graceful degradation when schema fields are missing."""
        config_data = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {"basic": True},
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name"]}
                    # Missing required_fields, optional_fields, default_values
                }
            }
        }
        
        config_path = self.create_test_config(config_data)
        config_manager = VersionConfigManager(config_path)
        
        # Test that missing schema sections return empty lists/dicts
        assert config_manager.get_required_fields("v1", "pet_create") == []
        assert config_manager.get_optional_fields("v1", "pet_create") == []
        assert config_manager.get_default_values("v1", "pet_create") == {}
        
        # Test BaseVersionTest graceful handling
        base_test = BaseVersionTest()
        base_test._config_manager = config_manager
        
        assert base_test.get_required_fields("v1", "pet") == []
        assert base_test.get_optional_fields("v1", "pet") == []
        assert base_test.get_test_data_template("v1", "pet") == {}
        
        # Cleanup
        Path(config_path).unlink()
    
    def test_configuration_validation_new_version_additions(self):
        """Test configuration validation when adding new versions."""
        # Test valid new version addition
        valid_config = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {"basic": True},
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name"]}
                },
                "v3": {  # New version
                    "base_url": "/api/v3",
                    "features": {"advanced": True, "ai_powered": True},
                    "endpoints": {"pets": "/api/v3/pets", "ai_analysis": "/api/v3/ai"},
                    "schema_fields": {
                        "pet_create": ["name", "species", "ai_profile"],
                        "ai_analysis_response": ["confidence", "recommendations"]
                    }
                }
            }
        }
        
        config_path = self.create_test_config(valid_config)
        
        # Should not raise exception
        config_manager = VersionConfigManager(config_path)
        assert "v3" in config_manager.get_supported_versions()
        
        # Test invalid new version (missing required sections)
        invalid_config = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {"basic": True},
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name"]}
                },
                "v3": {  # Invalid - missing required sections
                    "base_url": "/api/v3",
                    "features": {"advanced": True}
                    # Missing endpoints and schema_fields
                }
            }
        }
        
        invalid_config_path = self.create_test_config(invalid_config)
        
        # Should raise ConfigurationError
        with pytest.raises(ConfigurationError, match="missing required section"):
            VersionConfigManager(invalid_config_path)
        
        # Cleanup
        Path(config_path).unlink()
        Path(invalid_config_path).unlink()
    
    def test_configuration_validation_malformed_sections(self):
        """Test configuration validation with malformed sections."""
        # Test invalid base_url
        invalid_base_url_config = {
            "versions": {
                "v1": {
                    "base_url": "",  # Empty base_url
                    "features": {"basic": True},
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name"]}
                }
            }
        }
        
        config_path = self.create_test_config(invalid_base_url_config)
        with pytest.raises(ConfigurationError, match="base_url must be a non-empty string"):
            VersionConfigManager(config_path)
        Path(config_path).unlink()
        
        # Test invalid features section
        invalid_features_config = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": "not_a_dict",  # Should be dict
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name"]}
                }
            }
        }
        
        config_path = self.create_test_config(invalid_features_config)
        with pytest.raises(ConfigurationError, match="features must be a dictionary"):
            VersionConfigManager(config_path)
        Path(config_path).unlink()
        
        # Test invalid endpoints section
        invalid_endpoints_config = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {"basic": True},
                    "endpoints": [],  # Should be dict
                    "schema_fields": {"pet_create": ["name"]}
                }
            }
        }
        
        config_path = self.create_test_config(invalid_endpoints_config)
        with pytest.raises(ConfigurationError, match="endpoints must be a dictionary"):
            VersionConfigManager(config_path)
        Path(config_path).unlink()
    
    def test_backward_compatibility_maintenance(self):
        """Test that adding new versions maintains backward compatibility."""
        # Original configuration (v1, v2)
        original_config = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {"basic": True},
                    "endpoints": {"pets": "/api/v1/pets", "users": "/api/v1/users"},
                    "schema_fields": {
                        "pet_create": ["name", "species"],
                        "pet_response": ["id", "name", "species", "created_at"]
                    },
                    "required_fields": {"pet_create": ["name", "species"]},
                    "default_values": {"pet_create": {"name": "Buddy", "species": "dog"}}
                },
                "v2": {
                    "base_url": "/api/v2",
                    "features": {"basic": True, "enhanced": True},
                    "endpoints": {"pets": "/api/v2/pets", "users": "/api/v2/users"},
                    "schema_fields": {
                        "pet_create": ["name", "species", "temperament"],
                        "pet_response": ["id", "name", "species", "temperament", "created_at"]
                    },
                    "required_fields": {"pet_create": ["name", "species"]},
                    "default_values": {"pet_create": {"name": "Buddy", "species": "dog", "temperament": "friendly"}}
                }
            }
        }
        
        config_path = self.create_test_config(original_config)
        original_manager = VersionConfigManager(config_path)
        
        # Store original behavior
        original_v1_features = original_manager.get_features_for_version("v1")
        original_v1_endpoints = original_manager.get_version_config("v1")["endpoints"]
        original_v1_fields = original_manager.get_schema_fields("v1", "pet_create")
        
        # Extended configuration (v1, v2, v3)
        extended_config = {
            "versions": {
                "v1": {  # Unchanged
                    "base_url": "/api/v1",
                    "features": {"basic": True},
                    "endpoints": {"pets": "/api/v1/pets", "users": "/api/v1/users"},
                    "schema_fields": {
                        "pet_create": ["name", "species"],
                        "pet_response": ["id", "name", "species", "created_at"]
                    },
                    "required_fields": {"pet_create": ["name", "species"]},
                    "default_values": {"pet_create": {"name": "Buddy", "species": "dog"}}
                },
                "v2": {  # Unchanged
                    "base_url": "/api/v2",
                    "features": {"basic": True, "enhanced": True},
                    "endpoints": {"pets": "/api/v2/pets", "users": "/api/v2/users"},
                    "schema_fields": {
                        "pet_create": ["name", "species", "temperament"],
                        "pet_response": ["id", "name", "species", "temperament", "created_at"]
                    },
                    "required_fields": {"pet_create": ["name", "species"]},
                    "default_values": {"pet_create": {"name": "Buddy", "species": "dog", "temperament": "friendly"}}
                },
                "v3": {  # New version
                    "base_url": "/api/v3",
                    "features": {"basic": True, "enhanced": True, "ai_powered": True},
                    "endpoints": {"pets": "/api/v3/pets", "users": "/api/v3/users", "ai": "/api/v3/ai"},
                    "schema_fields": {
                        "pet_create": ["name", "species", "temperament", "ai_profile"],
                        "pet_response": ["id", "name", "species", "temperament", "ai_profile", "created_at"]
                    },
                    "required_fields": {"pet_create": ["name", "species"]},
                    "default_values": {"pet_create": {"name": "Buddy", "species": "dog", "temperament": "friendly", "ai_profile": {}}}
                }
            }
        }
        
        extended_config_path = self.create_test_config(extended_config)
        extended_manager = VersionConfigManager(extended_config_path)
        
        # Test that v1 behavior is unchanged
        assert extended_manager.get_features_for_version("v1") == original_v1_features
        assert extended_manager.get_version_config("v1")["endpoints"] == original_v1_endpoints
        assert extended_manager.get_schema_fields("v1", "pet_create") == original_v1_fields
        
        # Test that v2 behavior is unchanged
        assert extended_manager.get_feature_availability("v2", "enhanced") is True
        assert extended_manager.get_feature_availability("v2", "ai_powered") is False  # Not in v2
        
        # Test that new v3 features work
        assert extended_manager.get_feature_availability("v3", "ai_powered") is True
        assert "ai" in extended_manager.get_version_config("v3")["endpoints"]
        
        # Test that existing tests would still work with BaseVersionTest
        base_test = BaseVersionTest()
        base_test._config_manager = extended_manager
        
        # v1 tests should still work
        assert base_test.should_test_feature("v1", "basic") is True
        assert base_test.should_test_feature("v1", "enhanced") is False
        assert base_test.should_test_feature("v1", "ai_powered") is False
        
        # v2 tests should still work
        assert base_test.should_test_feature("v2", "basic") is True
        assert base_test.should_test_feature("v2", "enhanced") is True
        assert base_test.should_test_feature("v2", "ai_powered") is False
        
        # New v3 tests should work
        assert base_test.should_test_feature("v3", "ai_powered") is True
        
        # Cleanup
        Path(config_path).unlink()
        Path(extended_config_path).unlink()
    
    def test_data_factory_extensibility(self):
        """Test that TestDataFactory handles new versions gracefully."""
        config_data = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {"basic": True},
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name", "species"]},
                    "required_fields": {"pet_create": ["name"]},
                    "optional_fields": {"pet_create": ["species"]},
                    "default_values": {"pet_create": {"name": "Buddy", "species": "dog"}}
                },
                "v_future": {  # Future version with new fields
                    "base_url": "/api/v_future",
                    "features": {"basic": True, "quantum": True},
                    "endpoints": {"pets": "/api/v_future/pets"},
                    "schema_fields": {"pet_create": ["name", "species", "quantum_state", "dimension"]},
                    "required_fields": {"pet_create": ["name", "quantum_state"]},
                    "optional_fields": {"pet_create": ["species", "dimension"]},
                    "default_values": {"pet_create": {"name": "Schrödinger", "species": "cat", "quantum_state": "superposition", "dimension": "4D"}}
                }
            }
        }
        
        config_path = self.create_test_config(config_data)
        config_manager = VersionConfigManager(config_path)
        
        # Test that TestDataFactory can handle new version
        data_factory = TestDataFactory(config_manager)
        
        # Test v1 data generation (should work as before)
        v1_data = data_factory.build_pet_data("v1", use_template=False)
        assert "name" in v1_data
        assert "species" in v1_data
        assert "quantum_state" not in v1_data
        
        # Test future version data generation
        future_data = data_factory.build_pet_data("v_future", use_template=False)
        assert "name" in future_data
        assert "species" in future_data
        assert "quantum_state" in future_data
        assert "dimension" in future_data
        
        # Test that overrides work with new fields
        custom_future_data = data_factory.build_pet_data("v_future", use_template=False, quantum_state="collapsed", dimension="3D")
        assert custom_future_data["quantum_state"] == "collapsed"
        assert custom_future_data["dimension"] == "3D"
        
        # Cleanup
        Path(config_path).unlink()
    
    def test_error_handling_for_nonexistent_versions(self):
        """Test proper error handling when accessing nonexistent versions."""
        config_data = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {"basic": True},
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name"]}
                }
            }
        }
        
        config_path = self.create_test_config(config_data)
        config_manager = VersionConfigManager(config_path)
        
        # Test ConfigurationError for nonexistent version
        with pytest.raises(ConfigurationError, match="Version 'v999' not found"):
            config_manager.get_version_config("v999")
        
        with pytest.raises(ConfigurationError, match="Version 'v999' not found"):
            config_manager.get_endpoint_url("v999", "pets")
        
        with pytest.raises(ConfigurationError, match="Version 'v999' not found"):
            config_manager.get_schema_fields("v999", "pet_create")
        
        # Test graceful handling in feature availability (should return False)
        assert config_manager.get_feature_availability("v999", "basic") is False
        
        # Test BaseVersionTest error handling
        base_test = BaseVersionTest()
        base_test._config_manager = config_manager
        
        with pytest.raises(ConfigurationError):
            base_test.get_endpoint_url("v999", "pets")
        
        # Feature checking should be graceful
        assert base_test.should_test_feature("v999", "basic") is False
        
        # Cleanup
        Path(config_path).unlink()
    
    def test_configuration_reload_extensibility(self):
        """Test that configuration can be reloaded with new versions."""
        # Initial configuration
        initial_config = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {"basic": True},
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name"]}
                }
            }
        }
        
        config_path = self.create_test_config(initial_config)
        config_manager = VersionConfigManager(config_path)
        
        # Verify initial state
        assert config_manager.get_supported_versions() == ["v1"]
        assert config_manager.get_feature_availability("v1", "basic") is True
        
        # Update configuration file with new version
        updated_config = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {"basic": True},
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name"]}
                },
                "v2": {
                    "base_url": "/api/v2",
                    "features": {"basic": True, "advanced": True},
                    "endpoints": {"pets": "/api/v2/pets"},
                    "schema_fields": {"pet_create": ["name", "advanced_field"]}
                }
            }
        }
        
        # Write updated config to same file
        with open(config_path, 'w') as f:
            yaml.dump(updated_config, f)
        
        # Reload configuration
        config_manager.reload_config()
        
        # Verify updated state
        assert set(config_manager.get_supported_versions()) == {"v1", "v2"}
        assert config_manager.get_feature_availability("v2", "advanced") is True
        assert config_manager.get_schema_fields("v2", "pet_create") == ["name", "advanced_field"]
        
        # Cleanup
        Path(config_path).unlink()


class TestExtensibilityIntegration:
    """Integration tests for extensibility features."""
    
    def setup_method(self):
        """Reset configuration manager before each test."""
        reset_config_manager()
    
    def test_end_to_end_new_version_support(self):
        """Test end-to-end support for adding a completely new version."""
        # Create configuration with v1, v2, and hypothetical v4
        config_data = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {"basic": True},
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name"], "pet_response": ["id", "name"]},
                    "required_fields": {"pet_create": ["name"]},
                    "default_values": {"pet_create": {"name": "Buddy"}}
                },
                "v2": {
                    "base_url": "/api/v2",
                    "features": {"basic": True, "enhanced": True},
                    "endpoints": {"pets": "/api/v2/pets"},
                    "schema_fields": {"pet_create": ["name", "temperament"], "pet_response": ["id", "name", "temperament"]},
                    "required_fields": {"pet_create": ["name"]},
                    "default_values": {"pet_create": {"name": "Buddy", "temperament": "friendly"}}
                },
                "v4": {  # Skip v3, test non-sequential versions
                    "base_url": "/api/v4",
                    "features": {"basic": True, "enhanced": True, "neural": True, "blockchain": True},
                    "endpoints": {"pets": "/api/v4/pets", "neural": "/api/v4/neural", "blockchain": "/api/v4/blockchain"},
                    "schema_fields": {
                        "pet_create": ["name", "temperament", "neural_profile", "blockchain_id"],
                        "pet_response": ["id", "name", "temperament", "neural_profile", "blockchain_id", "smart_contract"]
                    },
                    "required_fields": {"pet_create": ["name", "blockchain_id"]},
                    "default_values": {"pet_create": {"name": "CryptoPet", "temperament": "digital", "neural_profile": {}, "blockchain_id": "0x123"}}
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            # Test that all components work with the new version
            config_manager = VersionConfigManager(config_path)
            base_test = BaseVersionTest()
            base_test._config_manager = config_manager
            data_factory = TestDataFactory(config_manager)
            
            # Test version discovery
            versions = config_manager.get_supported_versions()
            assert "v4" in versions
            assert len(versions) == 3
            
            # Test feature detection
            assert config_manager.get_feature_availability("v4", "neural") is True
            assert config_manager.get_feature_availability("v4", "blockchain") is True
            assert config_manager.get_feature_availability("v1", "neural") is False
            
            # Test endpoint URL generation
            neural_endpoint = config_manager.get_endpoint_url("v4", "neural")
            assert neural_endpoint == "/api/v4/neural"
            
            # Test schema field handling
            v4_create_fields = config_manager.get_schema_fields("v4", "pet_create")
            assert "neural_profile" in v4_create_fields
            assert "blockchain_id" in v4_create_fields
            
            # Test data factory with new version (bypass template system for extensibility test)
            v4_data = data_factory.build_pet_data("v4", use_template=False)
            assert "neural_profile" in v4_data
            assert "blockchain_id" in v4_data
            assert v4_data["blockchain_id"] == "0x123"
            
            # Test BaseVersionTest utilities
            assert base_test.should_test_feature("v4", "neural") is True
            assert base_test.should_test_feature("v4", "nonexistent") is False
            
            v4_endpoint = base_test.get_endpoint_url("v4", "pets", "123")
            assert v4_endpoint == "/api/v4/pets/123"
            
            # Test that older versions still work
            v1_data = data_factory.build_pet_data("v1", use_template=False)
            assert "neural_profile" not in v1_data
            assert "blockchain_id" not in v1_data
            
        finally:
            Path(config_path).unlink()
    
    def test_feature_evolution_compatibility(self):
        """Test that features can evolve across versions while maintaining compatibility."""
        config_data = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {"search": True},  # Basic search
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name"], "pet_response": ["id", "name"]},
                    "default_values": {"pet_create": {"name": "Buddy"}}
                },
                "v2": {
                    "base_url": "/api/v2",
                    "features": {"search": True, "advanced_search": True},  # Enhanced search
                    "endpoints": {"pets": "/api/v2/pets", "search": "/api/v2/search"},
                    "schema_fields": {"pet_create": ["name", "tags"], "pet_response": ["id", "name", "tags"]},
                    "default_values": {"pet_create": {"name": "Buddy", "tags": []}}
                },
                "v3": {
                    "base_url": "/api/v3",
                    "features": {"search": True, "advanced_search": True, "ai_search": True},  # AI-powered search
                    "endpoints": {"pets": "/api/v3/pets", "search": "/api/v3/search", "ai_search": "/api/v3/ai-search"},
                    "schema_fields": {"pet_create": ["name", "tags", "ai_keywords"], "pet_response": ["id", "name", "tags", "ai_keywords", "search_score"]},
                    "default_values": {"pet_create": {"name": "Buddy", "tags": [], "ai_keywords": []}}
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config_manager = VersionConfigManager(config_path)
            
            # Test feature evolution
            # All versions support basic search
            for version in ["v1", "v2", "v3"]:
                assert config_manager.get_feature_availability(version, "search") is True
            
            # Only v2 and v3 support advanced search
            assert config_manager.get_feature_availability("v1", "advanced_search") is False
            assert config_manager.get_feature_availability("v2", "advanced_search") is True
            assert config_manager.get_feature_availability("v3", "advanced_search") is True
            
            # Only v3 supports AI search
            assert config_manager.get_feature_availability("v1", "ai_search") is False
            assert config_manager.get_feature_availability("v2", "ai_search") is False
            assert config_manager.get_feature_availability("v3", "ai_search") is True
            
            # Test that versions supporting features can be queried
            search_versions = config_manager.get_versions_supporting_feature("search")
            assert set(search_versions) == {"v1", "v2", "v3"}
            
            advanced_search_versions = config_manager.get_versions_supporting_feature("advanced_search")
            assert set(advanced_search_versions) == {"v2", "v3"}
            
            ai_search_versions = config_manager.get_versions_supporting_feature("ai_search")
            assert set(ai_search_versions) == {"v3"}
            
        finally:
            Path(config_path).unlink()