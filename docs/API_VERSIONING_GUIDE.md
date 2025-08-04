# API Versioning Guide

## Overview

This guide documents the patterns and procedures for adding new API versions (V3, V4, etc.) to the version-agnostic architecture. The architecture is designed to make adding new versions straightforward while maintaining backward compatibility and avoiding code duplication.

## Architecture Principles

### Version-Agnostic Business Logic
- **Controllers and Services**: Shared across ALL API versions
- **Business Logic**: Changes once, benefits all versions
- **No Duplication**: Business rules are never duplicated between versions

### Version-Specific API Contracts
- **Schemas**: Organized by version in `api/schemas/v1/`, `api/schemas/v2/`, etc.
- **Routes**: Organized by version in `api/v1/`, `api/v2/`, etc.
- **Independent Evolution**: Each version can evolve without affecting others

## Adding a New API Version

### Step 1: Create Version-Specific Schema Directory

```bash
mkdir -p api/schemas/v3
touch api/schemas/v3/__init__.py
```

### Step 2: Define New Schemas

Create enhanced schemas in `api/schemas/v3/` that build upon previous versions:

```python
# api/schemas/v3/users.py
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

### Step 3: Create Version-Specific Routes

Create new route definitions in `api/v3/`:

```bash
mkdir -p api/v3
touch api/v3/__init__.py
```

```python
# api/v3/users.py
from fastapi import APIRouter, Depends
from typing import Optional

from app.users.controller import UserController  # Same controller as V1 and V2!
from app.api.schemas.v3.users import UserCreateV3, UserResponseV3, UserUpdateV3
from app.app_helpers.dependency_helpers import get_controller
from app.app_helpers.response_helpers import success_response, created_response, paginated_response

router = APIRouter(prefix="/users", tags=["users-v3"])


@router.get("/", response_model=dict)
async def list_users_v3(
        page: int = 1,
        size: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
        department: Optional[str] = None,
        timezone: Optional[str] = None,     # New in V3
        language: Optional[str] = None,     # New in V3
        is_active: Optional[bool] = None,
        controller: UserController = get_controller(UserController)  # Same controller!
):
    """V3: List users with enhanced filtering including timezone and language."""
    result = await controller.list_users(
        page=page, size=size, search=search, role=role,
        department=department, timezone=timezone, language=language,
        is_active=is_active
    )

    # Format response with V3 schema
    return paginated_response(
        data=[UserResponseV3.from_orm(user).dict() for user in result["users"]],
        total=result["total"],
        page=result["page"],
        size=result["size"],
        message="Users retrieved successfully"
    )


@router.post("/", response_model=dict)
async def create_user_v3(
        user_data: UserCreateV3,  # V3 schema, same controller
        controller: UserController = get_controller(UserController)
):
    """V3: Create user with enhanced fields including timezone and language."""
    user = await controller.create_user(user_data)
    return created_response(
        data=UserResponseV3.from_orm(user).dict(),
        message="User created successfully"
    )

# ... other endpoints follow the same pattern
```

### Step 4: Update Database Models (if needed)

If V3 introduces new fields, update the database model:

```python
# models/user.py
class User(Base):
    __tablename__ = "users"
    
    # Existing fields...
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.PET_OWNER)  # Added in V2
    department = Column(String, nullable=True)  # Added in V2
    preferences = Column(JSON, nullable=True)  # Added in V2
    notification_settings = Column(JSON, nullable=True)  # Added in V2
    
    # New V3 fields
    timezone = Column(String, nullable=True)  # New in V3
    language = Column(String, default="en")   # New in V3
    avatar_url = Column(String, nullable=True)  # New in V3
    
    # ... other fields
```

### Step 5: Create Database Migration

```bash
alembic revision --autogenerate -m "Add V3 user fields: timezone, language, avatar_url"
alembic upgrade head
```

### Step 6: Update Main Router

```python
# main.py or router configuration
from api.v1 import users as users_v1
from api.v2 import users as users_v2
from api.v3 import users as users_v3  # New

app.include_router(users_v1.router, prefix="/api/v1")
app.include_router(users_v2.router, prefix="/api/v2")
app.include_router(users_v3.router, prefix="/api/v3")  # New
```

### Step 7: Add Version-Specific Tests

```python
# app_tests/integration/test_v3_endpoints/test_users.py
import pytest
from httpx import AsyncClient

from app.api.schemas.v3.users import UserCreateV3, UserResponseV3


class TestUsersV3:
    """Integration tests for V3 user endpoints."""

    async def test_create_user_v3_with_new_fields(self, client: AsyncClient):
        """Test V3 user creation with timezone and language."""
        user_data = {
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "pet_owner",
            "timezone": "America/New_York",  # New in V3
            "language": "en"                 # New in V3
        }
        
        response = await client.post("/api/v3/users/", json=user_data)
        assert response.status_code == 201
        
        data = response.json()["data"]
        assert data["timezone"] == "America/New_York"
        assert data["language"] == "en"

    async def test_list_users_v3_with_timezone_filter(self, client: AsyncClient):
        """Test V3 user listing with timezone filtering."""
        response = await client.get("/api/v3/users/?timezone=America/New_York")
        assert response.status_code == 200
        
        # Verify V3 response format includes new fields
        users = response.json()["data"]
        for user in users:
            assert "timezone" in user
            assert "language" in user
            assert "profile_completion" in user
```

## Controller Graceful Parameter Handling

The version-agnostic controllers are designed to handle parameters from any API version gracefully:

```python
# users/controller.py - Already handles future parameters!
class UserController:
    async def list_users(
        self,
        page: int = 1,
        size: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
        department: Optional[str] = None,  # V2 parameter
        timezone: Optional[str] = None,    # V3 parameter
        language: Optional[str] = None,    # V3 parameter
        is_active: Optional[bool] = None,
        **kwargs  # Handle any additional parameters from future versions (V4, V5, etc.)
    ) -> Dict[str, Any]:
        """Handle user listing for all API versions."""
        # Controller automatically handles new parameters
        # Service layer filters out unsupported fields gracefully
        
        return await self.service.list_users(
            page=page, size=size, search=search, role=role,
            department=department, timezone=timezone, language=language,
            is_active=is_active, **kwargs
        )

    async def create_user(
        self,
        user_data: Union[UserCreateV1, UserCreateV2, UserCreateV3]  # Add new versions here
    ) -> User:
        """Handle user creation for all API versions."""
        # Extract parameters dynamically - works with any version
        create_params = {}
        for field, value in user_data.dict().items():
            if value is not None:
                create_params[field] = value

        return await self.service.create_user(**create_params)
```

## Service Layer Future-Proofing

Services handle new fields automatically through dynamic parameter handling:

```python
# users/services.py - Already future-proof!
class UserService:
    async def list_users(
        self,
        page: int,
        size: int,
        search: Optional[str] = None,
        role: Optional[Any] = None,
        department: Optional[str] = None,
        timezone: Optional[str] = None,    # V3 parameter
        language: Optional[str] = None,    # V3 parameter
        **kwargs  # Handle V4, V5, etc. parameters
    ) -> Tuple[List[User], int]:
        """Retrieve users with filtering for all API versions."""
        
        conditions = []
        
        # Existing filters...
        if search:
            # ... existing search logic
        
        # V3 filters
        if timezone and hasattr(User, 'timezone'):
            conditions.append(User.timezone == timezone)
            
        if language and hasattr(User, 'language'):
            conditions.append(User.language == language)
        
        # Future version filters handled automatically
        for field, value in kwargs.items():
            if value is not None and hasattr(User, field):
                conditions.append(getattr(User, field) == value)
        
        # ... rest of the method

    async def create_user(self, **kwargs) -> User:
        """Create user with support for all API versions."""
        user_data = {}
        
        # Add any fields that exist in the model
        for field, value in kwargs.items():
            if hasattr(User, field) and value is not None:
                user_data[field] = value
        
        # This automatically supports new V3, V4, V5 fields!
        new_user = User(**user_data)
        # ... rest of creation logic
```

## Version Evolution Strategies

### Additive Changes (Recommended)
- Add new optional fields to schemas
- Extend existing enums with new values
- Add new optional query parameters
- Controllers and services handle gracefully

### Breaking Changes (Use Sparingly)
- Change field types or validation rules
- Remove fields (mark as deprecated first)
- Change response structure significantly
- Require careful migration planning

### Deprecation Strategy
1. **Announce**: Document deprecated features in API docs
2. **Support**: Continue supporting for at least 2 major versions
3. **Warn**: Add deprecation warnings to responses
4. **Remove**: Remove only after sufficient notice period

## Schema Template for New Versions

```python
# Template: api/schemas/vX/resource.py
from pydantic import BaseModel
from typing import Optional, Dict, List, Union
from datetime import datetime
from enum import Enum

# Import previous version for reference
from app.api.schemas.v{X-1}.{resource} import {Resource}ResponseV{X-1}

class {Resource}CreateVX(BaseModel):
    """VX {resource} creation schema - enhanced with new fields."""
    # Include all previous version fields
    # Add new optional fields for VX
    new_field: Optional[str] = None  # New in VX
    
class {Resource}ResponseVX(BaseModel):
    """VX {resource} response schema - enhanced fields."""
    # Include all previous version fields
    # Add new fields for VX
    new_field: Optional[str]  # New in VX
    
    class Config:
        from_attributes = True

class {Resource}UpdateVX(BaseModel):
    """VX {resource} update schema - enhanced fields."""
    # All fields optional for updates
    # Include previous version fields + new VX fields
    new_field: Optional[str] = None  # New in VX
```

## Testing New Versions

### Version Compatibility Tests
```python
# app_tests/integration/test_version_compatibility.py
async def test_controller_works_with_all_versions():
    """Test that the same controller works with V1, V2, and V3 schemas."""
    controller = UserController(db_session)
    
    # Test with V1 schema
    v1_data = UserCreateV1(email="test@example.com", first_name="John", last_name="Doe")
    user_v1 = await controller.create_user(v1_data)
    assert user_v1.email == "test@example.com"
    
    # Test with V2 schema (same controller!)
    v2_data = UserCreateV2(
        email="test2@example.com", first_name="Jane", last_name="Doe",
        role="veterinarian", department="surgery"
    )
    user_v2 = await controller.create_user(v2_data)
    assert user_v2.role == "veterinarian"
    
    # Test with V3 schema (same controller!)
    v3_data = UserCreateV3(
        email="test3@example.com", first_name="Bob", last_name="Smith",
        role="pet_owner", timezone="America/New_York", language="en"
    )
    user_v3 = await controller.create_user(v3_data)
    assert user_v3.timezone == "America/New_York"
```

### Cross-Version Business Logic Tests
```python
async def test_business_logic_consistency_across_versions():
    """Test that business rules apply consistently across all API versions."""
    controller = UserController(db_session)
    
    # Test email uniqueness across versions
    v1_data = UserCreateV1(email="duplicate@example.com", first_name="John", last_name="Doe")
    await controller.create_user(v1_data)
    
    # Should fail with V2 schema (same business rule)
    v2_data = UserCreateV2(email="duplicate@example.com", first_name="Jane", last_name="Doe")
    with pytest.raises(HTTPException) as exc_info:
        await controller.create_user(v2_data)
    assert exc_info.value.status_code == 422
    assert "Email already registered" in str(exc_info.value.detail)
```

## Documentation Updates

When adding a new version:

1. **API Documentation**: Update OpenAPI/Swagger docs
2. **Migration Guide**: Document changes from previous version
3. **Changelog**: Record all new features and changes
4. **Client Libraries**: Update any client SDKs
5. **Integration Examples**: Provide usage examples

## Best Practices

### DO:
- ✅ Add new fields as optional in schemas
- ✅ Use `**kwargs` in controllers and services for future parameters
- ✅ Test cross-version compatibility
- ✅ Document all changes thoroughly
- ✅ Use semantic versioning for API versions

### DON'T:
- ❌ Modify existing version schemas (create new versions instead)
- ❌ Duplicate business logic between versions
- ❌ Remove fields without deprecation period
- ❌ Change field types in existing versions
- ❌ Skip testing version compatibility

This architecture makes adding new API versions straightforward while maintaining the benefits of shared business logic and clean separation of concerns.