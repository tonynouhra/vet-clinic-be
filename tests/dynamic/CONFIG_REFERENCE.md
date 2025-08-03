# Configuration Reference

This document provides a comprehensive reference for configuring the dynamic API testing framework.

## Configuration File Structure

The main configuration file is located at `tests/config/version_config.yaml` and follows this structure:

```yaml
versions:
  v1:
    base_url: "/api/v1"
    features:
      feature_name: boolean
    endpoints:
      resource_name: "endpoint_url"
    schema_fields:
      schema_name: ["field1", "field2"]
    required_fields:
      schema_name: ["required_field1"]
    optional_fields:
      schema_name: ["optional_field1"]
    default_values:
      schema_name:
        field_name: default_value
```

## Configuration Sections

### Version Definition

Each API version must be defined as a top-level key under `versions`:

```yaml
versions:
  v1:
    # v1 configuration
  v2:
    # v2 configuration
  v3:
    # v3 configuration (future)
```

**Requirements:**
- Version names should follow semantic versioning (v1, v2, v3, etc.)
- Each version must include all required sections
- Version names are case-sensitive

### Base URL

Defines the base URL path for the API version:

```yaml
versions:
  v1:
    base_url: "/api/v1"
  v2:
    base_url: "/api/v2"
```

**Usage:**
- Used by `get_endpoint_url()` to build complete endpoint URLs
- Should include the version identifier
- Must start with `/` for absolute paths

### Features

Boolean flags indicating feature availability in each version:

```yaml
versions:
  v1:
    features:
      health_records: false
      statistics: false
      enhanced_filtering: false
      batch_operations: false
      export_data: false
  v2:
    features:
      health_records: true
      statistics: true
      enhanced_filtering: true
      batch_operations: true
      export_data: false
```

**Feature Types:**
- **health_records**: Health record management endpoints
- **statistics**: Pet statistics and analytics endpoints
- **enhanced_filtering**: Advanced filtering and sorting options
- **batch_operations**: Batch update/delete operations
- **export_data**: Data export functionality

**Usage:**
- Controls which tests run for each version
- Used by `@feature_test` decorator
- Checked by `should_test_feature()` method

### Endpoints

Maps resource names to their endpoint URLs:

```yaml
versions:
  v1:
    endpoints:
      pets: "/api/v1/pets"
      users: "/api/v1/users"
      appointments: "/api/v1/appointments"
  v2:
    endpoints:
      pets: "/api/v2/pets"
      users: "/api/v2/users"
      appointments: "/api/v2/appointments"
      health_records: "/api/v2/pets/{pet_id}/health-records"
      statistics: "/api/v2/statistics"
```

**URL Templates:**
- Use `{parameter_name}` for URL parameters
- Parameters are replaced when building URLs
- Common parameters: `{pet_id}`, `{user_id}`, `{appointment_id}`

**Example Usage:**
```python
# Basic endpoint
pets_url = base_test.get_endpoint_url("v2", "pets")
# Result: "/api/v2/pets"

# Parameterized endpoint
health_url = base_test.get_endpoint_url("v2", "health_records", pet_id="123")
# Result: "/api/v2/pets/123/health-records"
```

### Schema Fields

Defines which fields are available for each operation and resource:

```yaml
versions:
  v1:
    schema_fields:
      pet_create: ["name", "species", "breed", "owner_id", "gender", "weight"]
      pet_response: ["id", "name", "species", "breed", "owner_id", "created_at", "updated_at"]
      pet_update: ["name", "breed", "weight"]
      user_create: ["email", "first_name", "last_name", "phone"]
      user_response: ["id", "email", "first_name", "last_name", "created_at"]
  v2:
    schema_fields:
      pet_create: ["name", "species", "breed", "owner_id", "gender", "weight", "temperament", "behavioral_notes", "emergency_contact"]
      pet_response: ["id", "name", "species", "breed", "owner_id", "temperament", "behavioral_notes", "additional_photos", "created_at", "updated_at"]
      pet_update: ["name", "breed", "weight", "temperament", "behavioral_notes"]
      user_create: ["email", "first_name", "last_name", "phone", "address", "emergency_contact"]
      user_response: ["id", "email", "first_name", "last_name", "phone", "address", "created_at", "updated_at"]
```

**Schema Naming Convention:**
- `{resource}_{operation}`: e.g., `pet_create`, `user_response`
- **create**: Fields available for POST requests
- **response**: Fields expected in response objects
- **update**: Fields available for PUT/PATCH requests
- **list**: Fields in list/collection responses

### Required Fields

Specifies which fields are required for each operation:

```yaml
versions:
  v1:
    required_fields:
      pet_create: ["name", "species", "owner_id"]
      user_create: ["email", "first_name", "last_name"]
  v2:
    required_fields:
      pet_create: ["name", "species", "owner_id"]
      user_create: ["email", "first_name", "last_name"]
```

**Usage:**
- Used by `get_required_fields()` method
- Validates test data completeness
- Ensures minimum required data is provided

### Optional Fields

Specifies which fields are optional for each operation:

```yaml
versions:
  v1:
    optional_fields:
      pet_create: ["breed", "gender", "weight"]
      user_create: ["phone"]
  v2:
    optional_fields:
      pet_create: ["breed", "gender", "weight", "temperament", "behavioral_notes", "emergency_contact"]
      user_create: ["phone", "address", "emergency_contact"]
```

**Usage:**
- Used by `get_optional_fields()` method
- Helps generate realistic test data
- Documents API flexibility

### Default Values

Provides default values for test data generation:

```yaml
versions:
  v1:
    default_values:
      pet_create:
        name: "Test Pet"
        species: "dog"
        breed: "mixed"
        gender: "unknown"
        weight: 10.5
        owner_id: 1
      user_create:
        email: "test@example.com"
        first_name: "Test"
        last_name: "User"
        phone: "555-0123"
  v2:
    default_values:
      pet_create:
        name: "Test Pet"
        species: "dog"
        breed: "mixed"
        gender: "unknown"
        weight: 10.5
        temperament: "friendly"
        behavioral_notes: "Well-behaved pet"
        emergency_contact: "555-0199"
        owner_id: 1
      user_create:
        email: "test@example.com"
        first_name: "Test"
        last_name: "User"
        phone: "555-0123"
        address: "123 Test St"
        emergency_contact: "555-0199"
```

**Usage:**
- Used by `build_test_data()` method
- Provides realistic default values
- Can be overridden in individual tests

## Configuration Examples

### Adding a New Version

To add v3 with new features:

```yaml
versions:
  # ... existing versions ...
  v3:
    base_url: "/api/v3"
    features:
      health_records: true
      statistics: true
      enhanced_filtering: true
      batch_operations: true
      export_data: true        # New feature
      ai_recommendations: true # New feature
    endpoints:
      pets: "/api/v3/pets"
      users: "/api/v3/users"
      appointments: "/api/v3/appointments"
      health_records: "/api/v3/pets/{pet_id}/health-records"
      statistics: "/api/v3/statistics"
      exports: "/api/v3/exports"           # New endpoint
      recommendations: "/api/v3/pets/{pet_id}/recommendations" # New endpoint
    schema_fields:
      pet_create: ["name", "species", "breed", "owner_id", "gender", "weight", "temperament", "behavioral_notes", "emergency_contact", "microchip_id"] # New field
      pet_response: ["id", "name", "species", "breed", "owner_id", "temperament", "behavioral_notes", "additional_photos", "microchip_id", "ai_score", "created_at", "updated_at"] # New fields
    required_fields:
      pet_create: ["name", "species", "owner_id"]
    optional_fields:
      pet_create: ["breed", "gender", "weight", "temperament", "behavioral_notes", "emergency_contact", "microchip_id"]
    default_values:
      pet_create:
        name: "Test Pet"
        species: "dog"
        breed: "mixed"
        gender: "unknown"
        weight: 10.5
        temperament: "friendly"
        behavioral_notes: "Well-behaved pet"
        emergency_contact: "555-0199"
        microchip_id: "123456789012345"
        owner_id: 1
```

### Feature Evolution Example

Showing how features evolve across versions:

```yaml
versions:
  v1:
    features:
      basic_crud: true
      user_management: true
      appointment_scheduling: true
      # Advanced features not available
      health_records: false
      statistics: false
      enhanced_filtering: false
      batch_operations: false
      
  v2:
    features:
      # All v1 features remain
      basic_crud: true
      user_management: true
      appointment_scheduling: true
      # New features added
      health_records: true
      statistics: true
      enhanced_filtering: true
      batch_operations: true
      
  v3:
    features:
      # All v2 features remain
      basic_crud: true
      user_management: true
      appointment_scheduling: true
      health_records: true
      statistics: true
      enhanced_filtering: true
      batch_operations: true
      # Next generation features
      ai_recommendations: true
      export_data: true
      real_time_notifications: true
```

### Complex Endpoint Configuration

For endpoints with multiple parameters:

```yaml
versions:
  v2:
    endpoints:
      # Simple endpoints
      pets: "/api/v2/pets"
      users: "/api/v2/users"
      
      # Nested resource endpoints
      health_records: "/api/v2/pets/{pet_id}/health-records"
      appointments: "/api/v2/users/{user_id}/appointments"
      
      # Complex endpoints with multiple parameters
      appointment_history: "/api/v2/users/{user_id}/pets/{pet_id}/appointments"
      health_record_details: "/api/v2/pets/{pet_id}/health-records/{record_id}"
      
      # Query-based endpoints
      statistics: "/api/v2/statistics"
      search: "/api/v2/search"
```

## Configuration Validation

### Automatic Validation

The framework automatically validates configuration on startup:

```python
from tests.dynamic.config_manager import get_config_manager

config_manager = get_config_manager()
# Validation happens automatically during initialization
```

### Manual Validation

You can manually validate configuration:

```python
from tests.dynamic.config_manager import validate_configuration

validation_result = validate_configuration("tests/config/version_config.yaml")
if not validation_result["valid"]:
    print("Configuration errors:", validation_result["errors"])
    print("Configuration warnings:", validation_result["warnings"])
```

### Common Validation Errors

1. **Missing required sections**
   ```
   Error: Version 'v2' missing required section 'features'
   ```

2. **Invalid endpoint URLs**
   ```
   Error: Endpoint URL '/api/v1/pets/{invalid-param}' contains invalid parameter format
   ```

3. **Schema field inconsistencies**
   ```
   Warning: Field 'temperament' in pet_create but not in pet_response for v2
   ```

4. **Feature dependency violations**
   ```
   Error: Feature 'health_records' requires 'enhanced_filtering' but it's disabled in v2
   ```

## Configuration Best Practices

### 1. Maintain Backward Compatibility

When adding new versions:
- Keep existing version configurations unchanged
- Add new features as `false` by default in older versions
- Ensure new fields are optional

### 2. Use Consistent Naming

- Feature names: `snake_case` (e.g., `health_records`, `batch_operations`)
- Schema names: `{resource}_{operation}` (e.g., `pet_create`, `user_response`)
- Endpoint names: `snake_case` matching resource names

### 3. Document Breaking Changes

```yaml
# Version v3 introduces breaking changes:
# - Removed 'gender' field from pet_create (use 'sex' instead)
# - Changed 'phone' field format to international format
# - Renamed 'behavioral_notes' to 'behavior_notes'
v3:
  schema_fields:
    pet_create: ["name", "species", "breed", "owner_id", "sex", "weight"] # 'gender' -> 'sex'
```

### 4. Group Related Features

```yaml
features:
  # Basic CRUD operations
  basic_crud: true
  
  # User management features
  user_authentication: true
  user_profiles: true
  user_permissions: false
  
  # Pet management features
  pet_health_records: true
  pet_statistics: true
  pet_photos: true
  
  # Advanced features
  batch_operations: false
  data_export: false
  api_webhooks: false
```

### 5. Use Environment-Specific Configurations

For different environments, you can override configurations:

```yaml
# tests/config/version_config.yaml (base configuration)
versions:
  v1:
    base_url: "/api/v1"
    
# tests/config/version_config.staging.yaml (staging overrides)
versions:
  v1:
    base_url: "https://staging-api.example.com/api/v1"
    
# tests/config/version_config.production.yaml (production overrides)
versions:
  v1:
    base_url: "https://api.example.com/api/v1"
```

## Configuration Migration

### Migrating from Hardcoded Tests

1. **Identify version differences in existing tests**
2. **Extract differences to configuration**
3. **Update tests to use configuration**

Example migration:

**Before (hardcoded):**
```python
def test_pet_fields(api_version):
    if api_version == "v1":
        expected_fields = ["name", "species", "breed"]
    elif api_version == "v2":
        expected_fields = ["name", "species", "breed", "temperament"]
```

**After (configuration-driven):**
```python
def test_pet_fields(api_version, base_test):
    expected_fields = base_test.config_manager.get_schema_fields(api_version, "pet_response")
```

**Configuration:**
```yaml
versions:
  v1:
    schema_fields:
      pet_response: ["name", "species", "breed"]
  v2:
    schema_fields:
      pet_response: ["name", "species", "breed", "temperament"]
```

## Troubleshooting Configuration

### Debug Configuration Loading

```python
import yaml
from tests.dynamic.config_manager import get_config_manager

# Check raw configuration file
with open("tests/config/version_config.yaml") as f:
    raw_config = yaml.safe_load(f)
    print("Raw configuration:", raw_config)

# Check processed configuration
config_manager = get_config_manager()
for version in config_manager.get_supported_versions():
    print(f"\n{version} configuration:")
    config = config_manager.get_version_config(version)
    print(f"  Features: {config.get('features', {})}")
    print(f"  Endpoints: {config.get('endpoints', {})}")
```

### Common Configuration Issues

1. **YAML syntax errors**
   - Use proper indentation (2 spaces)
   - Quote strings with special characters
   - Validate YAML syntax online

2. **Missing configuration sections**
   - Ensure all versions have required sections
   - Check for typos in section names

3. **Inconsistent field definitions**
   - Verify schema fields match actual API responses
   - Keep required/optional field lists in sync

4. **Feature flag mismatches**
   - Ensure feature flags reflect actual API capabilities
   - Update flags when API features change

For more help, see the [Troubleshooting Guide](TROUBLESHOOTING.md).