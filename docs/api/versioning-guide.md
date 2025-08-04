# API Versioning Guide

This guide explains how to add new API versions (V3, V4, etc.) to the veterinary clinic platform using the established version-agnostic architecture.

## Architecture Overview

The API versioning system is designed with the following principles:

- **Version-Agnostic Business Logic**: Controllers and services are shared across ALL API versions
- **Version-Specific API Contracts**: Only schemas and routes differ between versions
- **Shared Infrastructure**: Common helpers and utilities work across all versions
- **Future-Proof Design**: Easy to add new versions without touching existing business logic

## Directory Structure

```
app/
├── api/
│   ├── schemas/
│   │   ├── v1/          # V1 request/response models
│   │   ├── v2/          # V2 request/response models
│   │   └── v3/          # V3 request/response models (future)
│   ├── v1/              # V1 routes → shared controllers
│   ├── v2/              # V2 routes → shared controllers
│   └── v3/              # V3 routes → shared controllers (future)
├── users/               # Version-agnostic business logic
│   ├── controller.py    # Shared across ALL API versions
│   └── services.py      # Shared across ALL API versions
└── app_helpers/         # Shared utilities
```

## Adding a New API Version (V3 Example)

### Step 1: Create Version-Specific Schemas

Create the directory structure:

```bash
mkdir -p app/api/schemas/v3
mkdir -p app/api/v3
```

Create `app/api/schemas/v3/__init__.py`:

```python
"""
V3 API Schemas - Enhanced with new features
"""

from .users import (
    UserCreateV3,
    UserResponseV3,
    UserUpdateV3,
    UserListResponseV3
)

from .pets import (
    PetCreateV3,
    PetResponseV3,
    PetUpdateV3,
    PetListResponseV3
)

from .appointments import (
    AppointmentCreateV3,
    AppointmentResponseV3,
    AppointmentUpdateV3,
    AppointmentListResponseV3
)

__all__ = [
    # User schemas
    "UserCreateV3",
    "UserResponseV3", 
    "UserUpdateV3",
    "UserListResponseV3",
    
    # Pet schemas
    "PetCreateV3",
    "PetResponseV3",
    "PetUpdateV3", 
    "PetListResponseV3",
    
    # Appointment schemas
    "AppointmentCreateV3",
    "AppointmentResponseV3",
    "AppointmentUpdateV3",
    "AppointmentListResponseV3"
]
```

### Step 2: Define V3 Schemas

Create `app/api/schemas/v3/users.py`:

```python
"""
V3 User Schemas - Enhanced with AI and IoT features
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

from ..base import BaseSchema, TimestampMixin, IDMixin


class UserRole(str, Enum):
    ADMIN = "admin"
    VETERINARIAN = "veterinarian"
    RECEPTIONIST = "receptionist"
    PET_OWNER = "pet_owner"
    AI_SPECIALIST = "ai_specialist"  # New in V3


class AIPreferences(BaseModel):
    """V3: AI-specific preferences."""
    language_model: str = Field(default="gpt-4", description="Preferred AI model")
    automation_level: str = Field(default="medium", description="AI automation level")
    personalization: bool = Field(default=True, description="Enable AI personalization")
    predictive_insights: bool = Field(default=True, description="Enable predictive insights")


class BiometricData(BaseModel):
    """V3: Biometric data integration."""
    heart_rate: Optional[int] = Field(None, description="Heart rate")
    steps: Optional[int] = Field(None, description="Daily steps")
    sleep_hours: Optional[float] = Field(None, description="Sleep hours")
    stress_level: Optional[str] = Field(None, description="Stress level")


class UserCreateV3(BaseSchema):
    """V3 user creation schema with AI and biometric features."""
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    role: UserRole = UserRole.PET_OWNER
    department: Optional[str] = None
    
    # V2 features
    preferences: Optional[Dict] = Field(default_factory=dict)
    notification_settings: Optional[Dict] = Field(default_factory=dict)
    
    # V3 new features
    ai_preferences: Optional[AIPreferences] = Field(default_factory=AIPreferences)
    biometric_data: Optional[BiometricData] = Field(default_factory=BiometricData)
    social_connections: List[str] = Field(default_factory=list, description="Connected social accounts")
    iot_devices: List[Dict[str, Any]] = Field(default_factory=list, description="Connected IoT devices")


class UserResponseV3(BaseSchema, IDMixin, TimestampMixin):
    """V3 user response schema with enhanced fields."""
    email: str
    first_name: str
    last_name: str
    phone_number: Optional[str]
    role: UserRole
    department: Optional[str]
    is_active: bool
    
    # V2 features
    preferences: Optional[Dict]
    notification_settings: Optional[Dict]
    last_login: Optional[datetime]
    permissions: List[str]
    
    # V3 new features
    ai_preferences: Optional[AIPreferences]
    biometric_data: Optional[BiometricData]
    social_connections: List[str]
    iot_devices: List[Dict[str, Any]]
    ml_insights: Optional[Dict[str, Any]] = Field(default_factory=dict, description="ML-generated insights")
    predictive_health: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Predictive health data")

    class Config:
        from_attributes = True


class UserUpdateV3(BaseSchema):
    """V3 user update schema."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[UserRole] = None
    department: Optional[str] = None
    preferences: Optional[Dict] = None
    notification_settings: Optional[Dict] = None
    
    # V3 updates
    ai_preferences: Optional[AIPreferences] = None
    biometric_data: Optional[BiometricData] = None
    social_connections: Optional[List[str]] = None
    iot_devices: Optional[List[Dict[str, Any]]] = None


class UserListResponseV3(BaseSchema):
    """V3 user list response with enhanced metadata."""
    users: List[UserResponseV3]
    total: int
    page: int
    per_page: int
    
    # V3 enhancements
    ai_insights: Optional[Dict[str, Any]] = Field(default_factory=dict, description="AI-generated list insights")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")
    suggested_actions: List[str] = Field(default_factory=list, description="AI-suggested actions")
```

### Step 3: Create V3 API Routes

Create `app/api/v3/__init__.py`:

```python
"""
V3 API Routes - Version-specific endpoints using shared controllers
"""
from fastapi import APIRouter

# Import routers
from app.api.v3 import users, pets, appointments

api_router = APIRouter()

# Include routers
api_router.include_router(users.router, prefix="/users", tags=["users-v3"])
api_router.include_router(pets.router, prefix="/pets", tags=["pets-v3"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments-v3"])

@api_router.get("/")
async def api_root():
    """API v3 root endpoint."""
    return {
        "message": "Veterinary Clinic Platform API v3",
        "features": ["AI Integration", "IoT Support", "Predictive Analytics", "Enhanced Biometrics"]
    }
```

Create `app/api/v3/users.py`:

```python
"""
V3 User API Endpoints - Enhanced with AI features
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional, List

from app.users.controller import UserController  # Same controller as V1 and V2!
from app.api.schemas.v3.users import (
    UserCreateV3, 
    UserResponseV3, 
    UserUpdateV3,
    UserListResponseV3
)
from app.app_helpers.dependency_helpers import get_controller
from app.app_helpers.response_helpers import success_response, created_response, paginated_response
from app.api.deps import get_current_user, require_role

router = APIRouter()


@router.get("/", response_model=dict)
async def list_users_v3(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    department: Optional[str] = None,
    is_active: Optional[bool] = None,
    # V3 new filters
    has_ai_preferences: Optional[bool] = None,
    has_biometric_data: Optional[bool] = None,
    iot_device_count: Optional[int] = None,
    controller: UserController = Depends(get_controller(UserController)),
    current_user = Depends(require_role(["admin", "ai_specialist"]))
):
    """V3: List users with AI and IoT filtering."""
    result = await controller.list_users(
        page=page, 
        per_page=per_page, 
        search=search, 
        role=role,
        department=department, 
        is_active=is_active,
        # V3 parameters - controller handles gracefully
        has_ai_preferences=has_ai_preferences,
        has_biometric_data=has_biometric_data,
        iot_device_count=iot_device_count
    )

    # V3 enhanced response with AI insights
    response_data = UserListResponseV3(
        users=[UserResponseV3.from_orm(user) for user in result["users"]],
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
        ai_insights=result.get("ai_insights", {}),
        filters_applied={
            "search": search,
            "role": role,
            "department": department,
            "is_active": is_active,
            "has_ai_preferences": has_ai_preferences,
            "has_biometric_data": has_biometric_data,
            "iot_device_count": iot_device_count
        },
        suggested_actions=result.get("suggested_actions", [])
    )

    return success_response(
        data=response_data.dict(),
        message="Users retrieved successfully with AI insights",
        version="v3"
    )


@router.post("/", response_model=dict)
async def create_user_v3(
    user_data: UserCreateV3,
    controller: UserController = Depends(get_controller(UserController)),
    current_user = Depends(require_role(["admin", "ai_specialist"]))
):
    """V3: Create user with AI and biometric features."""
    user = await controller.create_user(user_data)
    
    return created_response(
        data=UserResponseV3.from_orm(user).dict(),
        message="User created successfully with V3 features",
        version="v3"
    )


@router.get("/{user_id}", response_model=dict)
async def get_user_v3(
    user_id: str,
    include_ai_insights: bool = Query(True, description="Include AI-generated insights"),
    controller: UserController = Depends(get_controller(UserController)),
    current_user = Depends(get_current_user)
):
    """V3: Get user with AI insights."""
    user = await controller.get_user(
        user_id, 
        include_ai_insights=include_ai_insights  # V3 parameter
    )
    
    return success_response(
        data=UserResponseV3.from_orm(user).dict(),
        message="User retrieved successfully with AI insights",
        version="v3"
    )


@router.put("/{user_id}", response_model=dict)
async def update_user_v3(
    user_id: str,
    user_data: UserUpdateV3,
    controller: UserController = Depends(get_controller(UserController)),
    current_user = Depends(get_current_user)
):
    """V3: Update user with AI and biometric features."""
    user = await controller.update_user(user_id, user_data)
    
    return success_response(
        data=UserResponseV3.from_orm(user).dict(),
        message="User updated successfully with V3 features",
        version="v3"
    )


# V3 specific endpoints
@router.post("/{user_id}/ai-insights", response_model=dict)
async def generate_ai_insights_v3(
    user_id: str,
    controller: UserController = Depends(get_controller(UserController)),
    current_user = Depends(require_role(["admin", "ai_specialist"]))
):
    """V3: Generate AI insights for user."""
    insights = await controller.generate_ai_insights(user_id)  # New method
    
    return success_response(
        data=insights,
        message="AI insights generated successfully",
        version="v3"
    )


@router.post("/{user_id}/sync-biometrics", response_model=dict)
async def sync_biometric_data_v3(
    user_id: str,
    controller: UserController = Depends(get_controller(UserController)),
    current_user = Depends(get_current_user)
):
    """V3: Sync biometric data from connected devices."""
    sync_result = await controller.sync_biometric_data(user_id)  # New method
    
    return success_response(
        data=sync_result,
        message="Biometric data synced successfully",
        version="v3"
    )
```

### Step 4: Update Controllers for V3 Support

The beauty of the version-agnostic architecture is that controllers automatically support new versions! However, you may want to add V3-specific methods:

```python
# In app/users/controller.py - add new methods for V3 features

async def generate_ai_insights(self, user_id: str) -> Dict[str, Any]:
    """Generate AI insights for user (V3 feature)."""
    user = await self.get_user(user_id)
    
    # AI insight generation logic
    insights = await self.service.generate_ai_insights(user)
    
    return insights

async def sync_biometric_data(self, user_id: str) -> Dict[str, Any]:
    """Sync biometric data from IoT devices (V3 feature)."""
    user = await self.get_user(user_id)
    
    # Biometric sync logic
    sync_result = await self.service.sync_biometric_data(user)
    
    return sync_result

async def list_users(
    self,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    role: Optional[str] = None,
    department: Optional[str] = None,
    is_active: Optional[bool] = None,
    # V3 parameters - handled gracefully
    has_ai_preferences: Optional[bool] = None,
    has_biometric_data: Optional[bool] = None,
    iot_device_count: Optional[int] = None,
    **kwargs  # Handle future version parameters
) -> Dict[str, Any]:
    """Enhanced list_users with V3 support."""
    # Existing logic...
    
    # V3 enhancements
    if has_ai_preferences is not None or has_biometric_data is not None:
        # Add V3-specific filtering
        pass
    
    # Generate AI insights for V3
    ai_insights = {}
    suggested_actions = []
    if any([has_ai_preferences, has_biometric_data, iot_device_count]):
        ai_insights = await self.service.generate_list_insights(users)
        suggested_actions = await self.service.get_suggested_actions(users)
    
    return {
        "users": users,
        "total": total,
        "page": page,
        "per_page": per_page,
        "ai_insights": ai_insights,
        "suggested_actions": suggested_actions
    }
```

### Step 5: Update Main Application

Add V3 to the main application in `app/main.py`:

```python
from app.api.v1 import api_router as v1_router
from app.api.v2 import api_router as v2_router
from app.api.v3 import api_router as v3_router  # New

# Include API routers
app.include_router(v1_router, prefix="/api/v1")
app.include_router(v2_router, prefix="/api/v2")
app.include_router(v3_router, prefix="/api/v3")  # New
```

### Step 6: Update Database Models (if needed)

If V3 introduces new fields, update the database models:

```python
# In app/models/user.py - add V3 fields

class User(Base):
    # Existing fields...
    
    # V3 fields (nullable for backward compatibility)
    ai_preferences = Column(JSON, nullable=True)
    biometric_data = Column(JSON, nullable=True)
    social_connections = Column(JSON, nullable=True)
    iot_devices = Column(JSON, nullable=True)
    ml_insights = Column(JSON, nullable=True)
    predictive_health = Column(JSON, nullable=True)
```

Create a database migration:

```bash
alembic revision --autogenerate -m "Add V3 user fields"
alembic upgrade head
```

### Step 7: Add V3 Tests

Create comprehensive tests for V3:

```bash
mkdir -p tests/integration/v3
mkdir -p tests/unit/schemas/v3
```

Create `tests/integration/v3/test_v3_user_endpoints.py`:

```python
"""
Integration tests for V3 User endpoints with AI features.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

class TestV3UserEndpoints:
    """Test V3 user endpoints with AI features."""
    
    def test_create_user_with_ai_preferences(self):
        """Test V3 user creation with AI preferences."""
        client = TestClient(app)
        
        user_data = {
            "email": "ai_user@example.com",
            "first_name": "AI",
            "last_name": "User",
            "ai_preferences": {
                "language_model": "gpt-4",
                "automation_level": "high",
                "personalization": True
            },
            "biometric_data": {
                "heart_rate": 72,
                "steps": 10000
            }
        }
        
        response = client.post("/api/v3/users/", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["version"] == "v3"
        assert data["data"]["ai_preferences"]["language_model"] == "gpt-4"
    
    def test_generate_ai_insights(self):
        """Test V3 AI insights generation."""
        # Test implementation...
        pass
```

## Version Evolution Strategies

### Backward Compatibility

- Always make new fields optional
- Never remove existing fields in newer versions
- Use Union types in controllers to handle multiple schema versions
- Provide migration utilities between versions

### Forward Compatibility

- Design controllers to handle unknown parameters gracefully using `**kwargs`
- Use feature flags for experimental V3+ features
- Implement version detection in controllers when needed

### Database Evolution

- Add new columns as nullable
- Use JSON columns for flexible V3+ data structures
- Create migration scripts for data transformation
- Maintain indexes for new query patterns

### Testing Strategy

- Test each version independently
- Test cross-version compatibility
- Test migration scenarios
- Test that business logic changes affect all versions

## Best Practices

1. **Keep Business Logic Version-Agnostic**: Controllers and services should work with any version
2. **Version-Specific Only at API Layer**: Only schemas and routes should differ between versions
3. **Graceful Parameter Handling**: Use `**kwargs` and `hasattr()` checks for version-specific parameters
4. **Comprehensive Testing**: Test each version thoroughly and cross-version compatibility
5. **Documentation**: Document new features and migration paths clearly
6. **Performance**: Consider performance implications of new features across all versions

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all new schema files are properly imported
2. **Database Errors**: Run migrations for new fields
3. **Test Failures**: Update test fixtures for new schema fields
4. **Performance Issues**: Add indexes for new query patterns

### Debugging Tips

1. Check controller parameter handling with `**kwargs`
2. Verify schema validation with Pydantic
3. Test API endpoints with different version schemas
4. Monitor database query performance with new fields

This guide provides a complete framework for adding new API versions while maintaining the clean, version-agnostic architecture.