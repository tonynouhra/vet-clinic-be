# Getting Started with Dynamic API Testing Framework

This guide will help you get started with the dynamic API testing framework, which eliminates code duplication across API versions by creating parameterized, version-aware tests.

## Quick Start

### 1. Basic Version-Aware Test

The simplest way to create a test that runs across all API versions:

```python
from tests.dynamic.fixtures import parametrize_versions
from tests.dynamic.base_test import BaseVersionTest

@parametrize_versions()
class TestPets:
    def test_get_pets(self, api_version: str, base_test: BaseVersionTest):
        # This test automatically runs for all configured versions (v1, v2, etc.)
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        
        # Your test logic here...
        assert f"/api/{api_version}/pets" in endpoint
```

### 2. Feature-Specific Testing

For features that only exist in certain versions:

```python
from tests.dynamic.fixtures import parametrize_feature_versions

@parametrize_feature_versions("health_records")
class TestHealthRecords:
    def test_health_records(self, api_version: str, base_test: BaseVersionTest):
        # This test only runs on versions that support health_records (v2+)
        endpoint = base_test.get_endpoint_url(api_version, "health_records", pet_id="123")
        
        # Test health records functionality...
```

### 3. Version-Appropriate Test Data

Generate test data that matches each version's schema:

```python
@parametrize_versions()
class TestPetCreation:
    def test_create_pet(self, api_version: str, base_test: BaseVersionTest):
        # Generate version-appropriate pet data
        pet_data = base_test.build_test_data(api_version, "pet", "create", 
                                           name="TestPet", 
                                           species="dog")
        
        # v1 data: basic fields only
        # v2 data: includes temperament, behavioral_notes, etc.
        
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        # Make request with version-appropriate data...
```

## Core Concepts

### Configuration-Driven Testing

All version differences are defined in `tests/config/version_config.yaml`:

```yaml
versions:
  v1:
    base_url: "/api/v1"
    features:
      health_records: false
      statistics: false
    schema_fields:
      pet_create: ["name", "species", "breed", "owner_id"]
  v2:
    base_url: "/api/v2"
    features:
      health_records: true
      statistics: true
    schema_fields:
      pet_create: ["name", "species", "breed", "owner_id", "temperament", "behavioral_notes"]
```

### Automatic Feature Detection

Tests automatically skip when features aren't supported:

```python
@parametrize_versions()
class TestConditionalFeatures:
    def test_statistics(self, api_version: str, base_test: BaseVersionTest, skip_if_feature_unavailable):
        # Automatically skips for v1, runs for v2
        skip_if_feature_unavailable("statistics")
        
        # Test statistics functionality...
```

## Common Patterns

### Pattern 1: CRUD Operations Across Versions

```python
@parametrize_versions()
class TestPetCRUD:
    async def test_create_pet(self, api_version: str, base_test: BaseVersionTest, async_client):
        # Generate version-appropriate data
        pet_data = base_test.build_test_data(api_version, "pet", "create", name="TestPet")
        
        # Build endpoint URL
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        
        # Make request
        response = await base_test.make_request("POST", endpoint, async_client, json=pet_data)
        
        # Assert success
        base_test.assert_status_code(response, 201, "Creating pet")
        
        # Validate response structure
        pet_response = response.json()
        base_test.validate_response_structure(pet_response, api_version, "pet")
    
    async def test_get_pet(self, api_version: str, base_test: BaseVersionTest, async_client):
        # Create a test pet first
        pet = await base_test.create_test_resource(async_client, api_version, "pet", name="GetTestPet")
        
        # Get the pet
        endpoint = base_test.get_endpoint_url(api_version, "pets", pet["id"])
        response = await base_test.make_request("GET", endpoint, async_client)
        
        # Validate response
        base_test.assert_status_code(response, 200, "Getting pet")
        pet_data = response.json()
        base_test.validate_response_structure(pet_data, api_version, "pet")
        
        # Cleanup
        await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
```

### Pattern 2: Version-Specific Field Validation

```python
@parametrize_versions()
class TestVersionSpecificFields:
    def test_pet_response_fields(self, api_version: str, base_test: BaseVersionTest):
        # Get expected fields for this version
        expected_fields = base_test.config_manager.get_schema_fields(api_version, "pet_response")
        
        # Create test data
        pet_data = base_test.build_test_data(api_version, "pet", "create")
        
        # Verify version-specific fields
        if api_version == "v1":
            assert "temperament" not in expected_fields
            assert "behavioral_notes" not in expected_fields
        elif api_version == "v2":
            assert "temperament" in expected_fields
            assert "behavioral_notes" in expected_fields
```

### Pattern 3: Error Handling Consistency

```python
@parametrize_versions()
class TestErrorHandling:
    async def test_not_found_error(self, api_version: str, base_test: BaseVersionTest, async_client):
        # Test that 404 errors are consistent across versions
        endpoint = base_test.get_endpoint_url(api_version, "pets", "nonexistent-id")
        response = await base_test.make_request("GET", endpoint, async_client)
        
        # Assert consistent error response
        base_test.assert_error_response(response, 404)
    
    async def test_validation_error(self, api_version: str, base_test: BaseVersionTest, async_client):
        # Test validation errors with invalid data
        invalid_data = {"name": ""}  # Empty name should be invalid
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        
        response = await base_test.make_request("POST", endpoint, async_client, json=invalid_data)
        base_test.assert_error_response(response, 422)
```

## Using Fixtures Directly

If you prefer not to inherit from `BaseVersionTest`, you can use fixtures directly:

```python
@parametrize_versions()
class TestWithFixtures:
    def test_endpoint_building(self, api_version: str, endpoint_builder):
        pets_url = endpoint_builder("pets")
        pet_url = endpoint_builder("pets", "123")
        
        assert f"/api/{api_version}/pets" in pets_url
        assert f"/api/{api_version}/pets/123" in pet_url
    
    def test_data_generation(self, api_version: str, test_data_builder):
        pet_data = test_data_builder("pet", "create", name="TestPet")
        
        assert pet_data["name"] == "TestPet"
        # Version-specific fields are automatically included/excluded
    
    def test_feature_checking(self, api_version: str, feature_checker, skip_if_feature_unavailable):
        # Skip if feature not available
        skip_if_feature_unavailable("health_records")
        
        # If we get here, feature is available
        assert feature_checker("health_records")
```

## Advanced Usage

### Custom Version Selection

Test specific versions only:

```python
@pytest.mark.parametrize("api_version", ["v1", "v2"], indirect=True)
class TestSpecificVersions:
    def test_only_v1_and_v2(self, api_version: str, base_test: BaseVersionTest):
        # This test only runs for v1 and v2
        pass
```

### Multiple Feature Requirements

```python
from tests.dynamic.decorators import require_features

@parametrize_versions()
@require_features(["health_records", "statistics"])
class TestAdvancedFeatures:
    def test_health_statistics(self, api_version: str, base_test: BaseVersionTest):
        # Only runs on versions supporting both features
        pass
```

### Conditional Logic Based on Version

```python
@parametrize_versions()
class TestVersionConditional:
    def test_version_specific_behavior(self, api_version: str, base_test: BaseVersionTest):
        if api_version == "v1":
            # v1-specific test logic
            pass
        elif api_version == "v2":
            # v2-specific test logic
            pass
        
        # Common test logic for all versions
```

## Best Practices

### 1. Use Configuration for Version Differences

❌ **Don't hardcode version logic:**
```python
def test_pet_fields(self, api_version: str):
    if api_version == "v1":
        expected_fields = ["name", "species", "breed"]
    elif api_version == "v2":
        expected_fields = ["name", "species", "breed", "temperament"]
```

✅ **Use configuration:**
```python
def test_pet_fields(self, api_version: str, base_test: BaseVersionTest):
    expected_fields = base_test.config_manager.get_schema_fields(api_version, "pet_response")
```

### 2. Use Feature Detection for Conditional Tests

❌ **Don't hardcode version checks:**
```python
def test_health_records(self, api_version: str):
    if api_version == "v1":
        pytest.skip("Health records not in v1")
```

✅ **Use feature detection:**
```python
def test_health_records(self, api_version: str, skip_if_feature_unavailable):
    skip_if_feature_unavailable("health_records")
```

### 3. Generate Version-Appropriate Test Data

❌ **Don't create version-specific data manually:**
```python
def test_create_pet(self, api_version: str):
    if api_version == "v1":
        pet_data = {"name": "Test", "species": "dog"}
    elif api_version == "v2":
        pet_data = {"name": "Test", "species": "dog", "temperament": "friendly"}
```

✅ **Use data builders:**
```python
def test_create_pet(self, api_version: str, base_test: BaseVersionTest):
    pet_data = base_test.build_test_data(api_version, "pet", "create", name="Test", species="dog")
```

### 4. Validate Response Structures

Always validate that responses match expected version schemas:

```python
async def test_get_pet(self, api_version: str, base_test: BaseVersionTest, async_client):
    # ... create and get pet ...
    
    pet_data = response.json()
    
    # Validate structure matches version expectations
    base_test.validate_response_structure(pet_data, api_version, "pet")
    
    # Validate version-specific fields
    base_test.validate_version_specific_fields(pet_data, api_version, "pet")
```

### 5. Clean Up Test Resources

Always clean up resources created during tests:

```python
async def test_pet_operations(self, api_version: str, base_test: BaseVersionTest, async_client):
    # Create test pet
    pet = await base_test.create_test_resource(async_client, api_version, "pet", name="TestPet")
    
    try:
        # Test operations...
        pass
    finally:
        # Always clean up
        await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
```

## Troubleshooting

### Common Issues

1. **Test skipped unexpectedly**
   - Check if the feature is enabled in `version_config.yaml`
   - Verify the feature name matches exactly

2. **Schema validation errors**
   - Ensure schema fields are defined in configuration
   - Check that API responses match configured schemas

3. **Endpoint not found errors**
   - Verify endpoint URLs are correct in configuration
   - Check that the resource exists in the specified version

### Debug Configuration

```python
def debug_configuration(api_version: str, base_test: BaseVersionTest):
    config = base_test.config_manager.get_version_config(api_version)
    print(f"Configuration for {api_version}:")
    print(f"  Features: {config['features']}")
    print(f"  Endpoints: {config['endpoints']}")
    print(f"  Schema fields: {config.get('schema_fields', {})}")
```

## Next Steps

- Read the [Configuration Reference](CONFIG_REFERENCE.md) for detailed configuration options
- Check out [Common Testing Scenarios](COMMON_SCENARIOS.md) for more examples
- Review [Best Practices](BEST_PRACTICES.md) for advanced patterns
- See [Migration Guide](MIGRATION_GUIDE.md) to convert existing tests