# Dynamic Testing Framework Troubleshooting Guide

## Overview

This guide helps diagnose and resolve common issues when working with the dynamic testing framework. Issues are organized by category with symptoms, causes, and solutions.

## Configuration Issues

### Issue: Configuration File Not Found

**Symptoms:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'tests/config/version_config.yaml'
```

**Causes:**
- Configuration file missing or in wrong location
- Incorrect file path in configuration manager
- File permissions issues

**Solutions:**
```bash
# Check if configuration file exists
ls -la tests/config/version_config.yaml

# Create missing configuration directory
mkdir -p tests/config

# Copy example configuration
cp tests/config/version_config.yaml.example tests/config/version_config.yaml

# Fix file permissions
chmod 644 tests/config/version_config.yaml
```

### Issue: Invalid Configuration Format

**Symptoms:**
```
yaml.scanner.ScannerError: while scanning for the next token
found character '\t' that cannot start any token
```

**Causes:**
- YAML syntax errors (tabs instead of spaces)
- Invalid YAML structure
- Missing required configuration sections

**Solutions:**
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('tests/config/version_config.yaml'))"

# Check for tabs (should use spaces)
grep -P '\t' tests/config/version_config.yaml

# Validate against schema
python -m tests.dynamic.config_manager --validate
```

**Example Fix:**
```yaml
# Wrong (uses tabs)
versions:
	v1:
		base_url: "/api/v1"

# Correct (uses spaces)
versions:
  v1:
    base_url: "/api/v1"
```

### Issue: Missing Version Configuration

**Symptoms:**
```
KeyError: 'v3'
ConfigurationError: Version 'v3' not found in configuration
```

**Causes:**
- Test requesting unsupported version
- Configuration missing version definition
- Typo in version name

**Solutions:**
```python
# Check available versions
from tests.dynamic.config_manager import VersionConfigManager
config = VersionConfigManager()
print(config.get_supported_versions())

# Add missing version to configuration
# tests/config/version_config.yaml
versions:
  v3:
    base_url: "/api/v3"
    features: {}
    endpoints: {}
    schema_fields: {}
```

## Test Execution Issues

### Issue: Tests Skipped Unexpectedly

**Symptoms:**
```
SKIPPED [1] Feature 'health_records' not supported in version 'v1'
```

**Causes:**
- Feature not enabled in version configuration
- Incorrect feature name in decorator
- Missing feature definition

**Solutions:**
```python
# Check feature availability
config = VersionConfigManager()
print(config.get_feature_availability("v1", "health_records"))

# Update configuration to enable feature
# tests/config/version_config.yaml
versions:
  v1:
    features:
      health_records: true  # Enable feature

# Or use correct feature name in test
@feature_test("health_records")  # Ensure name matches config
```

### Issue: Parameterization Not Working

**Symptoms:**
```
TypeError: test_create_pet() missing 1 required positional argument: 'api_version'
```

**Causes:**
- Missing `@version_parametrize()` decorator
- Incorrect fixture parameter names
- Decorator import issues

**Solutions:**
```python
# Add missing decorator
from tests.dynamic.decorators import version_parametrize

@version_parametrize()
async def test_create_pet(self, api_version: str, ...):
    pass

# Check parameter names match fixture
@pytest.fixture(params=["v1", "v2"])
def api_version(request):
    return request.param

# Verify imports
from tests.dynamic.decorators import version_parametrize, feature_test
```

### Issue: Data Factory Errors

**Symptoms:**
```
AttributeError: 'TestDataFactory' object has no attribute 'build_pet_data'
KeyError: 'pet_create' not found in schema_fields for version 'v1'
```

**Causes:**
- Missing schema field definitions
- Incorrect method names
- Data factory not properly initialized

**Solutions:**
```python
# Check schema field configuration
# tests/config/version_config.yaml
versions:
  v1:
    schema_fields:
      pet_create: ["name", "species", "breed", "owner_id"]
      pet_response: ["id", "name", "species", "breed", "created_at"]

# Verify data factory initialization
test_data_factory = TestDataFactory(config_manager)

# Check available methods
print(dir(test_data_factory))
```

## Response Validation Issues

### Issue: Response Structure Validation Fails

**Symptoms:**
```
AssertionError: Expected field 'temperament' not found in v2 response
ValidationError: Response missing required fields for version v2
```

**Causes:**
- Incorrect expected fields configuration
- API response doesn't match configuration
- Version mismatch in validation

**Solutions:**
```python
# Debug response structure
print(f"Actual response: {response.json()}")
print(f"Expected fields: {config.get_schema_fields(api_version, 'pet_response')}")

# Update configuration to match actual API
# tests/config/version_config.yaml
versions:
  v2:
    schema_fields:
      pet_response: ["id", "name", "species", "breed", "temperament", "created_at"]

# Add debugging to validation
def validate_response_structure(self, response, api_version, resource, schema_type):
    expected_fields = self.config.get_schema_fields(api_version, f"{resource}_{schema_type}")
    actual_fields = list(response.keys())
    print(f"Expected: {expected_fields}")
    print(f"Actual: {actual_fields}")
```

### Issue: Version-Specific Field Validation

**Symptoms:**
```
AssertionError: Field 'emergency_contact' should not be present in v1 response
```

**Causes:**
- API returning fields not expected for version
- Configuration doesn't match API behavior
- Test logic error

**Solutions:**
```python
# Check API behavior
curl -X GET "http://localhost:8000/api/v1/pets/1"
curl -X GET "http://localhost:8000/api/v2/pets/1"

# Update configuration to match API
versions:
  v1:
    schema_fields:
      pet_response: ["id", "name", "species", "breed", "created_at"]
  v2:
    schema_fields:
      pet_response: ["id", "name", "species", "breed", "temperament", "emergency_contact", "created_at"]

# Add conditional validation
def validate_version_specific_fields(self, response, api_version, resource):
    if api_version == "v1":
        assert "emergency_contact" not in response
    elif api_version == "v2":
        assert "emergency_contact" in response
```

## Performance Issues

### Issue: Slow Test Execution

**Symptoms:**
- Tests taking significantly longer than version-specific tests
- Timeout errors in CI/CD
- High memory usage

**Causes:**
- Configuration loaded multiple times
- Inefficient data generation
- Too many parameterized combinations

**Solutions:**
```python
# Cache configuration loading
@pytest.fixture(scope="session")
def config_manager():
    return VersionConfigManager()

# Optimize data generation
@lru_cache(maxsize=128)
def generate_base_pet_data():
    return {"name": "Test Pet", "species": "dog"}

# Reduce parameterization scope
@version_parametrize(versions=["v1", "v2"])  # Limit to specific versions
async def test_specific_feature(self, api_version, ...):
    pass

# Use session-scoped fixtures for expensive setup
@pytest.fixture(scope="session")
def test_database():
    # Expensive database setup
    pass
```

### Issue: Memory Leaks

**Symptoms:**
- Memory usage increases during test runs
- Out of memory errors in CI
- Slow garbage collection

**Causes:**
- Fixtures not properly cleaned up
- Large test data not released
- Circular references in test objects

**Solutions:**
```python
# Proper fixture cleanup
@pytest.fixture
def test_data():
    data = create_large_test_data()
    yield data
    # Cleanup
    del data
    gc.collect()

# Use weak references for caches
import weakref
_cache = weakref.WeakValueDictionary()

# Monitor memory usage
import psutil
import os

def test_memory_usage():
    process = psutil.Process(os.getpid())
    print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

## Debugging Techniques

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In test files
import logging
logger = logging.getLogger(__name__)

@version_parametrize()
async def test_with_debug(self, api_version, ...):
    logger.debug(f"Testing version: {api_version}")
    logger.debug(f"Request data: {test_data}")
```

### Use pytest Debug Options

```bash
# Run with verbose output
pytest tests/integration/test_pets_dynamic.py -v -s

# Run specific test with debugging
pytest tests/integration/test_pets_dynamic.py::TestPetsDynamic::test_create_pet_success -v -s

# Show local variables on failure
pytest --tb=long

# Drop into debugger on failure
pytest --pdb

# Show print statements
pytest -s
```

### Configuration Debugging

```python
# Debug configuration loading
from tests.dynamic.config_manager import VersionConfigManager

config = VersionConfigManager()
print("Supported versions:", config.get_supported_versions())
print("V1 features:", config.get_version_config("v1")["features"])
print("V2 endpoints:", config.get_version_config("v2")["endpoints"])

# Validate configuration
config.validate_configuration()
```

### Response Debugging

```python
@version_parametrize()
async def test_with_response_debug(self, api_version, async_client):
    response = await async_client.get(f"/api/{api_version}/pets")
    
    # Debug response
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Body: {response.text}")
    
    if response.status_code != 200:
        print(f"Error response: {response.json()}")
```

## Common Error Patterns

### Pattern 1: Import Errors

```python
# Wrong
from tests.dynamic import BaseVersionTest  # Module not found

# Correct
from tests.dynamic.base_test import BaseVersionTest
```

### Pattern 2: Fixture Scope Issues

```python
# Wrong - scope mismatch
@pytest.fixture(scope="session")
def api_version():  # This should be function-scoped for parameterization
    return "v1"

# Correct
@pytest.fixture(params=["v1", "v2"])
def api_version(request):
    return request.param
```

### Pattern 3: Configuration Path Issues

```python
# Wrong - hardcoded path
config = VersionConfigManager("/absolute/path/to/config.yaml")

# Correct - relative path
config = VersionConfigManager("tests/config/version_config.yaml")
```

## Performance Optimization

### 1. Configuration Caching

```python
# Cache configuration at module level
_config_cache = None

def get_config():
    global _config_cache
    if _config_cache is None:
        _config_cache = VersionConfigManager()
    return _config_cache
```

### 2. Data Factory Optimization

```python
from functools import lru_cache

class TestDataFactory:
    @lru_cache(maxsize=128)
    def _generate_base_data(self, resource_type: str):
        # Expensive data generation
        return base_data
```

### 3. Fixture Optimization

```python
# Use appropriate fixture scopes
@pytest.fixture(scope="session")  # Expensive, shared setup
def database_connection():
    pass

@pytest.fixture(scope="module")   # Per-module setup
def test_user():
    pass

@pytest.fixture                   # Per-test setup (default)
def test_data():
    pass
```

### 4. Test Selection

```bash
# Run only specific versions
pytest -k "v1" tests/integration/test_pets_dynamic.py

# Run only feature tests
pytest -k "feature_test" tests/integration/

# Skip slow tests in development
pytest -m "not slow" tests/
```

## Getting Additional Help

### 1. Check Logs

```bash
# Application logs
tail -f logs/app.log

# Test logs
pytest --log-cli-level=DEBUG

# Framework logs
export DYNAMIC_TESTING_DEBUG=1
pytest tests/
```

### 2. Validate Environment

```bash
# Check Python version
python --version

# Check dependencies
pip list | grep -E "(pytest|httpx|pydantic)"

# Check test environment
python -c "import tests.dynamic; print('Framework available')"
```

### 3. Community Resources

- Framework documentation: `tests/dynamic/README.md`
- Configuration reference: `tests/dynamic/CONFIG_REFERENCE.md`
- Best practices: `tests/dynamic/BEST_PRACTICES.md`
- Common scenarios: `tests/dynamic/COMMON_SCENARIOS.md`

### 4. Reporting Issues

When reporting issues, include:

1. **Error message and stack trace**
2. **Configuration files** (sanitized)
3. **Test code** that reproduces the issue
4. **Environment information** (Python version, dependencies)
5. **Steps to reproduce** the problem

```bash
# Generate environment report
python -c "
import sys
import pytest
import yaml
print(f'Python: {sys.version}')
print(f'Pytest: {pytest.__version__}')
print(f'YAML: {yaml.__version__}')
"
```