"""
Version-aware pytest fixtures for dynamic API testing.

Provides parameterized fixtures that automatically test across API versions
and configuration-driven test setup.
"""

from typing import Dict, Any, List
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from tests.dynamic.config_manager import get_config_manager, VersionConfigManager
from tests.dynamic.base_test import BaseVersionTest


@pytest.fixture(params=None)
def api_version(request) -> str:
    """
    Parameterized fixture that provides API version for testing.
    
    By default, tests run against all configured versions.
    Can be overridden by setting params in test configuration.
    
    Returns:
        API version string (e.g., 'v1', 'v2')
    """
    # If no specific versions requested, use all supported versions
    if request.param is None:
        config_manager = get_config_manager()
        supported_versions = config_manager.get_supported_versions()
        
        # For parametrized tests, we need to handle this differently
        # This fixture will be used with pytest.mark.parametrize
        return supported_versions[0] if supported_versions else "v1"
    
    return request.param


@pytest.fixture
def version_config(api_version: str) -> Dict[str, Any]:
    """
    Fixture that provides configuration for the current API version.
    
    Args:
        api_version: API version from api_version fixture
        
    Returns:
        Dictionary containing version-specific configuration
    """
    config_manager = get_config_manager()
    return config_manager.get_version_config(api_version)


@pytest.fixture
def base_url(api_version: str) -> str:
    """
    Fixture that provides base URL for the current API version.
    
    Args:
        api_version: API version from api_version fixture
        
    Returns:
        Base URL string for the API version
    """
    config_manager = get_config_manager()
    return config_manager.get_base_url(api_version)


@pytest.fixture
def config_manager() -> VersionConfigManager:
    """
    Fixture that provides the version configuration manager.
    
    Returns:
        VersionConfigManager instance
    """
    return get_config_manager()


@pytest.fixture
def base_test() -> BaseVersionTest:
    """
    Fixture that provides a BaseVersionTest instance.
    
    Returns:
        BaseVersionTest instance with utilities
    """
    return BaseVersionTest()


@pytest.fixture
async def async_client(api_version: str) -> AsyncClient:
    """
    Fixture that provides an async HTTP client with version context.
    
    Args:
        api_version: API version from api_version fixture
        
    Returns:
        AsyncClient configured for the API version
    """
    # Import here to avoid circular imports
    from app.main import app
    
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        # Add version context to client
        client.headers.update({
            "X-API-Version": api_version,
            "Content-Type": "application/json"
        })
        yield client


@pytest.fixture
def sync_client(api_version: str) -> TestClient:
    """
    Fixture that provides a synchronous HTTP client with version context.
    
    Args:
        api_version: API version from api_version fixture
        
    Returns:
        TestClient configured for the API version
    """
    # Import here to avoid circular imports
    from app.main import app
    
    client = TestClient(app)
    
    # Add version context to client
    client.headers.update({
        "X-API-Version": api_version,
        "Content-Type": "application/json"
    })
    
    return client


@pytest.fixture
def supported_versions(config_manager: VersionConfigManager) -> List[str]:
    """
    Fixture that provides list of all supported API versions.
    
    Args:
        config_manager: Configuration manager from config_manager fixture
        
    Returns:
        List of supported version strings
    """
    return config_manager.get_supported_versions()


@pytest.fixture
def version_features(api_version: str, config_manager: VersionConfigManager) -> Dict[str, bool]:
    """
    Fixture that provides feature availability for the current API version.
    
    Args:
        api_version: API version from api_version fixture
        config_manager: Configuration manager from config_manager fixture
        
    Returns:
        Dictionary mapping feature names to availability
    """
    return config_manager.get_features_for_version(api_version)


@pytest.fixture
def endpoint_builder(api_version: str, config_manager: VersionConfigManager):
    """
    Fixture that provides a function to build endpoint URLs for the current version.
    
    Args:
        api_version: API version from api_version fixture
        config_manager: Configuration manager from config_manager fixture
        
    Returns:
        Function that builds endpoint URLs
    """
    def build_endpoint(resource: str, resource_id: str = None, **kwargs) -> str:
        """
        Build endpoint URL for the current API version.
        
        Args:
            resource: Resource name (e.g., 'pets', 'users')
            resource_id: Optional resource ID
            **kwargs: Additional URL parameters
            
        Returns:
            Complete endpoint URL
        """
        endpoint_url = config_manager.get_endpoint_url(api_version, resource, **kwargs)
        
        if resource_id:
            endpoint_url = f"{endpoint_url}/{resource_id}"
        
        return endpoint_url
    
    return build_endpoint


@pytest.fixture
def test_data_builder(api_version: str, config_manager: VersionConfigManager):
    """
    Fixture that provides a function to build test data for the current version.
    
    Args:
        api_version: API version from api_version fixture
        config_manager: Configuration manager from config_manager fixture
        
    Returns:
        Function that builds version-appropriate test data
    """
    def build_data(resource: str, operation: str = "create", **overrides) -> Dict[str, Any]:
        """
        Build test data for the current API version.
        
        Args:
            resource: Resource type (e.g., 'pet', 'user')
            operation: Operation type (e.g., 'create', 'update')
            **overrides: Field values to override defaults
            
        Returns:
            Dictionary containing test data
        """
        schema_name = f"{resource}_{operation}"
        
        # Get default values
        try:
            test_data = config_manager.get_default_values(api_version, schema_name).copy()
        except Exception:
            test_data = {}
        
        # Apply overrides
        test_data.update(overrides)
        
        return test_data
    
    return build_data


@pytest.fixture
def feature_checker(api_version: str, config_manager: VersionConfigManager):
    """
    Fixture that provides a function to check feature availability.
    
    Args:
        api_version: API version from api_version fixture
        config_manager: Configuration manager from config_manager fixture
        
    Returns:
        Function that checks if features are available
    """
    def has_feature(feature: str) -> bool:
        """
        Check if a feature is available in the current API version.
        
        Args:
            feature: Feature name to check
            
        Returns:
            True if feature is available, False otherwise
        """
        return config_manager.get_feature_availability(api_version, feature)
    
    return has_feature


@pytest.fixture
def skip_if_feature_unavailable(api_version: str, config_manager: VersionConfigManager):
    """
    Fixture that provides a function to skip tests for unavailable features.
    
    Args:
        api_version: API version from api_version fixture
        config_manager: Configuration manager from config_manager fixture
        
    Returns:
        Function that skips tests if features are unavailable
    """
    def skip_if_unavailable(feature: str) -> None:
        """
        Skip test if feature is not available in the current API version.
        
        Args:
            feature: Feature name to check
        """
        if not config_manager.get_feature_availability(api_version, feature):
            pytest.skip(f"Feature '{feature}' not available in {api_version}")
    
    return skip_if_unavailable


# Parametrization helpers for common use cases

def parametrize_versions(versions: List[str] = None):
    """
    Decorator to parametrize tests across API versions.
    
    Args:
        versions: List of versions to test. If None, uses all supported versions.
        
    Returns:
        pytest.mark.parametrize decorator
    """
    if versions is None:
        config_manager = get_config_manager()
        versions = config_manager.get_supported_versions()
    
    return pytest.mark.parametrize("api_version", versions, indirect=True)


def parametrize_feature_versions(feature: str):
    """
    Decorator to parametrize tests across versions that support a specific feature.
    
    Args:
        feature: Feature name that must be supported
        
    Returns:
        pytest.mark.parametrize decorator
    """
    config_manager = get_config_manager()
    supporting_versions = config_manager.get_versions_supporting_feature(feature)
    
    if not supporting_versions:
        # If no versions support the feature, skip the test entirely
        return pytest.mark.skip(reason=f"No versions support feature '{feature}'")
    
    return pytest.mark.parametrize("api_version", supporting_versions, indirect=True)


def parametrize_resources(resources: List[str]):
    """
    Decorator to parametrize tests across multiple resources.
    
    Args:
        resources: List of resource names to test
        
    Returns:
        pytest.mark.parametrize decorator
    """
    return pytest.mark.parametrize("resource", resources)


def parametrize_crud_operations(operations: List[str] = None):
    """
    Decorator to parametrize tests across CRUD operations.
    
    Args:
        operations: List of operations to test. Defaults to ['create', 'read', 'update', 'delete']
        
    Returns:
        pytest.mark.parametrize decorator
    """
    if operations is None:
        operations = ['create', 'read', 'update', 'delete']
    
    return pytest.mark.parametrize("operation", operations)