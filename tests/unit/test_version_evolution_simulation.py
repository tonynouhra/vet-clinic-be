"""
Tests for version evolution simulation.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from typing import Dict, Any

from tests.dynamic.config_manager import VersionConfigManager, reset_config_manager


class TestVersionEvolutionSimulation:
    """Test version evolution and migration scenarios."""
    
    def setup_method(self):
        """Reset configuration manager before each test."""
        reset_config_manager()
    
    def test_mock_v3_configuration_creation(self):
        """Test creating a mock v3 configuration for extensibility testing."""
        # Simple test to verify v3 configuration works
        v3_config = {
            "versions": {
                "v1": {
                    "base_url": "/api/v1",
                    "features": {"basic": True},
                    "endpoints": {"pets": "/api/v1/pets"},
                    "schema_fields": {"pet_create": ["name"]}
                },
                "v3": {
                    "base_url": "/api/v3",
                    "features": {"basic": True, "ai": True},
                    "endpoints": {"pets": "/api/v3/pets", "ai": "/api/v3/ai"},
                    "schema_fields": {"pet_create": ["name", "ai_profile"]}
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(v3_config, f)
            config_path = f.name
        
        try:
            config_manager = VersionConfigManager(config_path)
            versions = config_manager.get_supported_versions()
            assert "v3" in versions
            assert config_manager.get_feature_availability("v3", "ai") is True
        finally:
            Path(config_path).unlink()
