# Dynamic Testing Framework Migration Guide

## Overview

This guide provides step-by-step instructions for migrating existing version-specific tests to the dynamic testing framework. The migration process eliminates code duplication while maintaining full test coverage and improving maintainability.

## Migration Process

### Step 1: Analyze Existing Tests

Before starting migration, analyze your existing test files to understand:

1. **Test Coverage**: What functionality is being tested
2. **Version Differences**: How tests differ between versions
3. **Common Patterns**: Shared logic that can be abstracted
4. **Version-Specific Features**: Features only available in certain versions

#### Example Analysis

```bash
# Identify test files to migrate
find tests/ -name "*v1*" -o -name "*v2*" | grep -E "\.(py)$"

# Count test methods per file
grep -c "def test_" tests/integration/test_v1_pet_endpoints.py
grep -c "def test_" tests/integration/test_v2_pet_endpoints.py
```

### Step 2: Set Up Dynamic Test Structure

Create your new dynamic test file with the proper structure:

```python
# tests/integration/test_resource_dynamic.py
import pytest
from tests.dynamic.base_test import BaseVersionTest
from tests.dynamic.decorators import version_parametrize, feature_test


class TestResourceDynamic(BaseVersionTest):
    """Dynamic tests for resource endpoints across API versions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        # Add any resource-specific setup
```

### Step 3: Migrate Common CRUD Operations

Start with basic CRUD operations that work across all versions:

#### Before (Version-Specific)
```python
# test_v1_pets.py
async def test_create_pet_v1(self, async_client, mock_user):
    pet_data = {
        "name": "Buddy",
        "species": "dog",
        "breed": "Golden Retriever",
        "owner_id": mock_user.id
    }
    response = await async_client.post("/api/v1/pets", json=pet_data)
    assert response.status_code == 201

# test_v2_pets.py  
async def test_create_pet_v2(self, async_client, mock_user):
    pet_data = {
        "name": "Buddy",
        "species": "dog", 
        "breed": "Golden Retriever",
        "owner_id": mock_user.id,
        "temperament": "friendly",
        "emergency_contact": "555-0123"
    }
    response = await async_client.post("/api/v2/pets", json=pet_data)
    assert response.status_code == 201
```

#### After (Dynamic)
```python
@version_parametrize()
async def test_create_pet_success(
    self, 
    api_version: str,
    async_client,
    mock_user,
    test_data_factory
):
    """Test successful pet creation across all API versions."""
    # Generate version-appropriate data
    pet_data = test_data_factory.build_pet_data(api_version, owner_id=mock_user.id)
    
    # Make request to version-specific endpoint
    url = self.get_endpoint_url(api_version, "pets")
    response = await async_client.post(url, json=pet_data)
    
    # Validate response
    assert response.status_code == 201
    pet_response = response.json()
    
    # Version-aware response validation
    self.validate_response_structure(pet_response, api_version, "pet", "response")
    assert pet_response["name"] == pet_data["name"]
```

### Step 4: Handle Version-Specific Features

Migrate features that only exist in certain versions:

#### Before (Manual Version Checking)
```python
# test_v2_pets.py
async def test_get_pet_statistics(self, async_client):
    # This test only exists in v2 file
    response = await async_client.get("/api/v2/pets/statistics")
    assert response.status_code == 200
```

#### After (Feature Detection)
```python
@feature_test("statistics")
async def test_get_pet_statistics(
    self,
    api_version: str,
    async_client
):
    """Test pet statistics endpoint (v2+ only)."""
    url = self.get_endpoint_url(api_version, "pets", "statistics")
    response = await async_client.get(url)
    
    assert response.status_code == 200
    stats = response.json()
    
    # Validate statistics structure
    expected_fields = ["total_pets", "by_species", "by_breed"]
    for field in expected_fields:
        assert field in stats
```

### Step 5: Migrate Error Handling Tests

Convert error handling tests to work across versions:

```python
@version_parametrize()
async def test_create_pet_validation_error(
    self,
    api_version: str,
    async_client,
    test_data_factory
):
    """Test validation errors are consistent across versions."""
    # Create invalid data (missing required fields)
    invalid_data = test_data_factory.build_pet_data(api_version)
    del invalid_data["name"]  # Remove required field
    
    url = self.get_endpoint_url(api_version, "pets")
    response = await async_client.post(url, json=invalid_data)
    
    assert response.status_code == 422
    error_response = response.json()
    
    # Validate error structure is consistent
    assert "detail" in error_response
    assert any("name" in str(error) for error in error_response["detail"])
```

### Step 6: Update Configuration

Ensure your version configuration supports the migrated tests:

```yaml
# tests/config/version_config.yaml
versions:
  v1:
    features:
      statistics: false
      health_records: false
    schema_fields:
      pet_create: ["name", "species", "breed", "owner_id"]
      pet_response: ["id", "name", "species", "breed", "owner_id", "created_at"]
  v2:
    features:
      statistics: true
      health_records: true
    schema_fields:
      pet_create: ["name", "species", "breed", "owner_id", "temperament", "emergency_contact"]
      pet_response: ["id", "name", "species", "breed", "owner_id", "temperament", "created_at"]
```

### Step 7: Validate Migration

Run comprehensive validation to ensure migration success:

```bash
# Run the new dynamic tests
pytest tests/integration/test_pets_dynamic.py -v

# Compare coverage with original tests
pytest --cov=app tests/integration/test_v1_pet_endpoints.py tests/integration/test_v2_pet_endpoints.py
pytest --cov=app tests/integration/test_pets_dynamic.py

# Run both old and new tests to compare results
pytest tests/integration/test_v1_pet_endpoints.py tests/integration/test_v2_pet_endpoints.py tests/integration/test_pets_dynamic.py
```

## Migration Checklist

### Pre-Migration
- [ ] Analyze existing test coverage
- [ ] Identify version-specific features
- [ ] Document test patterns and logic
- [ ] Set up dynamic test file structure

### During Migration
- [ ] Migrate common CRUD operations first
- [ ] Handle version-specific features with decorators
- [ ] Update test data generation
- [ ] Maintain error handling patterns
- [ ] Update configuration files

### Post-Migration
- [ ] Run comprehensive test validation
- [ ] Compare test coverage metrics
- [ ] Verify all test scenarios are covered
- [ ] Update CI/CD configuration
- [ ] Remove original test files (after validation)

## Common Migration Patterns

### Pattern 1: Simple CRUD Migration

```python
# Before: Separate files for each version
# After: Single parameterized test

@version_parametrize()
async def test_crud_operation(self, api_version, ...):
    # Version-aware implementation
```

### Pattern 2: Feature-Specific Migration

```python
# Before: Tests only in v2 file
# After: Feature-gated test

@feature_test("feature_name")
async def test_feature_specific(self, api_version, ...):
    # Feature implementation
```

### Pattern 3: Data Generation Migration

```python
# Before: Hardcoded version-specific data
# After: Dynamic data generation

pet_data = test_data_factory.build_pet_data(api_version, **overrides)
```

### Pattern 4: Response Validation Migration

```python
# Before: Manual field checking
# After: Automatic validation

self.validate_response_structure(response, api_version, "resource", "type")
```

## Best Practices

### 1. Start Small
- Begin with simple CRUD operations
- Migrate one resource at a time
- Validate each migration step

### 2. Maintain Test Quality
- Preserve all original test logic
- Enhance error messages with version context
- Add comprehensive assertions

### 3. Use Configuration Effectively
- Externalize version differences
- Keep test code version-agnostic
- Document configuration changes

### 4. Validate Thoroughly
- Run both old and new tests during transition
- Compare coverage metrics
- Test edge cases and error scenarios

## Migration Examples

See the following files for complete migration examples:

- `tests/integration/test_pets_dynamic_migrated.py` - Complete pet endpoints migration
- `tests/integration/MIGRATION_SUMMARY.md` - Detailed migration results
- `tests/dynamic/example_test.py` - Simple migration example

## Next Steps

After successful migration:

1. **Remove Original Files**: Delete version-specific test files
2. **Update Documentation**: Update testing guides and references
3. **Share Knowledge**: Document lessons learned for future migrations
4. **Monitor Performance**: Track test execution time and reliability

## Getting Help

If you encounter issues during migration:

1. Check the troubleshooting guide: `tests/dynamic/TROUBLESHOOTING.md`
2. Review common scenarios: `tests/dynamic/COMMON_SCENARIOS.md`
3. Examine working examples in the codebase
4. Consult the configuration reference: `tests/dynamic/CONFIG_REFERENCE.md`