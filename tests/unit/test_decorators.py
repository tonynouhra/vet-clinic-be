"""
Unit tests for dynamic testing framework decorators.

Tests the parameterized test decorators and feature detection system
to ensure proper functionality across API versions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from tests.dynamic.decorators import (
    version_parametrize,
    feature_test,
    crud_test,
    skip_versions,
    require_features,
    version_specific,
    smart_feature_test,
    conditional_skip,
    auto_skip_unavailable,
    FeatureDetector,
    get_feature_detector,
    reset_feature_detector,
    get_versions_supporting_features,
    get_versions_with_resource,
    validate_decorator_config,
    check_feature_compatibility,
    get_feature_evolution_path
)
from tests.dynamic.config_manager import ConfigurationError


class TestVersionParametrize:
    """Test version_parametrize decorator functionality."""
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_version_parametrize_all_versions(self, mock_get_config):
        """Test version_parametrize with all configured versions."""
        mock_config = Mock()
        mock_config.get_supported_versions.return_value = ["v1", "v2", "v3"]
        mock_get_config.return_value = mock_config
        
        @version_parametrize()
        def test_function(api_version):
            return api_version
        
        # Check that pytest.mark.parametrize was applied
        assert hasattr(test_function, 'pytestmark')
        mark = test_function.pytestmark[0]
        assert mark.name == 'parametrize'
        assert mark.args[0] == 'api_version'
        assert mark.args[1] == ["v1", "v2", "v3"]
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_version_parametrize_specific_versions(self, mock_get_config):
        """Test version_parametrize with specific versions."""
        mock_config = Mock()
        mock_config.get_supported_versions.return_value = ["v1", "v2", "v3"]
        mock_get_config.return_value = mock_config
        
        @version_parametrize(versions=["v1", "v2"])
        def test_function(api_version):
            return api_version
        
        mark = test_function.pytestmark[0]
        assert mark.args[1] == ["v1", "v2"]
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_version_parametrize_skip_unsupported(self, mock_get_config):
        """Test version_parametrize skips unsupported versions."""
        mock_config = Mock()
        mock_config.get_supported_versions.return_value = ["v1", "v2"]
        mock_get_config.return_value = mock_config
        
        @version_parametrize(versions=["v1", "v2", "v3"], skip_unsupported=True)
        def test_function(api_version):
            return api_version
        
        mark = test_function.pytestmark[0]
        assert mark.args[1] == ["v1", "v2"]  # v3 should be filtered out


class TestFeatureTest:
    """Test feature_test decorator functionality."""
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_feature_test_supporting_versions(self, mock_get_config):
        """Test feature_test only includes supporting versions."""
        mock_config = Mock()
        mock_config.get_supported_versions.return_value = ["v1", "v2", "v3"]
        mock_config.get_feature_availability.side_effect = lambda v, f: v in ["v2", "v3"]
        mock_get_config.return_value = mock_config
        
        @feature_test("health_records")
        def test_function(api_version):
            return api_version
        
        mark = test_function.pytestmark[0]
        assert mark.args[1] == ["v2", "v3"]
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_feature_test_no_supporting_versions(self, mock_get_config):
        """Test feature_test creates skip wrapper when no versions support feature."""
        mock_config = Mock()
        mock_config.get_supported_versions.return_value = ["v1", "v2"]
        mock_config.get_feature_availability.return_value = False
        mock_get_config.return_value = mock_config
        
        @feature_test("nonexistent_feature")
        def test_function(api_version):
            return api_version
        
        # Should create a skip wrapper function
        with pytest.raises(pytest.skip.Exception):
            test_function("v1")
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_feature_test_runtime_check(self, mock_get_config):
        """Test feature_test performs runtime feature availability check."""
        mock_config = Mock()
        mock_config.get_supported_versions.return_value = ["v1", "v2"]
        mock_config.get_feature_availability.side_effect = lambda v, f: v == "v2"
        mock_get_config.return_value = mock_config
        
        @feature_test("health_records")
        def test_function(api_version):
            return f"tested_{api_version}"
        
        # Should skip for v1 (feature not available)
        with pytest.raises(pytest.skip.Exception):
            test_function("v1")


class TestCrudTest:
    """Test crud_test decorator functionality."""
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_crud_test_all_operations(self, mock_get_config):
        """Test crud_test with all CRUD operations."""
        mock_config = Mock()
        mock_config.get_supported_versions.return_value = ["v1", "v2"]
        mock_config.get_endpoint_url.return_value = "/api/v1/pets"
        mock_get_config.return_value = mock_config
        
        @crud_test("pets")
        def test_function(api_version, crud_operation):
            return f"{api_version}_{crud_operation}"
        
        mark = test_function.pytestmark[0]
        expected_params = [
            ("v1", "create"), ("v1", "read"), ("v1", "update"), ("v1", "delete"), ("v1", "list"),
            ("v2", "create"), ("v2", "read"), ("v2", "update"), ("v2", "delete"), ("v2", "list")
        ]
        assert mark.args[1] == expected_params
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_crud_test_specific_operations(self, mock_get_config):
        """Test crud_test with specific operations."""
        mock_config = Mock()
        mock_config.get_supported_versions.return_value = ["v1", "v2"]
        mock_config.get_endpoint_url.return_value = "/api/v1/users"
        mock_get_config.return_value = mock_config
        
        @crud_test("users", operations=["create", "read"])
        def test_function(api_version, crud_operation):
            return f"{api_version}_{crud_operation}"
        
        mark = test_function.pytestmark[0]
        expected_params = [("v1", "create"), ("v1", "read"), ("v2", "create"), ("v2", "read")]
        assert mark.args[1] == expected_params
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_crud_test_filters_invalid_versions(self, mock_get_config):
        """Test crud_test filters out versions without the resource."""
        mock_config = Mock()
        mock_config.get_supported_versions.return_value = ["v1", "v2"]
        
        def mock_get_endpoint_url(version, resource):
            if version == "v2":
                return "/api/v2/pets"
            else:
                raise ConfigurationError("Not found")
        
        mock_config.get_endpoint_url.side_effect = mock_get_endpoint_url
        mock_get_config.return_value = mock_config
        
        @crud_test("pets")
        def test_function(api_version, crud_operation):
            return f"{api_version}_{crud_operation}"
        
        mark = test_function.pytestmark[0]
        # Should only include v2 parameters
        v2_params = [("v2", op) for op in ["create", "read", "update", "delete", "list"]]
        assert mark.args[1] == v2_params


class TestFeatureDetector:
    """Test FeatureDetector class functionality."""
    
    def setup_method(self):
        """Reset feature detector before each test."""
        reset_feature_detector()
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_is_feature_available(self, mock_get_config):
        """Test feature availability checking."""
        mock_config = Mock()
        mock_config.get_feature_availability.return_value = True
        mock_get_config.return_value = mock_config
        
        detector = FeatureDetector()
        assert detector.is_feature_available("v2", "health_records") is True
        
        # Test caching
        assert detector.is_feature_available("v2", "health_records") is True
        mock_config.get_feature_availability.assert_called_once()
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_get_missing_features(self, mock_get_config):
        """Test missing features detection."""
        mock_config = Mock()
        mock_config.get_feature_availability.side_effect = lambda v, f: f in ["feature1", "feature3"]
        mock_get_config.return_value = mock_config
        
        detector = FeatureDetector()
        missing = detector.get_missing_features("v1", ["feature1", "feature2", "feature3"])
        assert missing == ["feature2"]
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_should_skip_test(self, mock_get_config):
        """Test test skipping logic."""
        mock_config = Mock()
        mock_config.get_feature_availability.side_effect = lambda v, f: f == "available_feature"
        mock_config.get_supported_versions.return_value = ["v1", "v2"]
        mock_get_config.return_value = mock_config
        
        detector = FeatureDetector()
        
        # Should not skip when all features available
        should_skip, reason = detector.should_skip_test("v1", ["available_feature"])
        assert should_skip is False
        assert reason == ""
        
        # Should skip when required feature missing
        should_skip, reason = detector.should_skip_test("v1", ["missing_feature"])
        assert should_skip is True
        assert "missing_feature" in reason
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_validate_feature_dependencies(self, mock_get_config):
        """Test feature dependency validation."""
        mock_config = Mock()
        mock_config.get_feature_availability.side_effect = lambda v, f: f in ["dep1", "dep3"]
        mock_get_config.return_value = mock_config
        
        detector = FeatureDetector()
        dependencies = {"feature1": ["dep1", "dep2", "dep3"]}
        
        result = detector.validate_feature_dependencies("v1", "feature1", dependencies)
        
        assert result['valid'] is False
        assert result['missing_dependencies'] == ["dep2"]
        assert result['available_dependencies'] == ["dep1", "dep3"]
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_generate_skip_message(self, mock_get_config):
        """Test skip message generation."""
        mock_config = Mock()
        mock_config.get_versions_supporting_feature.return_value = ["v2", "v3"]
        mock_get_config.return_value = mock_config
        
        detector = FeatureDetector()
        message = detector.generate_skip_message("v1", "health_records")
        
        assert "health_records" in message
        assert "v1" in message
        assert "v2, v3" in message


class TestSmartFeatureTest:
    """Test smart_feature_test decorator functionality."""
    
    @patch('tests.dynamic.decorators.get_feature_detector')
    def test_smart_feature_test_single_feature(self, mock_get_detector):
        """Test smart_feature_test with single feature."""
        mock_detector = Mock()
        mock_detector.config_manager.get_supported_versions.return_value = ["v1", "v2"]
        mock_detector.should_skip_test.side_effect = lambda v, f, o: (v == "v1", "Skip v1")
        mock_get_detector.return_value = mock_detector
        
        @smart_feature_test("health_records")
        def test_function(api_version):
            return api_version
        
        mark = test_function.pytestmark[0]
        assert mark.args[1] == ["v2"]  # Only v2 should be included
    
    @patch('tests.dynamic.decorators.get_feature_detector')
    def test_smart_feature_test_with_dependencies(self, mock_get_detector):
        """Test smart_feature_test with feature dependencies."""
        mock_detector = Mock()
        mock_detector.config_manager.get_supported_versions.return_value = ["v1", "v2"]
        mock_detector.should_skip_test.return_value = (False, "")
        mock_detector.validate_feature_dependencies.side_effect = lambda v, f, d: {"valid": v == "v2"}
        mock_get_detector.return_value = mock_detector
        
        dependencies = {"health_records": ["enhanced_filtering"]}
        
        @smart_feature_test("health_records", dependencies=dependencies)
        def test_function(api_version):
            return api_version
        
        mark = test_function.pytestmark[0]
        assert mark.args[1] == ["v2"]  # Only v2 should pass dependency validation


class TestUtilityFunctions:
    """Test utility functions for decorator configuration."""
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_get_versions_supporting_features(self, mock_get_config):
        """Test getting versions that support all specified features."""
        mock_config = Mock()
        mock_config.get_supported_versions.return_value = ["v1", "v2", "v3"]
        mock_config.get_feature_availability.side_effect = lambda v, f: {
            ("v1", "feature1"): True, ("v1", "feature2"): False,
            ("v2", "feature1"): True, ("v2", "feature2"): True,
            ("v3", "feature1"): False, ("v3", "feature2"): True
        }.get((v, f), False)
        mock_get_config.return_value = mock_config
        
        supporting = get_versions_supporting_features(["feature1", "feature2"])
        assert supporting == ["v2"]  # Only v2 supports both features
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_get_versions_with_resource(self, mock_get_config):
        """Test getting versions that have a specific resource."""
        mock_config = Mock()
        mock_config.get_supported_versions.return_value = ["v1", "v2", "v3"]
        
        def mock_get_endpoint_url(version, resource):
            if version == "v1" and resource == "pets":
                return "/api/v1/pets"
            elif version == "v2" and resource == "pets":
                return "/api/v2/pets"
            else:
                raise ConfigurationError("Not found")
        
        mock_config.get_endpoint_url.side_effect = mock_get_endpoint_url
        mock_get_config.return_value = mock_config
        
        versions = get_versions_with_resource("pets")
        assert versions == ["v1", "v2"]  # v3 should be excluded
    
    @patch('tests.dynamic.decorators.get_config_manager')
    def test_validate_decorator_config(self, mock_get_config):
        """Test decorator configuration validation."""
        mock_config = Mock()
        mock_config.get_supported_versions.return_value = ["v1", "v2"]
        mock_config.get_features_for_version.return_value = {"feature1": True, "feature2": False}
        mock_get_config.return_value = mock_config
        
        result = validate_decorator_config(
            versions=["v1", "v3"],  # v3 is invalid
            features=["feature1", "feature3"],  # feature3 doesn't exist
            resources=["pets"]
        )
        
        assert result['valid'] is False
        assert any("Invalid versions" in error for error in result['errors'])
        assert any("Features not found" in warning for warning in result['warnings'])
    
    @patch('tests.dynamic.decorators.get_feature_detector')
    def test_check_feature_compatibility(self, mock_get_detector):
        """Test feature compatibility checking between versions."""
        mock_detector = Mock()
        mock_detector.is_feature_available.side_effect = lambda v, f: {
            ("v1", "feature1"): True, ("v1", "feature2"): False, ("v1", "feature3"): False,
            ("v2", "feature1"): True, ("v2", "feature2"): True, ("v2", "feature3"): False
        }.get((v, f), False)
        mock_get_detector.return_value = mock_detector
        
        result = check_feature_compatibility("v1", "v2", ["feature1", "feature2", "feature3"])
        
        assert result['compatible'] is False
        assert result['common_features'] == ["feature1"]
        assert result['version1_only'] == []
        assert result['version2_only'] == ["feature2"]
        assert result['incompatible_features'] == ["feature3"]
    
    @patch('tests.dynamic.decorators.get_feature_detector')
    def test_get_feature_evolution_path(self, mock_get_detector):
        """Test feature evolution path tracking."""
        mock_detector = Mock()
        mock_detector.config_manager.get_supported_versions.return_value = ["v1", "v2", "v3"]
        mock_detector.is_feature_available.side_effect = lambda v, f: v in ["v2", "v3"]
        mock_get_detector.return_value = mock_detector
        
        evolution = get_feature_evolution_path("health_records")
        assert evolution == ["v2", "v3"]


class TestConditionalDecorators:
    """Test conditional and auto-skip decorators."""
    
    def test_conditional_skip(self):
        """Test conditional_skip decorator."""
        def condition_func(version):
            return version != "v1"  # Skip v1
        
        @conditional_skip(condition_func, "Version not supported")
        def test_function(api_version):
            return f"tested_{api_version}"
        
        # Should skip for v1
        with pytest.raises(pytest.skip.Exception):
            test_function("v1")
        
        # Should run for v2
        result = test_function("v2")
        assert result == "tested_v2"
    
    @patch('tests.dynamic.decorators.get_feature_detector')
    def test_auto_skip_unavailable(self, mock_get_detector):
        """Test auto_skip_unavailable decorator."""
        mock_detector = Mock()
        mock_detector.get_missing_features.side_effect = lambda v, f: ["feature2"] if v == "v1" else []
        mock_get_detector.return_value = mock_detector
        
        @auto_skip_unavailable(["feature1", "feature2"])
        def test_function(api_version):
            return f"tested_{api_version}"
        
        # Should skip for v1 (missing feature2)
        with pytest.raises(pytest.skip.Exception):
            test_function("v1")
        
        # Should run for v2 (all features available)
        result = test_function("v2")
        assert result == "tested_v2"


if __name__ == "__main__":
    pytest.main([__file__])