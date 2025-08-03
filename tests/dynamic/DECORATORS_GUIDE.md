# Dynamic Testing Framework Decorators Guide

This guide explains how to use the parameterized test decorators and feature detection system in the dynamic API testing framework.

## Overview

The decorators provide a powerful way to write tests once and automatically run them across multiple API versions, with intelligent feature detection and skipping.

## Core Decorators

### @version_parametrize()

Automatically runs tests across all configured API versions.

```python
@version_parametrize()
def test_get_pets(api_version):
    # Test runs for all versions: v1, v2, etc.
    pass

@version_parametrize(versions=["v1", "v2"])
def test_specific_versions(api_version):
    # Test runs only for v1 and v2
    pass
```

### @feature_test(feature)

Runs tests only on versions that support the specified feature.

```python
@feature_test("health_records")
def test_health_records(api_version):
    # Only runs on versions supporting health_records (v2+)
    pass

@feature_test("statistics", versions=["v2", "v3"])
def test_statistics_limited(api_version):
    # Only runs on v2/v3 if they support statistics
    pass
```

### @crud_test(resource)

Parametrizes tests across versions and CRUD operations.

```python
@crud_test("pets")
def test_pet_crud(api_version, crud_operation):
    # Runs for all versions and operations: create, read, update, delete, list
    if crud_operation == "create":
        # Test creation logic
        pass
    elif crud_operation == "read":
        # Test reading logic
        pass

@crud_test("users", operations=["create", "read"])
def test_user_create_read(api_version, crud_operation):
    # Only tests create and read operations
    pass
```

## Advanced Decorators

### @smart_feature_test()

Enhanced feature testing with dependencies and optional features.

```python
@smart_feature_test(
    features=["health_records"],
    optional_features=["statistics"],
    dependencies={"health_records": ["enhanced_filtering"]}
)
def test_advanced_health_records(api_version):
    # Requires health_records and enhanced_filtering
    # Warns if statistics not available but doesn't skip
    pass
```

### @require_features()

Requires multiple features to be available.

```python
@version_parametrize()
@require_features(["health_records", "statistics"])
def test_health_statistics(api_version):
    # Only runs if both features are available
    pass
```

### @auto_skip_unavailable()

Automatically skips if any specified features are unavailable.

```python
@version_parametrize()
@auto_skip_unavailable(["enhanced_filtering"])
def test_filtering(api_version):
    # Skips if enhanced_filtering not available
    pass
```

### @conditional_skip()

Skips based on custom condition function.

```python
def has_batch_support(version):
    detector = get_feature_detector()
    return detector.is_feature_available(version, "batch_operations")

@version_parametrize()
@conditional_skip(has_batch_support, "Batch operations required")
def test_batch_operations(api_version):
    # Skips if custom condition returns False
    pass
```

## Utility Decorators

### @skip_versions()

Skips specific versions.

```python
@version_parametrize()
@skip_versions(["v1"], "Feature not available in v1")
def test_advanced_feature(api_version):
    # Runs on all versions except v1
    pass
```

### @version_specific()

Applies version-specific configurations.

```python
@version_parametrize()
@version_specific({
    "v1": {"skip": True, "skip_reason": "Not implemented"},
    "v2": {"marks": [pytest.mark.slow]}
})
def test_complex_feature(api_version):
    # Skipped for v1, marked as slow for v2
    pass
```

## Feature Detection System

### FeatureDetector Class

The `FeatureDetector` class provides advanced feature detection capabilities:

```python
from tests.dynamic.decorators import get_feature_detector

detector = get_feature_detector()

# Check feature availability
if detector.is_feature_available("v2", "health_records"):
    # Feature is available
    pass

# Get versions supporting a feature
supporting_versions = detector.get_feature_versions("statistics")

# Check for missing features
missing = detector.get_missing_features("v1", ["health_records", "statistics"])

# Validate feature dependencies
result = detector.validate_feature_dependencies(
    "v2", 
    "health_records", 
    {"health_records": ["enhanced_filtering"]}
)
```

## Best Practices

### 1. Use BaseVersionTest

Inherit from `BaseVersionTest` for version-aware utilities:

```python
from tests.dynamic.base_test import BaseVersionTest

class TestPets(BaseVersionTest):
    @version_parametrize()
    async def test_create_pet(self, api_version, async_client):
        endpoint = self.get_endpoint_url(api_version, "pets")
        test_data = self.build_test_data(api_version, "pets", "create")
        
        response = await self.make_request("POST", endpoint, async_client, json=test_data)
        self.assert_status_code(response, 201)
        
        pet_data = response.json()
        self.validate_response_structure(pet_data, api_version, "pet")
```

### 2. Combine Decorators

Decorators can be combined for complex scenarios:

```python
@version_parametrize()
@require_features(["health_records"])
@auto_skip_unavailable(["statistics"])
def test_health_with_stats(api_version):
    # Requires health_records, skips if statistics unavailable
    pass
```

### 3. Handle Version-Specific Data

Use the framework's data generation capabilities:

```python
@version_parametrize()
async def test_create_pet(self, api_version, async_client):
    # Automatically generates version-appropriate data
    test_data = self.build_test_data(api_version, "pets", "create", name="Custom Name")
    
    # Data will include v2-specific fields like temperament if testing v2
    endpoint = self.get_endpoint_url(api_version, "pets")
    response = await self.make_request("POST", endpoint, async_client, json=test_data)
```

### 4. Validate Version-Specific Responses

```python
@version_parametrize()
async def test_pet_response_structure(self, api_version, async_client):
    pet_data = await self.create_test_resource(async_client, api_version, "pets")
    
    # Validates that response has correct fields for the version
    self.validate_response_structure(pet_data, api_version, "pet")
    
    # Validates version-specific field presence/absence
    self.validate_version_specific_fields(pet_data, api_version, "pet")
```

## Configuration

The decorators rely on the version configuration in `tests/config/version_config.yaml`. Make sure your configuration includes:

- `features`: Boolean flags for feature availability per version
- `endpoints`: URL patterns for each resource per version  
- `schema_fields`: Expected fields in requests/responses per version

## Error Handling

The framework provides clear error messages and skip reasons:

- Tests are automatically skipped with descriptive messages when features are unavailable
- Configuration errors are caught and reported clearly
- Missing dependencies are validated and reported

## Testing the Decorators

Run the decorator tests to verify functionality:

```bash
python -m pytest tests/unit/test_decorators.py -v
```

See `tests/dynamic/example_decorator_usage.py` for comprehensive usage examples.