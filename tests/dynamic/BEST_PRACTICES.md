# Best Practices for Dynamic API Testing

This document outlines best practices for using the dynamic API testing framework effectively and maintaining high-quality, maintainable tests.

## Table of Contents

1. [Configuration Management](#configuration-management)
2. [Test Organization](#test-organization)
3. [Data Management](#data-management)
4. [Error Handling](#error-handling)
5. [Performance Considerations](#performance-considerations)
6. [Maintenance and Evolution](#maintenance-and-evolution)
7. [Common Anti-Patterns](#common-anti-patterns)
8. [Testing Strategies](#testing-strategies)

## Configuration Management

### 1. Keep Configuration External

✅ **Do: Use configuration files for version differences**
```python
# Good: Configuration-driven
def test_pet_fields(self, api_version: str, base_test: BaseVersionTest):
    expected_fields = base_test.config_manager.get_schema_fields(api_version, "pet_response")
    # Test logic using expected_fields
```

❌ **Don't: Hardcode version-specific logic**
```python
# Bad: Hardcoded version logic
def test_pet_fields(self, api_version: str):
    if api_version == "v1":
        expected_fields = ["name", "species", "breed"]
    elif api_version == "v2":
        expected_fields = ["name", "species", "breed", "temperament"]
    # This becomes unmaintainable with more versions
```

### 2. Maintain Configuration Consistency

✅ **Do: Keep configurations synchronized with actual API**
```yaml
# Good: Accurate configuration
versions:
  v2:
    features:
      health_records: true  # Actually available in v2
    schema_fields:
      pet_response: ["id", "name", "species", "temperament"]  # Matches actual API
```

❌ **Don't: Let configuration drift from reality**
```yaml
# Bad: Outdated configuration
versions:
  v2:
    features:
      health_records: false  # Actually available but marked as false
    schema_fields:
      pet_response: ["id", "name", "species"]  # Missing fields that exist in API
```

### 3. Use Semantic Feature Names

✅ **Do: Use descriptive feature names**
```yaml
features:
  health_records: true
  enhanced_filtering: true
  batch_operations: true
  real_time_notifications: true
```

❌ **Don't: Use cryptic or version-specific names**
```yaml
features:
  hr: true          # Unclear abbreviation
  filter_v2: true   # Version-specific naming
  batch: true       # Too generic
  feature_x: true   # Meaningless name
```

## Test Organization

### 1. Group Tests by Functionality

✅ **Do: Organize tests by business functionality**
```python
# Good: Functional organization
@parametrize_versions()
class TestPetManagement:
    """All pet-related operations."""
    
    async def test_create_pet(self, ...): pass
    async def test_update_pet(self, ...): pass
    async def test_delete_pet(self, ...): pass

@parametrize_feature_versions("health_records")
class TestHealthRecords:
    """Health record specific functionality."""
    
    async def test_create_health_record(self, ...): pass
    async def test_health_record_history(self, ...): pass
```

❌ **Don't: Organize tests by API version**
```python
# Bad: Version-based organization
class TestV1Endpoints:
    def test_v1_pets(self, ...): pass
    def test_v1_users(self, ...): pass

class TestV2Endpoints:
    def test_v2_pets(self, ...): pass
    def test_v2_users(self, ...): pass
    def test_v2_health_records(self, ...): pass
```

### 2. Use Descriptive Test Names

✅ **Do: Use clear, descriptive test names**
```python
async def test_create_pet_with_required_fields_only(self, ...):
    """Test pet creation with only required fields."""

async def test_update_pet_preserves_unchanged_fields(self, ...):
    """Test that updating a pet preserves fields not in the update."""

async def test_delete_pet_removes_associated_health_records(self, ...):
    """Test that deleting a pet also removes its health records."""
```

❌ **Don't: Use generic or unclear names**
```python
async def test_pet_1(self, ...): pass
async def test_pet_crud(self, ...): pass
async def test_version_differences(self, ...): pass
```

### 3. Structure Tests Consistently

✅ **Do: Follow a consistent test structure**
```python
async def test_create_pet(self, api_version: str, base_test: BaseVersionTest, async_client):
    """Test pet creation with version-appropriate data."""
    # Arrange: Set up test data
    pet_data = base_test.build_test_data(api_version, "pet", "create", name="Test Pet")
    endpoint = base_test.get_endpoint_url(api_version, "pets")
    
    # Act: Perform the operation
    response = await base_test.make_request("POST", endpoint, async_client, json=pet_data)
    
    # Assert: Verify results
    base_test.assert_status_code(response, 201, "Creating pet")
    pet = response.json()
    base_test.validate_response_structure(pet, api_version, "pet")
    
    # Cleanup: Remove test data
    await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
```

## Data Management

### 1. Use Data Builders for Test Data

✅ **Do: Use version-aware data builders**
```python
async def test_create_pet(self, api_version: str, base_test: BaseVersionTest, async_client):
    # Good: Uses data builder with overrides
    pet_data = base_test.build_test_data(
        api_version, "pet", "create",
        name="Specific Test Pet",
        species="dog"
    )
    # Data automatically includes version-appropriate fields
```

❌ **Don't: Hardcode test data**
```python
async def test_create_pet(self, api_version: str, base_test: BaseVersionTest, async_client):
    # Bad: Hardcoded data that may not work across versions
    pet_data = {
        "name": "Test Pet",
        "species": "dog",
        "breed": "labrador",
        "temperament": "friendly"  # May not exist in v1
    }
```

### 2. Clean Up Test Resources

✅ **Do: Always clean up test resources**
```python
async def test_pet_operations(self, api_version: str, base_test: BaseVersionTest, async_client):
    # Create test resource
    pet = await base_test.create_test_resource(async_client, api_version, "pet", name="Test Pet")
    
    try:
        # Test operations
        endpoint = base_test.get_endpoint_url(api_version, "pets", pet["id"])
        response = await base_test.make_request("GET", endpoint, async_client)
        # ... test logic ...
    finally:
        # Always clean up, even if test fails
        await base_test.cleanup_test_resource(async_client, api_version, "pet", pet["id"])
```

❌ **Don't: Leave test data behind**
```python
async def test_pet_operations(self, api_version: str, base_test: BaseVersionTest, async_client):
    # Bad: No cleanup
    pet = await base_test.create_test_resource(async_client, api_version, "pet", name="Test Pet")
    
    # Test operations without cleanup
    # This leaves test data in the system
```

### 3. Use Realistic Test Data

✅ **Do: Use realistic, meaningful test data**
```python
pet_data = base_test.build_test_data(
    api_version, "pet", "create",
    name="Buddy",                    # Realistic pet name
    species="dog",                   # Valid species
    breed="golden_retriever",        # Real breed
    weight=25.5,                     # Reasonable weight
    temperament="friendly"           # Realistic temperament
)
```

❌ **Don't: Use meaningless or unrealistic data**
```python
pet_data = {
    "name": "test123",               # Unrealistic name
    "species": "xyz",                # Invalid species
    "breed": "abc",                  # Fake breed
    "weight": 999999,                # Unrealistic weight
    "temperament": "test"            # Meaningless temperament
}
```

## Error Handling

### 1. Test Error Scenarios Consistently

✅ **Do: Test error handling across all versions**
```python
@parametrize_versions()
class TestErrorHandling:
    async def test_not_found_error(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test 404 errors are consistent across versions."""
        endpoint = base_test.get_endpoint_url(api_version, "pets", "nonexistent-id")
        response = await base_test.make_request("GET", endpoint, async_client)
        
        # Use framework method for consistent error checking
        base_test.assert_error_response(response, 404)
        
        # Verify error response structure
        error_data = response.json()
        assert "error" in error_data or "detail" in error_data
```

### 2. Use Framework Error Assertion Methods

✅ **Do: Use framework error assertion methods**
```python
# Good: Uses framework method
base_test.assert_error_response(response, 422, "validation_error")
base_test.assert_status_code(response, 201, "Creating pet")
```

❌ **Don't: Write custom error assertions**
```python
# Bad: Custom error checking
assert response.status_code == 422
error_data = response.json()
assert "error" in error_data
# This doesn't provide consistent error checking
```

### 3. Handle Feature Unavailability Gracefully

✅ **Do: Use framework feature detection**
```python
@parametrize_versions()
async def test_health_records(self, api_version: str, base_test: BaseVersionTest, skip_if_feature_unavailable):
    # Good: Automatic feature detection and skipping
    skip_if_feature_unavailable("health_records")
    
    # Test only runs if feature is available
    # ...test logic...
```

❌ **Don't: Hardcode version checks**
```python
async def test_health_records(self, api_version: str, base_test: BaseVersionTest):
    # Bad: Hardcoded version checking
    if api_version == "v1":
        pytest.skip("Health records not available in v1")
    
    # This doesn't scale with new versions
```

## Performance Considerations

### 1. Minimize Test Data Creation

✅ **Do: Reuse test data when possible**
```python
@pytest.fixture(scope="class")
async def shared_test_user(api_version, base_test, async_client):
    """Create a shared test user for the test class."""
    user = await base_test.create_test_resource(
        async_client, api_version, "user",
        email="shared@example.com"
    )
    yield user
    await base_test.cleanup_test_resource(async_client, api_version, "user", user["id"])

@parametrize_versions()
class TestPetOperations:
    async def test_create_pet_for_user(self, api_version: str, base_test: BaseVersionTest, 
                                     async_client, shared_test_user):
        # Good: Reuses shared user instead of creating new one
        pet_data = base_test.build_test_data(
            api_version, "pet", "create",
            owner_id=shared_test_user["id"]
        )
        # ...test logic...
```

### 2. Use Parallel Test Execution

✅ **Do: Design tests for parallel execution**
```python
# Good: Tests are independent and can run in parallel
@parametrize_versions()
class TestIndependentOperations:
    async def test_create_pet(self, api_version: str, base_test: BaseVersionTest, async_client):
        # Each test creates its own data
        pet_data = base_test.build_test_data(api_version, "pet", "create", 
                                           name=f"Test Pet {uuid.uuid4()}")
        # ...test logic...
```

❌ **Don't: Create dependencies between tests**
```python
# Bad: Tests depend on each other
class TestDependentOperations:
    shared_pet_id = None
    
    async def test_create_pet(self, ...):
        # Creates pet and stores ID
        TestDependentOperations.shared_pet_id = pet["id"]
    
    async def test_update_pet(self, ...):
        # Depends on previous test
        pet_id = TestDependentOperations.shared_pet_id
        # This breaks parallel execution
```

### 3. Optimize Configuration Loading

✅ **Do: Cache configuration appropriately**
```python
# Good: Framework handles configuration caching
@parametrize_versions()
class TestWithCachedConfig:
    def test_endpoint_building(self, api_version: str, base_test: BaseVersionTest):
        # Configuration is loaded once and cached
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        # Subsequent calls use cached configuration
```

## Maintenance and Evolution

### 1. Plan for New API Versions

✅ **Do: Design tests to accommodate new versions**
```python
# Good: Generic test that works with any version
@parametrize_versions()
async def test_pet_crud_operations(self, api_version: str, base_test: BaseVersionTest, async_client):
    """Test basic CRUD operations work across all versions."""
    # Uses configuration to determine available fields
    pet_data = base_test.build_test_data(api_version, "pet", "create")
    
    # Test logic adapts to version capabilities
    endpoint = base_test.get_endpoint_url(api_version, "pets")
    # ...test logic...
```

### 2. Document Version-Specific Behavior

✅ **Do: Document version differences in tests**
```python
async def test_pet_response_fields(self, api_version: str, base_test: BaseVersionTest):
    """
    Test pet response fields across versions.
    
    v1: Basic fields only (name, species, breed)
    v2: Adds temperament, behavioral_notes, emergency_contact
    v3: Adds microchip_id, ai_behavior_score
    """
    expected_fields = base_test.config_manager.get_schema_fields(api_version, "pet_response")
    # ...test logic...
```

### 3. Validate Configuration Changes

✅ **Do: Add configuration validation to CI/CD**
```python
# Good: Automated configuration validation
def test_configuration_validity():
    """Validate that configuration is consistent and complete."""
    config_manager = get_config_manager()
    
    # Validate all versions have required sections
    for version in config_manager.get_supported_versions():
        config = config_manager.get_version_config(version)
        assert "features" in config
        assert "endpoints" in config
        assert "schema_fields" in config
```

## Common Anti-Patterns

### 1. Version-Specific Test Classes

❌ **Avoid: Separate test classes per version**
```python
# Bad: Duplicated test logic
class TestV1Pets:
    def test_create_pet(self): pass
    def test_update_pet(self): pass

class TestV2Pets:
    def test_create_pet(self): pass
    def test_update_pet(self): pass
    def test_health_records(self): pass  # Only difference
```

✅ **Use: Single test class with version parameterization**
```python
# Good: Single test class with version awareness
@parametrize_versions()
class TestPets:
    async def test_create_pet(self, api_version: str, ...): pass
    async def test_update_pet(self, api_version: str, ...): pass

@parametrize_feature_versions("health_records")
class TestHealthRecords:
    async def test_health_records(self, api_version: str, ...): pass
```

### 2. Hardcoded Version Logic

❌ **Avoid: Hardcoded if/else version logic**
```python
# Bad: Hardcoded version checks
def test_pet_fields(self, api_version: str):
    if api_version == "v1":
        # v1 logic
    elif api_version == "v2":
        # v2 logic
    elif api_version == "v3":
        # v3 logic
    # This becomes unmaintainable
```

✅ **Use: Configuration-driven logic**
```python
# Good: Configuration-driven approach
def test_pet_fields(self, api_version: str, base_test: BaseVersionTest):
    expected_fields = base_test.config_manager.get_schema_fields(api_version, "pet_response")
    # Logic adapts automatically to any version
```

### 3. Ignoring Feature Availability

❌ **Avoid: Testing features without checking availability**
```python
# Bad: Assumes feature exists
async def test_health_records(self, api_version: str, ...):
    # This will fail on v1 which doesn't have health records
    endpoint = f"/api/{api_version}/pets/123/health-records"
    # ...test logic...
```

✅ **Use: Feature detection**
```python
# Good: Checks feature availability
@parametrize_feature_versions("health_records")
async def test_health_records(self, api_version: str, ...):
    # Only runs on versions that support health records
    endpoint = base_test.get_endpoint_url(api_version, "health_records", pet_id="123")
    # ...test logic...
```

## Testing Strategies

### 1. Layered Testing Approach

```python
# Layer 1: Basic functionality across all versions
@parametrize_versions()
class TestBasicPetOperations:
    async def test_create_pet(self, ...): pass
    async def test_read_pet(self, ...): pass
    async def test_update_pet(self, ...): pass
    async def test_delete_pet(self, ...): pass

# Layer 2: Feature-specific testing
@parametrize_feature_versions("health_records")
class TestHealthRecords:
    async def test_health_record_crud(self, ...): pass

# Layer 3: Integration and workflow testing
@parametrize_versions()
class TestPetWorkflows:
    async def test_complete_pet_lifecycle(self, ...): pass
```

### 2. Data-Driven Testing

```python
@parametrize_versions()
class TestPetValidation:
    @pytest.mark.parametrize("invalid_data,expected_error", [
        ({"name": ""}, "name_required"),
        ({"species": "invalid"}, "invalid_species"),
        ({"weight": -1}, "invalid_weight"),
    ])
    async def test_pet_validation_errors(self, api_version: str, base_test: BaseVersionTest, 
                                       async_client, invalid_data, expected_error):
        """Test various validation scenarios."""
        pet_data = base_test.build_test_data(api_version, "pet", "create")
        pet_data.update(invalid_data)
        
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        response = await base_test.make_request("POST", endpoint, async_client, json=pet_data)
        
        base_test.assert_error_response(response, 422)
        # Additional validation based on expected_error
```

### 3. Boundary Testing

```python
@parametrize_versions()
class TestPetBoundaries:
    async def test_pet_name_length_limits(self, api_version: str, base_test: BaseVersionTest, async_client):
        """Test pet name length boundaries."""
        # Test maximum allowed length
        max_length = 100  # Could be configured per version
        long_name = "x" * max_length
        
        pet_data = base_test.build_test_data(api_version, "pet", "create", name=long_name)
        endpoint = base_test.get_endpoint_url(api_version, "pets")
        
        response = await base_test.make_request("POST", endpoint, async_client, json=pet_data)
        base_test.assert_status_code(response, 201, "Creating pet with max length name")
        
        # Test over maximum length
        too_long_name = "x" * (max_length + 1)
        pet_data["name"] = too_long_name
        
        response = await base_test.make_request("POST", endpoint, async_client, json=pet_data)
        base_test.assert_error_response(response, 422)
```

By following these best practices, you'll create maintainable, scalable tests that work effectively across multiple API versions while being easy to understand and modify as your API evolves.