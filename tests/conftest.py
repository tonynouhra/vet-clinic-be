"""
Global pytest configuration and fixtures for dynamic API testing.

This file makes the dynamic testing fixtures available to all test modules.
"""

# Import fixtures to make them available to all tests
from tests.dynamic.fixtures import (
    api_version,
    version_config,
    base_url,
    config_manager,
    base_test,
    async_client,
    sync_client,
    supported_versions,
    version_features,
    endpoint_builder,
    test_data_builder,
    feature_checker,
    skip_if_feature_unavailable,
    parametrize_versions,
    parametrize_feature_versions,
    parametrize_resources,
    parametrize_crud_operations,
)