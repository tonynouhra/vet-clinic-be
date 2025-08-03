"""
Parameterized test decorators for dynamic API testing framework.

Provides decorators for automatic version testing, feature-specific tests,
and CRUD operation testing across multiple API versions.
"""

import functools
import pytest
from typing import List, Optional, Callable, Any, Dict, Union
from tests.dynamic.config_manager import get_config_manager, ConfigurationError


def version_parametrize(versions: Optional[List[str]] = None, 
                       skip_unsupported: bool = True) -> Callable:
    """
    Decorator to parametrize tests across API versions.
    
    Args:
        versions: List of versions to test. If None, uses all configured versions.
        skip_unsupported: If True, skip tests for versions that don't exist in config.
        
    Returns:
        Decorator function that parametrizes the test across versions.
        
    Example:
        @version_parametrize()
        def test_get_pets(api_version):
            # Test will run for all configured versions
            pass
            
        @version_parametrize(versions=["v1", "v2"])
        def test_specific_versions(api_version):
            # Test will run only for v1 and v2
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        config_manager = get_config_manager()
        
        # Determine which versions to test
        if versions is None:
            test_versions = config_manager.get_supported_versions()
        else:
            test_versions = versions.copy()
        
        # Filter out unsupported versions if requested
        if skip_unsupported:
            supported_versions = config_manager.get_supported_versions()
            test_versions = [v for v in test_versions if v in supported_versions]
        
        # Apply pytest parametrize decorator
        return pytest.mark.parametrize("api_version", test_versions)(test_func)
    
    return decorator


def feature_test(feature: str, versions: Optional[List[str]] = None,
                skip_message: Optional[str] = None) -> Callable:
    """
    Decorator for feature-specific tests that only run on versions supporting the feature.
    
    Args:
        feature: Feature name to check for availability.
        versions: List of versions to consider. If None, checks all configured versions.
        skip_message: Custom skip message. If None, generates default message.
        
    Returns:
        Decorator function that parametrizes the test across supporting versions.
        
    Example:
        @feature_test("health_records")
        def test_health_records(api_version):
            # Test will only run on versions that support health_records
            pass
            
        @feature_test("statistics", versions=["v2", "v3"])
        def test_statistics_specific_versions(api_version):
            # Test will only run on v2/v3 if they support statistics
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        config_manager = get_config_manager()
        
        # Determine which versions to consider
        if versions is None:
            candidate_versions = config_manager.get_supported_versions()
        else:
            candidate_versions = versions
        
        # Find versions that support the feature
        supporting_versions = []
        for version in candidate_versions:
            if config_manager.get_feature_availability(version, feature):
                supporting_versions.append(version)
        
        # Generate skip message if not provided
        if skip_message is None:
            skip_msg = f"Feature '{feature}' not supported in version"
        else:
            skip_msg = skip_message
        
        # If no versions support the feature, create a test that always skips
        if not supporting_versions:
            @functools.wraps(test_func)
            def skip_wrapper(*args, **kwargs):
                pytest.skip(f"Feature '{feature}' not supported in any configured version")
            return skip_wrapper
        
        # Create parametrized test with feature checking
        @pytest.mark.parametrize("api_version", supporting_versions)
        @functools.wraps(test_func)
        def feature_wrapper(api_version, *args, **kwargs):
            # Double-check feature availability (in case config changed)
            if not config_manager.get_feature_availability(api_version, feature):
                pytest.skip(f"{skip_msg} {api_version}")
            
            return test_func(api_version, *args, **kwargs)
        
        return feature_wrapper
    
    return decorator


def crud_test(resource: str, versions: Optional[List[str]] = None,
              operations: Optional[List[str]] = None) -> Callable:
    """
    Decorator for CRUD operation tests across versions.
    
    Args:
        resource: Resource type (e.g., 'pets', 'users', 'appointments').
        versions: List of versions to test. If None, uses all configured versions.
        operations: List of CRUD operations to test. If None, tests all operations.
        
    Returns:
        Decorator function that parametrizes the test across versions and operations.
        
    Example:
        @crud_test("pets")
        def test_pet_crud(api_version, crud_operation):
            # Test will run for all versions and all CRUD operations
            pass
            
        @crud_test("users", operations=["create", "read"])
        def test_user_create_read(api_version, crud_operation):
            # Test will run for create and read operations only
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        config_manager = get_config_manager()
        
        # Determine which versions to test
        if versions is None:
            test_versions = config_manager.get_supported_versions()
        else:
            test_versions = versions
        
        # Determine which operations to test
        if operations is None:
            test_operations = ["create", "read", "update", "delete", "list"]
        else:
            test_operations = operations
        
        # Filter versions that have the resource endpoint
        valid_versions = []
        for version in test_versions:
            try:
                config_manager.get_endpoint_url(version, resource)
                valid_versions.append(version)
            except (ConfigurationError, Exception):
                # Skip versions that don't have this resource
                continue
        
        # Create parameter combinations
        test_params = []
        for version in valid_versions:
            for operation in test_operations:
                test_params.append((version, operation))
        
        # Apply parametrization
        @pytest.mark.parametrize("api_version,crud_operation", test_params)
        @functools.wraps(test_func)
        def crud_wrapper(api_version, crud_operation, *args, **kwargs):
            return test_func(api_version, crud_operation, *args, **kwargs)
        
        return crud_wrapper
    
    return decorator


def skip_versions(versions: List[str], reason: str = "Version not supported") -> Callable:
    """
    Decorator to skip tests for specific versions.
    
    Args:
        versions: List of versions to skip.
        reason: Reason for skipping the versions.
        
    Returns:
        Decorator function that skips tests for specified versions.
        
    Example:
        @version_parametrize()
        @skip_versions(["v1"], "Feature not available in v1")
        def test_advanced_feature(api_version):
            # Test will run for all versions except v1
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        @functools.wraps(test_func)
        def skip_wrapper(*args, **kwargs):
            # Check if api_version is in the arguments
            api_version = None
            
            # Try to find api_version in kwargs first
            if 'api_version' in kwargs:
                api_version = kwargs['api_version']
            else:
                # Try to find it in args (assuming it's the first argument)
                if args and isinstance(args[0], str):
                    api_version = args[0]
            
            if api_version in versions:
                pytest.skip(f"{reason}: {api_version}")
            
            return test_func(*args, **kwargs)
        
        return skip_wrapper
    
    return decorator


def require_features(features: List[str], 
                    skip_message: Optional[str] = None) -> Callable:
    """
    Decorator to require multiple features for a test.
    
    Args:
        features: List of feature names that must all be supported.
        skip_message: Custom skip message. If None, generates default message.
        
    Returns:
        Decorator function that skips tests if any required feature is missing.
        
    Example:
        @version_parametrize()
        @require_features(["health_records", "statistics"])
        def test_health_statistics(api_version):
            # Test will only run on versions supporting both features
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        @functools.wraps(test_func)
        def feature_wrapper(*args, **kwargs):
            config_manager = get_config_manager()
            
            # Find api_version in arguments
            api_version = None
            if 'api_version' in kwargs:
                api_version = kwargs['api_version']
            elif args and isinstance(args[0], str):
                api_version = args[0]
            
            if api_version is None:
                pytest.fail("Could not determine API version for feature requirement check")
            
            # Check all required features
            missing_features = []
            for feature in features:
                if not config_manager.get_feature_availability(api_version, feature):
                    missing_features.append(feature)
            
            if missing_features:
                if skip_message is None:
                    skip_msg = f"Required features not available in {api_version}: {missing_features}"
                else:
                    skip_msg = f"{skip_message}: {missing_features}"
                pytest.skip(skip_msg)
            
            return test_func(*args, **kwargs)
        
        return feature_wrapper
    
    return decorator


def version_specific(version_configs: Dict[str, Dict[str, Any]]) -> Callable:
    """
    Decorator to apply version-specific configurations to tests.
    
    Args:
        version_configs: Dictionary mapping version names to configuration dictionaries.
                        Each config can contain 'skip', 'skip_reason', 'marks', etc.
        
    Returns:
        Decorator function that applies version-specific behavior.
        
    Example:
        @version_parametrize()
        @version_specific({
            "v1": {"skip": True, "skip_reason": "Not implemented in v1"},
            "v2": {"marks": [pytest.mark.slow]}
        })
        def test_complex_feature(api_version):
            # Test will be skipped for v1 and marked as slow for v2
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        @functools.wraps(test_func)
        def config_wrapper(*args, **kwargs):
            # Find api_version in arguments
            api_version = None
            if 'api_version' in kwargs:
                api_version = kwargs['api_version']
            elif args and isinstance(args[0], str):
                api_version = args[0]
            
            if api_version is None:
                return test_func(*args, **kwargs)
            
            # Apply version-specific configuration
            if api_version in version_configs:
                config = version_configs[api_version]
                
                # Handle skip configuration
                if config.get('skip', False):
                    skip_reason = config.get('skip_reason', f'Skipped for version {api_version}')
                    pytest.skip(skip_reason)
                
                # Handle pytest marks (applied at runtime)
                marks = config.get('marks', [])
                for mark in marks:
                    pytest.mark.apply(mark)
            
            return test_func(*args, **kwargs)
        
        return config_wrapper
    
    return decorator


# Utility functions for decorator configuration

def get_versions_supporting_features(features: List[str]) -> List[str]:
    """
    Get list of versions that support all specified features.
    
    Args:
        features: List of feature names.
        
    Returns:
        List of version identifiers that support all features.
    """
    config_manager = get_config_manager()
    all_versions = config_manager.get_supported_versions()
    
    supporting_versions = []
    for version in all_versions:
        if all(config_manager.get_feature_availability(version, feature) for feature in features):
            supporting_versions.append(version)
    
    return supporting_versions


def get_versions_with_resource(resource: str) -> List[str]:
    """
    Get list of versions that have the specified resource endpoint.
    
    Args:
        resource: Resource name (e.g., 'pets', 'users').
        
    Returns:
        List of version identifiers that have the resource.
    """
    config_manager = get_config_manager()
    all_versions = config_manager.get_supported_versions()
    
    versions_with_resource = []
    for version in all_versions:
        try:
            result = config_manager.get_endpoint_url(version, resource)
            # If we get a result and it's not an exception, add the version
            if isinstance(result, str):
                versions_with_resource.append(version)
        except (ConfigurationError, Exception):
            continue
    
    return versions_with_resource


def validate_decorator_config(versions: Optional[List[str]] = None,
                            features: Optional[List[str]] = None,
                            resources: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Validate decorator configuration and return validation results.
    
    Args:
        versions: List of versions to validate.
        features: List of features to validate.
        resources: List of resources to validate.
        
    Returns:
        Dictionary containing validation results and recommendations.
    """
    config_manager = get_config_manager()
    results = {
        'valid': True,
        'warnings': [],
        'errors': [],
        'recommendations': []
    }
    
    # Validate versions
    if versions:
        supported_versions = config_manager.get_supported_versions()
        invalid_versions = [v for v in versions if v not in supported_versions]
        if invalid_versions:
            results['errors'].append(f"Invalid versions: {invalid_versions}")
            results['valid'] = False
    
    # Validate features
    if features:
        all_features = set()
        for version in config_manager.get_supported_versions():
            version_features = config_manager.get_features_for_version(version)
            all_features.update(version_features.keys())
        
        invalid_features = [f for f in features if f not in all_features]
        if invalid_features:
            results['warnings'].append(f"Features not found in any version: {invalid_features}")
    
    # Validate resources
    if resources:
        for resource in resources:
            versions_with_resource = get_versions_with_resource(resource)
            if not versions_with_resource:
                results['errors'].append(f"Resource '{resource}' not found in any version")
                results['valid'] = False
    
    return results


# Feature Detection and Skipping System

class FeatureDetector:
    """
    Advanced feature detection and skipping system for dynamic API testing.
    
    Provides intelligent feature availability checking, automatic test skipping,
    and feature dependency validation across API versions.
    """
    
    def __init__(self):
        """Initialize the feature detector with configuration manager."""
        self.config_manager = get_config_manager()
        self._feature_cache = {}
        self._dependency_cache = {}
    
    def is_feature_available(self, version: str, feature: str) -> bool:
        """
        Check if a feature is available in the specified version.
        
        Args:
            version: API version identifier.
            feature: Feature name to check.
            
        Returns:
            True if feature is available, False otherwise.
        """
        cache_key = f"{version}:{feature}"
        if cache_key not in self._feature_cache:
            self._feature_cache[cache_key] = self.config_manager.get_feature_availability(version, feature)
        
        return self._feature_cache[cache_key]
    
    def get_feature_versions(self, feature: str) -> List[str]:
        """
        Get all versions that support a specific feature.
        
        Args:
            feature: Feature name.
            
        Returns:
            List of version identifiers supporting the feature.
        """
        try:
            return self.config_manager.get_versions_supporting_feature(feature)
        except AttributeError:
            # Fallback implementation if method doesn't exist
            supporting_versions = []
            for version in self.config_manager.get_supported_versions():
                if self.is_feature_available(version, feature):
                    supporting_versions.append(version)
            return supporting_versions
    
    def get_missing_features(self, version: str, required_features: List[str]) -> List[str]:
        """
        Get list of features that are required but not available in the version.
        
        Args:
            version: API version identifier.
            required_features: List of required feature names.
            
        Returns:
            List of missing feature names.
        """
        missing = []
        for feature in required_features:
            if not self.is_feature_available(version, feature):
                missing.append(feature)
        return missing
    
    def validate_feature_dependencies(self, version: str, feature: str, 
                                    dependencies: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Validate feature dependencies for a specific version.
        
        Args:
            version: API version identifier.
            feature: Primary feature name.
            dependencies: Dictionary mapping features to their required dependencies.
            
        Returns:
            Dictionary containing validation results.
        """
        cache_key = f"{version}:{feature}:deps"
        if cache_key in self._dependency_cache:
            return self._dependency_cache[cache_key]
        
        result = {
            'valid': True,
            'missing_dependencies': [],
            'available_dependencies': [],
            'warnings': []
        }
        
        if feature in dependencies:
            required_deps = dependencies[feature]
            for dep in required_deps:
                if self.is_feature_available(version, dep):
                    result['available_dependencies'].append(dep)
                else:
                    result['missing_dependencies'].append(dep)
                    result['valid'] = False
        
        # Check for circular dependencies
        if feature in dependencies.get(feature, []):
            result['warnings'].append(f"Circular dependency detected for feature '{feature}'")
        
        self._dependency_cache[cache_key] = result
        return result
    
    def generate_skip_message(self, version: str, feature: str, 
                            context: Optional[str] = None) -> str:
        """
        Generate a descriptive skip message for unavailable features.
        
        Args:
            version: API version identifier.
            feature: Feature name that's unavailable.
            context: Additional context for the skip message.
            
        Returns:
            Formatted skip message string.
        """
        try:
            supporting_versions = self.get_feature_versions(feature)
            # Ensure supporting_versions is a list
            if not isinstance(supporting_versions, list):
                supporting_versions = []
        except Exception:
            supporting_versions = []
        
        base_message = f"Feature '{feature}' not available in {version}"
        
        if supporting_versions:
            base_message += f". Available in: {', '.join(supporting_versions)}"
        else:
            base_message += ". Not available in any configured version"
        
        if context:
            base_message = f"{context}: {base_message}"
        
        return base_message
    
    def should_skip_test(self, version: str, required_features: List[str],
                        optional_features: Optional[List[str]] = None) -> tuple[bool, str]:
        """
        Determine if a test should be skipped based on feature requirements.
        
        Args:
            version: API version identifier.
            required_features: List of features that must be available.
            optional_features: List of features that are nice to have but not required.
            
        Returns:
            Tuple of (should_skip: bool, skip_reason: str).
        """
        missing_required = self.get_missing_features(version, required_features)
        
        if missing_required:
            skip_reason = self.generate_skip_message(
                version, 
                missing_required[0] if len(missing_required) == 1 else f"{len(missing_required)} features",
                f"Missing required features: {missing_required}"
            )
            return True, skip_reason
        
        # Check optional features for warnings (but don't skip)
        if optional_features:
            missing_optional = self.get_missing_features(version, optional_features)
            if missing_optional:
                # Log warning but don't skip
                print(f"Warning: Optional features not available in {version}: {missing_optional}")
        
        return False, ""
    
    def clear_cache(self) -> None:
        """Clear internal caches (useful for testing or config reloads)."""
        self._feature_cache.clear()
        self._dependency_cache.clear()


# Global feature detector instance
_feature_detector: Optional[FeatureDetector] = None


def get_feature_detector() -> FeatureDetector:
    """Get the global feature detector instance."""
    global _feature_detector
    if _feature_detector is None:
        _feature_detector = FeatureDetector()
    return _feature_detector


def reset_feature_detector() -> None:
    """Reset the global feature detector (useful for testing)."""
    global _feature_detector
    _feature_detector = None


# Enhanced decorators using the feature detection system

def smart_feature_test(features: Union[str, List[str]], 
                      optional_features: Optional[List[str]] = None,
                      dependencies: Optional[Dict[str, List[str]]] = None,
                      custom_skip_message: Optional[str] = None) -> Callable:
    """
    Enhanced feature test decorator with dependency validation and smart skipping.
    
    Args:
        features: Single feature name or list of required features.
        optional_features: List of optional features (warnings only).
        dependencies: Dictionary mapping features to their dependencies.
        custom_skip_message: Custom skip message template.
        
    Returns:
        Decorator function with enhanced feature detection.
        
    Example:
        @smart_feature_test("health_records", 
                           optional_features=["statistics"],
                           dependencies={"health_records": ["enhanced_filtering"]})
        def test_health_records_with_stats(api_version):
            # Test requires health_records and enhanced_filtering
            # Will warn if statistics not available but won't skip
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        detector = get_feature_detector()
        
        # Normalize features to list
        required_features = [features] if isinstance(features, str) else features
        
        # Find versions that support all required features
        supporting_versions = []
        all_versions = detector.config_manager.get_supported_versions()
        
        for version in all_versions:
            should_skip, _ = detector.should_skip_test(version, required_features, optional_features)
            
            if not should_skip:
                # Additional dependency validation if provided
                if dependencies:
                    all_deps_valid = True
                    for feature in required_features:
                        if feature in dependencies:
                            dep_result = detector.validate_feature_dependencies(version, feature, dependencies)
                            if not dep_result['valid']:
                                all_deps_valid = False
                                break
                    
                    if all_deps_valid:
                        supporting_versions.append(version)
                else:
                    supporting_versions.append(version)
        
        # If no versions support the features, create a test that always skips
        if not supporting_versions:
            @functools.wraps(test_func)
            def skip_wrapper(*args, **kwargs):
                skip_msg = custom_skip_message or f"Required features not supported: {required_features}"
                pytest.skip(skip_msg)
            return skip_wrapper
        
        # Create parametrized test with enhanced feature checking
        @pytest.mark.parametrize("api_version", supporting_versions)
        @functools.wraps(test_func)
        def enhanced_wrapper(api_version, *args, **kwargs):
            # Runtime feature validation
            should_skip, skip_reason = detector.should_skip_test(api_version, required_features, optional_features)
            if should_skip:
                pytest.skip(custom_skip_message or skip_reason)
            
            # Validate dependencies if provided
            if dependencies:
                for feature in required_features:
                    if feature in dependencies:
                        dep_result = detector.validate_feature_dependencies(api_version, feature, dependencies)
                        if not dep_result['valid']:
                            skip_msg = (f"Feature dependencies not met for '{feature}' in {api_version}: "
                                      f"missing {dep_result['missing_dependencies']}")
                            pytest.skip(custom_skip_message or skip_msg)
            
            return test_func(api_version, *args, **kwargs)
        
        return enhanced_wrapper
    
    return decorator


def conditional_skip(condition_func: Callable[[str], bool], 
                    skip_message: str = "Condition not met") -> Callable:
    """
    Decorator to conditionally skip tests based on a custom condition function.
    
    Args:
        condition_func: Function that takes api_version and returns True if test should run.
        skip_message: Message to display when skipping.
        
    Returns:
        Decorator function that applies conditional skipping.
        
    Example:
        def has_advanced_features(version):
            detector = get_feature_detector()
            return detector.is_feature_available(version, "statistics") and \
                   detector.is_feature_available(version, "batch_operations")
        
        @version_parametrize()
        @conditional_skip(has_advanced_features, "Advanced features required")
        def test_advanced_functionality(api_version):
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        @functools.wraps(test_func)
        def conditional_wrapper(*args, **kwargs):
            # Find api_version in arguments
            api_version = None
            if 'api_version' in kwargs:
                api_version = kwargs['api_version']
            elif args and isinstance(args[0], str):
                api_version = args[0]
            
            if api_version and not condition_func(api_version):
                pytest.skip(f"{skip_message} for version {api_version}")
            
            return test_func(*args, **kwargs)
        
        return conditional_wrapper
    
    return decorator


def feature_matrix_test(feature_matrix: Dict[str, Dict[str, bool]],
                       skip_partial: bool = False) -> Callable:
    """
    Decorator for testing feature combinations across versions.
    
    Args:
        feature_matrix: Dictionary mapping versions to feature availability.
        skip_partial: If True, skip tests where not all features are available.
        
    Returns:
        Decorator function that tests feature combinations.
        
    Example:
        @feature_matrix_test({
            "v1": {"basic_crud": True, "filtering": False},
            "v2": {"basic_crud": True, "filtering": True}
        })
        def test_feature_combination(api_version, available_features):
            # Test will receive available_features dict for each version
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        detector = get_feature_detector()
        
        # Build test parameters
        test_params = []
        for version, expected_features in feature_matrix.items():
            # Verify actual feature availability matches expectations
            actual_features = {}
            all_available = True
            
            for feature, expected in expected_features.items():
                actual = detector.is_feature_available(version, feature)
                actual_features[feature] = actual
                
                if expected and not actual:
                    all_available = False
                elif not expected and actual:
                    # Feature unexpectedly available - log warning but continue
                    print(f"Warning: Feature '{feature}' unexpectedly available in {version}")
            
            if skip_partial and not all_available:
                continue
            
            test_params.append((version, actual_features))
        
        @pytest.mark.parametrize("api_version,available_features", test_params)
        @functools.wraps(test_func)
        def matrix_wrapper(api_version, available_features, *args, **kwargs):
            return test_func(api_version, available_features, *args, **kwargs)
        
        return matrix_wrapper
    
    return decorator


def auto_skip_unavailable(features: List[str], 
                         message_template: str = "Features not available: {features}") -> Callable:
    """
    Decorator that automatically skips tests when any of the specified features are unavailable.
    
    Args:
        features: List of feature names to check.
        message_template: Template for skip message with {features} placeholder.
        
    Returns:
        Decorator function that auto-skips based on feature availability.
        
    Example:
        @version_parametrize()
        @auto_skip_unavailable(["health_records", "statistics"])
        def test_health_statistics(api_version):
            # Test will auto-skip if either feature is unavailable
            pass
    """
    def decorator(test_func: Callable) -> Callable:
        @functools.wraps(test_func)
        def auto_skip_wrapper(*args, **kwargs):
            detector = get_feature_detector()
            
            # Find api_version in arguments
            api_version = None
            if 'api_version' in kwargs:
                api_version = kwargs['api_version']
            elif args and isinstance(args[0], str):
                api_version = args[0]
            
            if api_version:
                missing_features = detector.get_missing_features(api_version, features)
                if missing_features:
                    skip_msg = message_template.format(features=missing_features)
                    pytest.skip(f"{skip_msg} in {api_version}")
            
            return test_func(*args, **kwargs)
        
        return auto_skip_wrapper
    
    return decorator


# Utility functions for feature detection

def check_feature_compatibility(version1: str, version2: str, 
                              features: List[str]) -> Dict[str, Any]:
    """
    Check feature compatibility between two versions.
    
    Args:
        version1: First version to compare.
        version2: Second version to compare.
        features: List of features to compare.
        
    Returns:
        Dictionary containing compatibility analysis.
    """
    detector = get_feature_detector()
    
    result = {
        'compatible': True,
        'version1_only': [],
        'version2_only': [],
        'common_features': [],
        'incompatible_features': []
    }
    
    for feature in features:
        v1_has = detector.is_feature_available(version1, feature)
        v2_has = detector.is_feature_available(version2, feature)
        
        if v1_has and v2_has:
            result['common_features'].append(feature)
        elif v1_has and not v2_has:
            result['version1_only'].append(feature)
            result['compatible'] = False
        elif not v1_has and v2_has:
            result['version2_only'].append(feature)
            result['compatible'] = False
        else:
            result['incompatible_features'].append(feature)
    
    return result


def get_feature_evolution_path(feature: str) -> List[str]:
    """
    Get the evolution path of a feature across versions.
    
    Args:
        feature: Feature name to trace.
        
    Returns:
        List of versions where the feature was introduced/available, in order.
    """
    detector = get_feature_detector()
    all_versions = detector.config_manager.get_supported_versions()
    
    # Sort versions (assuming they follow v1, v2, v3... pattern)
    try:
        sorted_versions = sorted(all_versions, key=lambda x: int(x[1:]) if x.startswith('v') else 0)
    except (ValueError, IndexError):
        sorted_versions = sorted(all_versions)
    
    evolution_path = []
    for version in sorted_versions:
        if detector.is_feature_available(version, feature):
            evolution_path.append(version)
    
    return evolution_path


def analyze_test_coverage(test_functions: List[Callable]) -> Dict[str, Any]:
    """
    Analyze test coverage across versions and features.
    
    Args:
        test_functions: List of test functions to analyze.
        
    Returns:
        Dictionary containing coverage analysis.
    """
    detector = get_feature_detector()
    all_versions = detector.config_manager.get_supported_versions()
    
    coverage = {
        'total_tests': len(test_functions),
        'version_coverage': {v: 0 for v in all_versions},
        'feature_coverage': {},
        'uncovered_combinations': []
    }
    
    # This is a simplified analysis - in practice, you'd need to inspect
    # the decorators and parameters of each test function
    for test_func in test_functions:
        # Check if test has version parametrization
        if hasattr(test_func, 'pytestmark'):
            for mark in test_func.pytestmark:
                if mark.name == 'parametrize' and 'api_version' in str(mark.args):
                    # Count coverage for parametrized versions
                    for version in mark.args[1]:
                        coverage['version_coverage'][version] += 1
    
    return coverage