# Dynamic API Testing Configuration

This directory contains configuration files for the dynamic API testing framework.

## Overview

The dynamic testing framework uses external configuration files to define version-specific behaviors, eliminating the need for hardcoded version logic in test files.

## Configuration Files

### version_config.yaml

The main configuration file that defines API version specifications:

```yaml
versions:
  v1:
    base_url: "/api/v1"
    features:
      health_records: false
      statistics: false
      enhanced_filtering: false
      batch_operations: false
    endpoints:
      pets: "/api/v1/pets"
      users: "/api/v1/users"
      appointments: "/api/v1/appointments"
    schema_fields:
      pet_create: ["name", "species", "breed", "owner_id", "gender", "weight"]
      pet_response: ["id", "name", "species", "breed", "owner_id", "created_at"]
  v2:
    base_url: "/api/v2"
    features:
      health_records: true
      statistics: true
      enhanced_filtering: true
      batch_operations: true
    endpoints:
      pets: "/api/v2/pets"
      users: "/api/v2/users"
      appointments: "/api/v2/appointments"
    schema_fields:
      pet_create: ["name", "species", "breed", "owner_id", "gender", "weight", "temperament", "emergency_contact"]
      pet_response: ["id", "name", "species", "breed", "owner_id", "temperament", "additional_photos", "created_at"]
```

## Configuration Structure

### Version Definition

Each API version must include:

- **base_url**: The base URL path for the API version
- **features**: Boolean flags for feature availability
- **endpoints**: Mapping of resource names to endpoint URLs
- **schema_fields**: Field definitions for request/response schemas

### Feature Flags

Feature flags control which tests run for each version:

- `health_records`: Health record management endpoints
- `statistics`: Pet statistics and analytics endpoints  
- `enhanced_filtering`: Advanced filtering and sorting options
- `batch_operations`: Batch update/delete operations

### Schema Fields

Schema field definitions specify which fields are available for each operation:

- `{resource}_create`: Fields available for creation requests
- `{resource}_response`: Fields expected in response objects
- `{resource}_update`: Fields available for update requests

## Adding New Versions

To add a new API version (e.g., v3):

1. Add a new version entry to `version_config.yaml`:

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
      new_feature: true  # New feature in v3
    endpoints:
      pets: "/api/v3/pets"
      users: "/api/v3/users"
      appointments: "/api/v3/appointments"
    schema_fields:
      pet_create: ["name", "species", "breed", "owner_id", "gender", "weight", "temperament", "emergency_contact", "new_field"]
      pet_response: ["id", "name", "species", "breed", "owner_id", "temperament", "additional_photos", "created_at", "new_field"]
```

2. Tests will automatically include the new version without code changes

3. Add feature-specific tests for new features:

```python
@feature_test("new_feature")
async def test_new_feature(self, api_version: str, ...):
    # Test will only run on versions supporting new_feature
    pass
```

## Configuration Validation

The CI/CD pipeline automatically validates configuration files:

- **Structure validation**: Ensures required keys are present
- **Endpoint validation**: Verifies all required endpoints are defined
- **Feature consistency**: Checks feature flag consistency
- **Schema validation**: Validates schema field definitions

## Best Practices

### 1. Backward Compatibility

When adding new versions:
- Keep existing version configurations unchanged
- Add new features as optional with default `false` values
- Ensure new fields are optional in schemas

### 2. Feature Naming

Use descriptive feature names:
- `health_records` instead of `hr`
- `enhanced_filtering` instead of `filter_v2`
- `batch_operations` instead of `batch`

### 3. Schema Evolution

When evolving schemas:
- Add new fields to the end of field lists
- Mark breaking changes clearly in comments
- Document field deprecations

### 4. Testing New Configurations

Before deploying configuration changes:

```bash
# Validate configuration syntax
python -c "
import yaml
with open('tests/config/version_config.yaml') as f:
    config = yaml.safe_load(f)
print('✓ Configuration is valid YAML')
"

# Test framework integration
python -c "
from tests.dynamic.config_manager import get_config_manager
config_manager = get_config_manager()
versions = config_manager.get_supported_versions()
print(f'✓ Supported versions: {versions}')
"

# Run dynamic tests
pytest tests/integration/test_pets_dynamic_migrated.py -v
```

## Troubleshooting

### Common Issues

1. **YAML Syntax Errors**
   - Use proper indentation (2 spaces)
   - Quote string values containing special characters
   - Validate YAML syntax before committing

2. **Missing Required Keys**
   - Ensure all versions have `base_url`, `features`, `endpoints`
   - Include all required endpoints for each version
   - Define schema fields for all operations

3. **Feature Flag Inconsistencies**
   - Ensure feature flags match actual API capabilities
   - Update tests when feature availability changes
   - Document feature dependencies

4. **Schema Mismatches**
   - Keep schema fields in sync with actual API responses
   - Test schema changes against real API responses
   - Update field lists when API schemas evolve

### Debugging Configuration Issues

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from tests.dynamic.config_manager import get_config_manager
config_manager = get_config_manager()
# Debug output will show configuration loading details
```

Check configuration loading:

```python
from tests.dynamic.config_manager import get_config_manager

config_manager = get_config_manager()
print("Supported versions:", config_manager.get_supported_versions())

for version in config_manager.get_supported_versions():
    print(f"\n{version} configuration:")
    print("  Features:", config_manager.get_features_for_version(version))
    print("  Endpoints:", config_manager.get_version_config(version)['endpoints'])
```

## Migration Guide

When migrating from version-specific tests to dynamic tests:

1. **Identify Common Patterns**: Extract shared test logic
2. **Map Version Differences**: Document what differs between versions
3. **Create Configuration**: Define version-specific behaviors in config
4. **Convert Tests**: Use dynamic decorators and utilities
5. **Validate Coverage**: Ensure equivalent test coverage

See `tests/integration/MIGRATION_SUMMARY.md` for a complete migration example.

## Support

For questions about dynamic testing configuration:

1. Check existing configuration examples
2. Review test migration documentation
3. Run configuration validation tools
4. Consult the dynamic testing framework documentation