# API Version Templates

This directory contains templates for creating new API versions quickly and consistently. These templates follow the version-agnostic architecture patterns established in the API restructure.

## Quick Start

To add a new API version (e.g., V3):

1. **Copy and customize schema template**:
   ```bash
   cp templates/api_version_templates/schema_template.py api/schemas/v3/users.py
   # Edit the file and replace placeholders
   ```

2. **Copy and customize router template**:
   ```bash
   cp templates/api_version_templates/router_template.py api/v3/users.py
   # Edit the file and replace placeholders
   ```

3. **Copy and customize test template**:
   ```bash
   cp templates/api_version_templates/test_template.py app_tests/integration/test_v3_endpoints/test_users.py
   # Edit the file and replace placeholders
   ```

4. **Update main router configuration**:
   ```python
   # main.py
   from api.v3 import users as users_v3
   app.include_router(users_v3.router, prefix="/api/v3")
   ```

## Template Files

### schema_template.py
Template for creating version-specific Pydantic schemas:
- `{Resource}CreateV{VERSION}` - Request schema for creation
- `{Resource}ResponseV{VERSION}` - Response schema
- `{Resource}UpdateV{VERSION}` - Request schema for updates
- `{Resource}FilterV{VERSION}` - Query parameter schema
- Example enums and configurations

### router_template.py
Template for creating version-specific FastAPI routers:
- Standard CRUD endpoints (GET, POST, PUT, DELETE)
- Proper dependency injection
- Version-specific schema usage
- Example of version-specific endpoints

### test_template.py
Template for comprehensive testing:
- Integration tests for all endpoints
- Business logic tests
- Cross-version compatibility tests
- Validation and error handling tests

## Placeholder Replacement Guide

When using templates, replace these placeholders:

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{VERSION}` | New API version number | `3` |
| `{PREVIOUS_VERSION}` | Previous API version | `2` |
| `{RESOURCE}` | Resource name (capitalized) | `User` |
| `{resource}` | Resource name (lowercase) | `user` |

## Example: Adding V3 Users API

### Step 1: Create V3 User Schema

```bash
mkdir -p api/schemas/v3
cp templates/api_version_templates/schema_template.py api/schemas/v3/users.py
```

Edit `api/schemas/v3/users.py`:

```python
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    VETERINARIAN = "veterinarian"
    RECEPTIONIST = "receptionist"
    PET_OWNER = "pet_owner"
    CLINIC_MANAGER = "clinic_manager"  # New in V3

class UserCreateV3(BaseModel):
    """V3 user creation schema - enhanced with new fields."""
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    role: UserRole = UserRole.PET_OWNER
    department: Optional[str] = None
    preferences: Optional[Dict] = None
    notification_settings: Optional[Dict] = None
    timezone: Optional[str] = None        # New in V3
    language: Optional[str] = "en"        # New in V3
    avatar_url: Optional[str] = None      # New in V3

class UserResponseV3(BaseModel):
    """V3 user response schema - enhanced fields."""
    id: str
    email: str
    first_name: str
    last_name: str
    phone_number: Optional[str]
    role: UserRole
    department: Optional[str]
    preferences: Optional[Dict]
    notification_settings: Optional[Dict]
    timezone: Optional[str]
    language: str
    avatar_url: Optional[str]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    permissions: List[str]
    profile_completion: float             # New in V3

    class Config:
        from_attributes = True

class UserUpdateV3(BaseModel):
    """V3 user update schema - enhanced fields."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[UserRole] = None
    department: Optional[str] = None
    preferences: Optional[Dict] = None
    notification_settings: Optional[Dict] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    avatar_url: Optional[str] = None
```

### Step 2: Create V3 User Router

```bash
mkdir -p api/v3
cp templates/api_version_templates/router_template.py api/v3/users.py
```

Edit `api/v3/users.py` (replace placeholders with actual values).

### Step 3: Create V3 User Tests

```bash
mkdir -p app_tests/integration/test_v3_endpoints
cp templates/api_version_templates/test_template.py app_tests/integration/test_v3_endpoints/test_users.py
```

Edit the test file and replace placeholders.

### Step 4: Update Main Router

```python
# main.py or router configuration
from api.v1 import users as users_v1
from api.v2 import users as users_v2
from api.v3 import users as users_v3  # New

app.include_router(users_v1.router, prefix="/api/v1")
app.include_router(users_v2.router, prefix="/api/v2")
app.include_router(users_v3.router, prefix="/api/v3")  # New
```

## Automated Script (Optional)

You can create a script to automate the template replacement:

```bash
#!/bin/bash
# create_api_version.sh

VERSION=$1
RESOURCE=$2
PREVIOUS_VERSION=$3

if [ -z "$VERSION" ] || [ -z "$RESOURCE" ] || [ -z "$PREVIOUS_VERSION" ]; then
    echo "Usage: $0 <version> <resource> <previous_version>"
    echo "Example: $0 3 users 2"
    exit 1
fi

RESOURCE_LOWER=$(echo "$RESOURCE" | tr '[:upper:]' '[:lower:]')
RESOURCE_UPPER=$(echo "$RESOURCE" | sed 's/.*/\u&/')

# Create directories
mkdir -p "api/schemas/v$VERSION"
mkdir -p "api/v$VERSION"
mkdir -p "app_tests/integration/test_v${VERSION}_endpoints"

# Copy and customize schema
sed "s/{VERSION}/$VERSION/g; s/{PREVIOUS_VERSION}/$PREVIOUS_VERSION/g; s/{RESOURCE}/$RESOURCE_UPPER/g; s/{resource}/$RESOURCE_LOWER/g" \
    templates/api_version_templates/schema_template.py > "api/schemas/v$VERSION/$RESOURCE_LOWER.py"

# Copy and customize router
sed "s/{VERSION}/$VERSION/g; s/{RESOURCE}/$RESOURCE_UPPER/g; s/{resource}/$RESOURCE_LOWER/g" \
    templates/api_version_templates/router_template.py > "api/v$VERSION/$RESOURCE_LOWER.py"

# Copy and customize tests
sed "s/{VERSION}/$VERSION/g; s/{PREVIOUS_VERSION}/$PREVIOUS_VERSION/g; s/{RESOURCE}/$RESOURCE_UPPER/g; s/{resource}/$RESOURCE_LOWER/g" \
    templates/api_version_templates/test_template.py > "app_tests/integration/test_v${VERSION}_endpoints/test_$RESOURCE_LOWER.py"

echo "Created V$VERSION $RESOURCE API files:"
echo "- api/schemas/v$VERSION/$RESOURCE_LOWER.py"
echo "- api/v$VERSION/$RESOURCE_LOWER.py"
echo "- app_tests/integration/test_v${VERSION}_endpoints/test_$RESOURCE_LOWER.py"
echo ""
echo "Don't forget to:"
echo "1. Update the main router configuration"
echo "2. Add database migrations if needed"
echo "3. Update API documentation"
```

Usage:
```bash
chmod +x create_api_version.sh
./create_api_version.sh 3 users 2
```

## Best Practices

### Schema Evolution
- Always make new fields optional to maintain backward compatibility
- Use descriptive field names and add comments for new fields
- Include proper validation and examples in docstrings

### Router Implementation
- Keep endpoints thin - delegate to controllers immediately
- Use consistent response formatting across versions
- Add proper OpenAPI documentation with examples

### Testing Strategy
- Test new functionality thoroughly
- Always include cross-version compatibility tests
- Test error scenarios and edge cases
- Verify business logic consistency across versions

### Documentation
- Update API documentation for each new version
- Document breaking changes and migration paths
- Provide examples for new features
- Maintain changelog for version history

## Controller and Service Compatibility

Remember that controllers and services are version-agnostic and should already handle new parameters gracefully through:

- `**kwargs` parameters in method signatures
- Dynamic parameter extraction using `hasattr()` checks
- Union types for schema parameters (e.g., `Union[UserCreateV1, UserCreateV2, UserCreateV3]`)

If you need to add new business logic, update the shared controller/service files, not the version-specific routes.

## Migration Checklist

When adding a new API version:

- [ ] Create version-specific schemas
- [ ] Create version-specific routes
- [ ] Update controller Union types (if needed)
- [ ] Add database migrations (if new fields)
- [ ] Create comprehensive tests
- [ ] Update main router configuration
- [ ] Update API documentation
- [ ] Test cross-version compatibility
- [ ] Update client libraries/SDKs
- [ ] Announce new version to users

This template system ensures consistency and reduces the effort required to add new API versions while maintaining the benefits of the version-agnostic architecture.