# Scalable Schema Validation System

This document explains the scalable validation system that can handle any number of API versions without hardcoding version-specific functions.

## 🎯 Problem Solved

Instead of hardcoding functions like `validate_v1_data()`, `validate_v2_data()`, `validate_v3_data()`, etc., we now have a dynamic system that can handle any version.

## 🚀 Recommended Functions (Scalable)

### Core Dynamic Functions

```python
from api.schemas import (
    validate_data_by_version,
    validate_data_with_latest,
    validate_with_smart_fallback,
    validate_with_auto_version
)

# Validate with any version
result = validate_data_by_version(data, "v3", "users")

# Validate with latest version, fallback to older versions
result = validate_data_with_latest(data, "users")

# Smart validation with preferred version and automatic fallback
result = validate_with_smart_fallback(data, "users", preferred_version="v3")

# Automatically select best version for resource
result = validate_with_auto_version(data, "users")
```

### Version Management

```python
from api.schemas import (
    get_supported_versions,
    get_latest_version,
    is_version_supported,
    get_version_for_resource
)

# Check what versions are available
versions = get_supported_versions()  # ['v1', 'v2', 'v3']
latest = get_latest_version()        # 'v3'
supported = is_version_supported("v4")  # False

# Get best version for a resource
best_version = get_version_for_resource("users", preferred_version="v3")
```

## 📦 Adding New Versions

### Easy Version Addition

```python
from api.schemas import add_new_api_version
from pydantic import Field
from api.schemas.base import BaseSchema, IDMixin, TimestampMixin

# Define V4 schemas
class UserV4Schema(BaseSchema, IDMixin, TimestampMixin):
    email: str = Field(description="User email")
    # ... V4 specific fields
    quantum_preferences: dict = Field(default_factory=dict)

# Define migrations
def migrate_v3_to_v4(v3_data):
    v4_data = v3_data.copy()
    v4_data["quantum_preferences"] = {}
    return v4_data

def migrate_v4_to_v3(v4_data):
    v3_data = v4_data.copy()
    v3_data.pop("quantum_preferences", None)
    return v3_data

# Register V4 in one call
add_new_api_version(
    version="v4",
    schemas={"users": UserV4Schema, "pets": PetV4Schema},
    migrations_from={"v3": migrate_v3_to_v4},
    migrations_to={"v3": migrate_v4_to_v3}
)

# Now V4 is available everywhere!
result = validate_data_by_version(data, "v4", "users")
```

### Manual Registration (Advanced)

```python
from api.schemas import register_version_schemas, register_version_migrations

# Register schemas
register_version_schemas("v5", {
    "users": UserV5Schema,
    "pets": PetV5Schema
})

# Register migrations
register_version_migrations({
    "v4_to_v5": migrate_v4_to_v5,
    "v5_to_v4": migrate_v5_to_v4
})
```

## 🔄 Migration System

The system automatically handles data migration between versions:

```python
# This will try V3, if it fails, try V2 and migrate to V3, if that fails, try V1 and migrate
result = validate_with_smart_fallback(data, "users", preferred_version="v3")

if result.is_valid and hasattr(result, 'warnings'):
    for warning in result.warnings:
        print(f"Migration warning: {warning}")
```

## 🏗️ Architecture Benefits

### 1. **No Hardcoded Versions**
- No need to create `validate_v3_data()`, `validate_v4_data()`, etc.
- One function handles all versions: `validate_data_by_version(data, version, resource)`

### 2. **Automatic Fallback**
- Smart fallback tries newer versions first, then older ones
- Automatic migration between compatible versions
- Graceful degradation when newer features aren't supported

### 3. **Easy Version Addition**
- Add new versions with a single function call
- No need to modify existing code
- Migrations are automatically registered and used

### 4. **Future-Proof**
- System scales to v10, v20, v100 without code changes
- Version management is centralized and configurable
- Business logic remains version-agnostic

## 📋 Legacy Support

The old hardcoded functions are still available for backward compatibility:

```python
# These still work but are not recommended for new code
from api.schemas import validate_v1_data, validate_v2_data

result = validate_v1_data(data, "users")  # Works but not scalable
result = validate_v2_data(data, "users")  # Works but not scalable
```

## 🎯 Best Practices

### 1. Use Dynamic Functions
```python
# ✅ Good - Scalable
result = validate_data_by_version(data, version, resource)

# ❌ Avoid - Not scalable
if version == "v1":
    result = validate_v1_data(data, resource)
elif version == "v2":
    result = validate_v2_data(data, resource)
# ... this doesn't scale
```

### 2. Use Smart Fallback
```python
# ✅ Good - Handles version compatibility automatically
result = validate_with_smart_fallback(data, resource, preferred_version=user_version)

# ❌ Avoid - Manual fallback logic
try:
    result = validate_data_by_version(data, "v3", resource)
except:
    try:
        result = validate_data_by_version(data, "v2", resource)
    except:
        result = validate_data_by_version(data, "v1", resource)
```

### 3. Version-Agnostic Business Logic
```python
# ✅ Good - Business logic doesn't care about versions
def process_user(user_data, user_preferred_version=None):
    result = validate_with_smart_fallback(
        user_data, 
        "users", 
        preferred_version=user_preferred_version
    )
    
    if result.is_valid:
        return process_validated_user(result.data)
    else:
        raise ValidationError(result.errors)
```

## 🔮 Future Versions

Adding V5, V6, V7... is now trivial:

```python
# V5 with blockchain features
add_new_api_version("v5", {
    "users": UserV5WithBlockchainSchema,
    "pets": PetV5WithNFTSchema
}, migrations_from={"v4": migrate_v4_to_v5})

# V6 with AI features  
add_new_api_version("v6", {
    "users": UserV6WithAISchema,
    "pets": PetV6WithAISchema
}, migrations_from={"v5": migrate_v5_to_v6})

# All existing code continues to work!
result = validate_data_by_version(data, "v6", "users")
result = validate_with_smart_fallback(data, "users")  # Will try v6 first
```

This scalable system ensures your API can grow to support any number of versions without technical debt or code duplication! 🎉