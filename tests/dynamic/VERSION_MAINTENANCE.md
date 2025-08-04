# Version Configuration Maintenance Guide

## Overview

This guide provides procedures for maintaining version configurations in the dynamic testing framework. Proper configuration maintenance ensures tests remain accurate as APIs evolve and new versions are introduced.

## Configuration Structure

### Core Configuration Files

```
tests/config/
├── version_config.yaml          # Main version configuration
├── test_data_templates.yaml     # Data generation templates
├── feature_matrix.yaml          # Feature availability matrix
└── validation_schemas/          # JSON schemas for validation
    ├── v1/
    │   ├── pet_create.json
    │   ├── pet_response.json
    │   └── user_response.json
    └── v2/
        ├── pet_create.json
        ├── pet_response.json
        └── user_response.json
```

### Configuration Schema

```yaml
# tests/config/version_config.yaml
versions:
  v1:
    base_url: "/api/v1"
    deprecated: false
    sunset_date: null
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
      pet_response: ["id", "name", "species", "breed", "owner_id", "created_at", "updated_at"]
      pet_update: ["name", "breed", "weight"]
    required_fields:
      pet_create: ["name", "species", "owner_id"]
    optional_fields:
      pet_create: ["breed", "gender", "weight"]
    default_values:
      pet_create:
        species: "dog"
        gender: "unknown"
```

## Adding New API Versions

### Step 1: Analyze New Version

Before adding a new version, analyze the API changes:

```bash
# Compare API endpoints
curl -s http://localhost:8000/api/v2/pets/1 > v2_response.json
curl -s http://localhost:8000/api/v3/pets/1 > v3_response.json
diff v2_response.json v3_response.json

# Document new features
echo "New features in v3:" > v3_features.md
echo "- Enhanced search capabilities" >> v3_features.md
echo "- Bulk operations" >> v3_features.md
echo "- Advanced filtering" >> v3_features.md
```

### Step 2: Update Configuration

Add the new version to `version_config.yaml`:

```yaml
versions:
  # ... existing versions ...
  v3:
    base_url: "/api/v3"
    deprecated: false
    sunset_date: null
    features:
      health_records: true
      statistics: true
      enhanced_filtering: true
      batch_operations: true
      advanced_search: true        # New feature
      bulk_operations: true        # New feature
    endpoints:
      pets: "/api/v3/pets"
      users: "/api/v3/users"
      appointments: "/api/v3/appointments"
      search: "/api/v3/search"     # New endpoint
    schema_fields:
      pet_create: [
        "name", "species", "breed", "owner_id", "gender", "weight",
        "temperament", "emergency_contact", "microchip_id",
        "vaccination_status"       # New field
      ]
      pet_response: [
        "id", "name", "species", "breed", "owner_id", "temperament",
        "emergency_contact", "microchip_id", "vaccination_status",
        "health_score", "last_checkup", "created_at", "updated_at"
      ]
    required_fields:
      pet_create: ["name", "species", "owner_id", "microchip_id"]
    optional_fields:
      pet_create: ["breed", "gender", "weight", "temperament", "emergency_contact", "vaccination_status"]
    default_values:
      pet_create:
        species: "dog"
        gender: "unknown"
        vaccination_status: "unknown"
```

### Step 3: Create Validation Schemas

Create JSON schemas for the new version:

```bash
mkdir -p tests/config/validation_schemas/v3
```

```json
// tests/config/validation_schemas/v3/pet_response.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "id": {"type": "integer"},
    "name": {"type": "string"},
    "species": {"type": "string"},
    "breed": {"type": "string"},
    "owner_id": {"type": "integer"},
    "temperament": {"type": "string"},
    "emergency_contact": {"type": "string"},
    "microchip_id": {"type": "string"},
    "vaccination_status": {"type": "string"},
    "health_score": {"type": "number"},
    "last_checkup": {"type": "string", "format": "date-time"},
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"}
  },
  "required": ["id", "name", "species", "owner_id", "microchip_id", "created_at", "updated_at"]
}
```

### Step 4: Update Test Data Templates

Add templates for the new version:

```yaml
# tests/config/test_data_templates.yaml
pet_templates:
  v3:
    base_data:
      name: "Test Pet"
      species: "dog"
      breed: "mixed"
      owner_id: 1
      gender: "male"
      weight: 25.5
      temperament: "friendly"
      emergency_contact: "555-0123"
      microchip_id: "123456789012345"
      vaccination_status: "up_to_date"
    field_generators:
      microchip_id: "generate_microchip_id"
      vaccination_status: "random_vaccination_status"
```

### Step 5: Validate Configuration

Run configuration validation:

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('tests/config/version_config.yaml'))"

# Validate configuration structure
python -m tests.dynamic.config_manager --validate

# Test new version
pytest tests/integration/test_pets_dynamic.py -k "v3" -v
```

## Updating Existing Versions

### Deprecating Features

When features are deprecated:

```yaml
versions:
  v1:
    deprecated: true
    sunset_date: "2024-12-31"
    deprecation_warnings:
      - "Version v1 is deprecated and will be removed on 2024-12-31"
      - "Please migrate to v2 or later"
    features:
      legacy_endpoint: true  # Mark as deprecated but still available
```

### Adding Fields to Existing Versions

When adding optional fields to existing versions:

```yaml
versions:
  v2:
    schema_fields:
      pet_response: [
        # ... existing fields ...
        "additional_notes"  # New optional field
      ]
    optional_fields:
      pet_create: [
        # ... existing optional fields ...
        "additional_notes"
      ]
```

### Removing Fields

When removing fields (breaking change):

```yaml
versions:
  v2:
    breaking_changes:
      - field: "deprecated_field"
        removed_in: "v2.1"
        migration_guide: "Use 'new_field' instead"
    schema_fields:
      pet_response: [
        # Remove deprecated_field from list
        "id", "name", "species"  # ... other fields
      ]
```

## Feature Management

### Adding New Features

When adding new features:

```yaml
# Update feature matrix
versions:
  v2:
    features:
      new_feature: true
  v3:
    features:
      new_feature: true
      enhanced_new_feature: true

# Add feature-specific configuration
feature_configs:
  new_feature:
    endpoints:
      - "/api/{version}/pets/new-feature"
    required_permissions:
      - "pets:read"
      - "pets:new_feature"
    rate_limits:
      requests_per_minute: 100
```

### Feature Flags

Implement feature flags for gradual rollouts:

```yaml
versions:
  v2:
    feature_flags:
      experimental_search: false  # Disabled by default
      beta_analytics: true        # Enabled for testing
    features:
      experimental_search: "{{ feature_flags.experimental_search }}"
      beta_analytics: "{{ feature_flags.beta_analytics }}"
```

## Configuration Validation

### Automated Validation

Create validation scripts:

```python
# scripts/validate_config.py
import yaml
import jsonschema
from pathlib import Path

def validate_version_config():
    """Validate version configuration structure."""
    config_path = Path("tests/config/version_config.yaml")
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Validate required sections
    required_sections = ["versions"]
    for section in required_sections:
        assert section in config, f"Missing required section: {section}"
    
    # Validate each version
    for version, version_config in config["versions"].items():
        validate_version_structure(version, version_config)
    
    print("✅ Configuration validation passed")

def validate_version_structure(version, config):
    """Validate individual version configuration."""
    required_fields = ["base_url", "features", "endpoints", "schema_fields"]
    
    for field in required_fields:
        assert field in config, f"Version {version} missing required field: {field}"
    
    # Validate endpoints are strings
    for endpoint_name, endpoint_url in config["endpoints"].items():
        assert isinstance(endpoint_url, str), f"Endpoint {endpoint_name} must be string"
        assert endpoint_url.startswith("/"), f"Endpoint {endpoint_name} must start with /"

if __name__ == "__main__":
    validate_version_config()
```

### CI/CD Integration

Add validation to CI pipeline:

```yaml
# .github/workflows/config-validation.yml
name: Configuration Validation

on:
  pull_request:
    paths:
      - 'tests/config/**'

jobs:
  validate-config:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install pyyaml jsonschema
      
      - name: Validate configuration
        run: |
          python scripts/validate_config.py
      
      - name: Test configuration loading
        run: |
          python -c "
          from tests.dynamic.config_manager import VersionConfigManager
          config = VersionConfigManager()
          print('Supported versions:', config.get_supported_versions())
          "
```

## Migration Procedures

### Version Sunset Process

When sunsetting an API version:

1. **Announce Deprecation** (6 months before sunset)
```yaml
versions:
  v1:
    deprecated: true
    sunset_date: "2024-06-30"
    deprecation_warnings:
      - "Version v1 will be sunset on 2024-06-30"
      - "Please migrate to v2 by this date"
```

2. **Update Tests** (3 months before sunset)
```python
# Mark tests as deprecated
@pytest.mark.deprecated
@version_parametrize(versions=["v1"])
async def test_v1_specific_feature(self, api_version, ...):
    pytest.skip("v1 is deprecated, test maintained for compatibility only")
```

3. **Remove Configuration** (after sunset)
```bash
# Remove v1 configuration
git rm tests/config/validation_schemas/v1/
# Update version_config.yaml to remove v1 section
```

### Breaking Change Management

When introducing breaking changes:

```yaml
versions:
  v3:
    breaking_changes:
      - change: "pet_id field renamed to id"
        migration: "Update client code to use 'id' instead of 'pet_id'"
        affected_endpoints: ["/api/v3/pets"]
      - change: "removed deprecated_field"
        migration: "Use new_field instead"
        affected_endpoints: ["/api/v3/pets", "/api/v3/users"]
```

## Monitoring and Maintenance

### Configuration Drift Detection

Monitor for configuration drift:

```python
# scripts/detect_config_drift.py
import requests
import yaml
from tests.dynamic.config_manager import VersionConfigManager

def detect_drift():
    """Detect drift between configuration and actual API."""
    config = VersionConfigManager()
    
    for version in config.get_supported_versions():
        version_config = config.get_version_config(version)
        base_url = version_config["base_url"]
        
        # Test actual API endpoints
        for resource, endpoint in version_config["endpoints"].items():
            try:
                response = requests.get(f"http://localhost:8000{endpoint}")
                if response.status_code == 404:
                    print(f"⚠️  Endpoint {endpoint} not found in {version}")
            except requests.RequestException as e:
                print(f"❌ Error testing {endpoint}: {e}")

if __name__ == "__main__":
    detect_drift()
```

### Regular Maintenance Tasks

Create maintenance checklist:

```bash
#!/bin/bash
# scripts/config_maintenance.sh

echo "🔍 Running configuration maintenance..."

# 1. Validate configuration syntax
echo "Validating YAML syntax..."
python -c "import yaml; yaml.safe_load(open('tests/config/version_config.yaml'))"

# 2. Check for unused configurations
echo "Checking for unused configurations..."
grep -r "v1" tests/ | grep -v config | wc -l

# 3. Validate against live API
echo "Testing against live API..."
python scripts/detect_config_drift.py

# 4. Check for deprecated versions
echo "Checking for deprecated versions..."
python -c "
from tests.dynamic.config_manager import VersionConfigManager
config = VersionConfigManager()
for v in config.get_supported_versions():
    vc = config.get_version_config(v)
    if vc.get('deprecated'):
        print(f'⚠️  Version {v} is deprecated (sunset: {vc.get(\"sunset_date\", \"TBD\")})')
"

echo "✅ Maintenance complete"
```

### Documentation Updates

Keep documentation synchronized:

```bash
# scripts/update_docs.sh
#!/bin/bash

echo "📝 Updating documentation..."

# Generate API version matrix
python scripts/generate_version_matrix.py > docs/api/version_matrix.md

# Update configuration reference
python scripts/generate_config_docs.py > tests/dynamic/CONFIG_REFERENCE.md

# Update migration guides
python scripts/update_migration_examples.py

echo "✅ Documentation updated"
```

## Best Practices

### 1. Configuration Management
- Use semantic versioning for API versions
- Maintain backward compatibility when possible
- Document all breaking changes
- Use feature flags for gradual rollouts

### 2. Validation
- Validate configuration on every change
- Test against live APIs regularly
- Use JSON schemas for response validation
- Automate validation in CI/CD

### 3. Documentation
- Keep configuration documentation up-to-date
- Document migration procedures
- Maintain version compatibility matrix
- Provide clear deprecation notices

### 4. Testing
- Test new configurations thoroughly
- Maintain test coverage across all versions
- Use feature flags for experimental features
- Monitor test performance impact

### 5. Monitoring
- Track configuration drift
- Monitor deprecated version usage
- Alert on validation failures
- Regular maintenance reviews

## Troubleshooting Configuration Issues

### Common Problems

1. **YAML Syntax Errors**
```bash
# Validate YAML
python -c "import yaml; yaml.safe_load(open('tests/config/version_config.yaml'))"
```

2. **Missing Required Fields**
```python
# Check required fields
from tests.dynamic.config_manager import VersionConfigManager
config = VersionConfigManager()
config.validate_configuration()
```

3. **Endpoint Mismatches**
```bash
# Test endpoints
curl -I http://localhost:8000/api/v1/pets
curl -I http://localhost:8000/api/v2/pets
```

4. **Schema Validation Failures**
```python
# Debug schema validation
response = {"id": 1, "name": "Test"}
config.validate_response_schema(response, "v1", "pet", "response")
```

By following these maintenance procedures, you can ensure your version configuration remains accurate, up-to-date, and properly validated as your API evolves.