# Dynamic API Testing Framework

This directory contains the implementation of the dynamic API testing framework that eliminates code duplication across API versions by creating parameterized, version-aware tests.

## Components

### Core Components

1. **`config_manager.py`** - Version Configuration Manager
   - Manages version-specific configurations loaded from YAML files
   - Provides centralized access to version differences, features, and schema definitions
   - Handles configuration validation and error handling

2. **`base_test.py`** - BaseVersionTest Class
   - Base class with version-aware utilities for testing
   - Provides methods for endpoint URL building, feature checking, and response validation
   - Includes helper methods for test data generation and common test operations

3. **`fixtures.py`** - Version-Aware Pytest Fixtures
   - Parameterized fixtures that automatically test across API versions
   - Configuration-driven test setup with version context
   - Helper functions for endpoint building, data generation, and feature checking

### Configuration

4. **`../config/version_config.yaml`** - Version Configuration File
   - External YAML configuration defining version-specific capabilities
   - Endpoint URLs, feature availability, schema fields, and default values
   - Easily extensible for new API versions

### Examples and Tests

5. **`example_test.py`** - Example Usage
   - Demonstrates how to use the dynamic testing framework
   - Shows different patterns for version-aware testing
   - Examples of feature-specific and resource-specific testing

6. **`../unit/test_fixtures.py`** - Framework Tests
   - Unit tests for the dynamic testing fixtures
   - Validates that all fixtures work correctly
   - Tests parametrization helpers and configuration loading

## Key Features

### Version-Aware Testing
- Tests automatically run against all configured API versions
- Version-specific features are handled through configuration
- Automatic test skipping for unsupported features

### Configuration-Driven
- All version differences are externalized to YAML configuration
- No hardcoded version logic in test code
- Easy to add new versions by updating configuration

### Intelligent Data Generation
- Test data factories generate version-appropriate data
- Respects required/optional field constraints per version
- Supports field overrides and customization

### Feature Detection
- Runtime feature availability checking
- Automatic test skipping for unavailable features
- Clear skip messages indicating version limitations

## Usage Patterns

### 1. Using BaseVersionTest Class

```python
from tests.dynamic.base_test import BaseVersionTest
from tests.dynamic.fixtures import parametrize_versions

@parametrize_versions()
class TestPets:
    def test_pet_creation(self, api_version: str, base_test: BaseVersionTest):
        # Generate version-appropriate test data
        pet_data = base_test.build_test_data(api_version, "pet", "create", name="TestPet")
        
        # Build endpoint URL
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        
        # Test logic here...
```

### 2. Using Fixtures Directly

```python
from tests.dynamic.fixtures import parametrize_versions

@parametrize_versions()
class TestPets:
    def test_pet_endpoints(self, api_version: str, endpoint_builder, test_data_builder):
        # Use fixture functions
        pets_url = endpoint_builder("pets")
        pet_data = test_data_builder("pet", "create", name="TestPet")
        
        # Test logic here...
```

### 3. Feature-Specific Testing

```python
from tests.dynamic.fixtures import parametrize_feature_versions

@parametrize_feature_versions("health_records")
class TestHealthRecords:
    def test_health_records(self, api_version: str, base_test: BaseVersionTest):
        # This test only runs on versions that support health_records
        assert base_test.should_test_feature(api_version, "health_records")
        
        # Test health records functionality...
```

### 4. Conditional Feature Testing

```python
@parametrize_versions()
class TestConditionalFeatures:
    def test_statistics(self, api_version: str, skip_if_feature_unavailable):
        # Skip if statistics not supported
        skip_if_feature_unavailable("statistics")
        
        # Test statistics functionality...
```

## Benefits

### Immediate Benefits
- **Eliminate Code Duplication**: Single test definitions work across all versions
- **Consistent Test Coverage**: Ensure all versions receive the same level of testing
- **Easier Maintenance**: Changes to business logic automatically apply to all version tests
- **Faster Test Development**: New tests automatically work with all versions

### Long-term Benefits
- **Scalable Version Management**: Adding new versions requires only configuration changes
- **Feature Evolution Tracking**: Clear visibility into feature availability across versions
- **Regression Prevention**: Automatic testing ensures version consistency
- **Living Documentation**: Configuration serves as documentation of version differences

## Configuration Structure

The version configuration file (`tests/config/version_config.yaml`) defines:

- **Base URLs**: API base paths for each version
- **Features**: Boolean flags for feature availability
- **Endpoints**: Resource endpoint URLs with parameter support
- **Schema Fields**: Lists of fields for request/response schemas
- **Required/Optional Fields**: Field validation constraints
- **Default Values**: Default data for test generation

## Adding New Versions

To add a new API version (e.g., v3):

1. Add v3 configuration to `version_config.yaml`
2. Define new features, endpoints, and schema fields
3. Existing tests automatically include v3
4. Add v3-specific tests for new features

## Best Practices

1. **Use Configuration**: Externalize all version differences to configuration
2. **Feature Flags**: Use feature availability checking for conditional logic
3. **Data Generation**: Use test data builders for version-appropriate data
4. **Clear Naming**: Use descriptive test names that indicate version behavior
5. **Documentation**: Document version-specific behavior in test docstrings