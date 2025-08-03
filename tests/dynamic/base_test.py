"""
Base test class for dynamic API testing.

Provides common utilities and fixtures for version-agnostic testing
using pytest parametrization and configuration-driven testing.
"""

import pytest
from typing import Dict, Any, List, Optional, Union
from httpx import AsyncClient, Response

from tests.dynamic.config_manager import get_config_manager, ConfigurationError


class BaseVersionTest:
    """Base class for dynamic API tests with version-aware utilities."""
    
    @property
    def config_manager(self):
        """Get the configuration manager instance."""
        if not hasattr(self, '_config_manager'):
            self._config_manager = get_config_manager()
        return self._config_manager
    
    def get_endpoint_url(self, version: str, resource: str, resource_id: Optional[str] = None, **kwargs) -> str:
        """
        Build endpoint URL for a specific version and resource.
        
        Args:
            version: API version (e.g., 'v1', 'v2')
            resource: Resource name (e.g., 'pets', 'users', 'appointments')
            resource_id: Optional resource ID for specific resource endpoints
            **kwargs: Additional parameters for URL formatting
            
        Returns:
            Complete endpoint URL
            
        Raises:
            ConfigurationError: If version or resource is not found
        """
        try:
            # Get base endpoint URL from configuration
            endpoint_url = self.config_manager.get_endpoint_url(version, resource, **kwargs)
            
            # Append resource ID if provided
            if resource_id:
                endpoint_url = f"{endpoint_url}/{resource_id}"
            
            return endpoint_url
        except ConfigurationError as e:
            raise ConfigurationError(f"Failed to build endpoint URL: {e}")
    
    def should_test_feature(self, version: str, feature: str) -> bool:
        """
        Check if a feature should be tested for the specified version.
        
        Args:
            version: API version
            feature: Feature name
            
        Returns:
            True if feature is available and should be tested, False otherwise
        """
        return self.config_manager.get_feature_availability(version, feature)
    
    def skip_if_feature_unavailable(self, version: str, feature: str) -> None:
        """
        Skip test if feature is not available in the specified version.
        
        Args:
            version: API version
            feature: Feature name
        """
        if not self.should_test_feature(version, feature):
            pytest.skip(f"Feature '{feature}' not available in {version}")
    
    async def make_request(self, method: str, url: str, client: AsyncClient, **kwargs) -> Response:
        """
        Make an HTTP request with common error handling.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: Request URL
            client: HTTP client for making requests
            **kwargs: Additional request parameters (json, params, headers, etc.)
            
        Returns:
            HTTP response object
        """
        try:
            response = await client.request(method, url, **kwargs)
            return response
        except Exception as e:
            pytest.fail(f"Request failed: {method} {url} - {e}")
    
    def validate_response_structure(self, response: Dict[str, Any], version: str, resource: str, 
                                  schema_type: str = "response") -> None:
        """
        Validate that response has expected structure for version and resource.
        
        Args:
            response: Response data to validate
            version: API version being tested
            resource: Resource type (pet, user, appointment)
            schema_type: Schema type suffix (e.g., 'response', 'create')
            
        Raises:
            AssertionError: If response structure is invalid
            ConfigurationError: If schema configuration is not found
        """
        schema_name = f"{resource}_{schema_type}"
        
        try:
            expected_fields = self.config_manager.get_schema_fields(version, schema_name)
        except ConfigurationError:
            # If specific schema not found, try generic response schema
            schema_name = f"{resource}_response"
            try:
                expected_fields = self.config_manager.get_schema_fields(version, schema_name)
            except ConfigurationError:
                pytest.fail(f"No schema configuration found for {resource} in {version}")
        
        # Check that all expected fields are present
        missing_fields = []
        for field in expected_fields:
            if field not in response:
                missing_fields.append(field)
        
        if missing_fields:
            assert False, (
                f"Missing expected fields in {version} {resource} response: {missing_fields}. "
                f"Expected fields: {expected_fields}. "
                f"Actual fields: {list(response.keys())}"
            )
    
    def validate_version_specific_fields(self, response: Dict[str, Any], version: str, 
                                       resource: str) -> None:
        """
        Validate version-specific fields are present or absent as expected.
        
        Args:
            response: Response data to validate
            version: API version being tested
            resource: Resource type
        """
        # Get all versions to compare field differences
        all_versions = self.config_manager.get_supported_versions()
        schema_name = f"{resource}_response"
        
        for other_version in all_versions:
            if other_version == version:
                continue
            
            try:
                current_fields = set(self.config_manager.get_schema_fields(version, schema_name))
                other_fields = set(self.config_manager.get_schema_fields(other_version, schema_name))
                
                # Fields that should be present in current version but not in other
                version_specific_fields = current_fields - other_fields
                
                for field in version_specific_fields:
                    if field not in response:
                        pytest.fail(
                            f"Version-specific field '{field}' missing from {version} {resource} response"
                        )
                
                # Fields that should NOT be present in current version
                excluded_fields = other_fields - current_fields
                
                for field in excluded_fields:
                    if field in response:
                        pytest.fail(
                            f"Field '{field}' should not be present in {version} {resource} response "
                            f"(only available in {other_version})"
                        )
                        
            except ConfigurationError:
                # Skip validation if schema not found for comparison version
                continue
    
    def get_test_data_template(self, version: str, resource: str, operation: str = "create") -> Dict[str, Any]:
        """
        Get test data template for a specific version, resource, and operation.
        
        Args:
            version: API version
            resource: Resource type
            operation: Operation type (create, update)
            
        Returns:
            Dictionary containing test data template
        """
        schema_name = f"{resource}_{operation}"
        
        try:
            # Get default values from configuration
            default_values = self.config_manager.get_default_values(version, schema_name)
            return default_values.copy()
        except ConfigurationError:
            # Return empty dict if no defaults configured
            return {}
    
    def get_required_fields(self, version: str, resource: str, operation: str = "create") -> List[str]:
        """
        Get required fields for a specific version, resource, and operation.
        
        Args:
            version: API version
            resource: Resource type
            operation: Operation type
            
        Returns:
            List of required field names
        """
        schema_name = f"{resource}_{operation}"
        
        try:
            return self.config_manager.get_required_fields(version, schema_name)
        except ConfigurationError:
            return []
    
    def get_optional_fields(self, version: str, resource: str, operation: str = "create") -> List[str]:
        """
        Get optional fields for a specific version, resource, and operation.
        
        Args:
            version: API version
            resource: Resource type
            operation: Operation type
            
        Returns:
            List of optional field names
        """
        schema_name = f"{resource}_{operation}"
        
        try:
            return self.config_manager.get_optional_fields(version, schema_name)
        except ConfigurationError:
            return []
    
    def build_test_data(self, version: str, resource: str, operation: str = "create", 
                       **overrides) -> Dict[str, Any]:
        """
        Build test data for a specific version, resource, and operation.
        
        Args:
            version: API version
            resource: Resource type
            operation: Operation type
            **overrides: Field values to override defaults
            
        Returns:
            Dictionary containing test data
        """
        # Start with template data
        test_data = self.get_test_data_template(version, resource, operation)
        
        # Apply any overrides
        test_data.update(overrides)
        
        return test_data
    
    def assert_status_code(self, response: Response, expected_status: int, 
                          context: str = "") -> None:
        """
        Assert response status code with helpful error message.
        
        Args:
            response: HTTP response object
            expected_status: Expected status code
            context: Additional context for error message
        """
        if response.status_code != expected_status:
            error_msg = (
                f"Expected status {expected_status}, got {response.status_code}"
            )
            if context:
                error_msg = f"{context}: {error_msg}"
            
            # Include response body for debugging
            try:
                response_body = response.json()
                error_msg += f". Response: {response_body}"
            except:
                error_msg += f". Response text: {response.text}"
            
            assert False, error_msg
    
    def assert_error_response(self, response: Response, expected_status: int, 
                            expected_error_type: Optional[str] = None) -> None:
        """
        Assert error response format and content.
        
        Args:
            response: HTTP response object
            expected_status: Expected error status code
            expected_error_type: Expected error type in response
        """
        self.assert_status_code(response, expected_status, "Error response")
        
        try:
            error_data = response.json()
            
            # Check for common error response fields
            if "error" not in error_data and "detail" not in error_data:
                assert False, f"Error response missing 'error' or 'detail' field: {error_data}"
            
            if expected_error_type:
                error_type = error_data.get("error", {}).get("type") or error_data.get("type")
                if error_type != expected_error_type:
                    assert False, (
                        f"Expected error type '{expected_error_type}', "
                        f"got '{error_type}' in response: {error_data}"
                    )
        except ValueError:
            assert False, f"Error response is not valid JSON: {response.text}"
    
    async def create_test_resource(self, client: AsyncClient, version: str, resource: str, 
                                 **data_overrides) -> Dict[str, Any]:
        """
        Create a test resource for the specified version.
        
        Args:
            client: HTTP client for making requests
            version: API version
            resource: Resource type (user, pet, appointment)
            **data_overrides: Additional fields to override defaults
            
        Returns:
            Created resource data
        """
        # Build test data
        test_data = self.build_test_data(version, resource, "create", **data_overrides)
        
        # Get endpoint URL
        endpoint_url = self.get_endpoint_url(version, resource)
        
        # Make create request
        response = await self.make_request("POST", endpoint_url, client, json=test_data)
        
        # Assert successful creation
        self.assert_status_code(response, 201, f"Creating test {resource}")
        
        # Return created resource data
        return response.json()
    
    async def cleanup_test_resource(self, client: AsyncClient, version: str, resource: str, 
                                  resource_id: str) -> None:
        """
        Clean up a test resource.
        
        Args:
            client: HTTP client for making requests
            version: API version
            resource: Resource type
            resource_id: ID of resource to delete
        """
        try:
            endpoint_url = self.get_endpoint_url(version, resource, resource_id)
            response = await self.make_request("DELETE", endpoint_url, client)
            
            # Accept both 204 (No Content) and 200 (OK) for successful deletion
            if response.status_code not in [200, 204]:
                # Log warning but don't fail test
                print(f"Warning: Failed to cleanup {resource} {resource_id}: {response.status_code}")
        except Exception as e:
            # Log warning but don't fail test
            print(f"Warning: Exception during cleanup of {resource} {resource_id}: {e}")


# Backward compatibility alias
BaseDynamicTest = BaseVersionTest