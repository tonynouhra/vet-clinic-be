# API Version Template

This template provides a step-by-step checklist for adding a new API version to the veterinary clinic platform.

## Pre-Implementation Checklist

- [ ] Define new features and enhancements for the version
- [ ] Review existing schemas to understand evolution path
- [ ] Plan database schema changes (if any)
- [ ] Identify new endpoints or enhanced functionality
- [ ] Plan backward compatibility strategy

## Implementation Checklist

### 1. Directory Structure Setup

- [ ] Create `app/api/schemas/v{N}/` directory
- [ ] Create `app/api/v{N}/` directory
- [ ] Create `app/api/schemas/v{N}/__init__.py`
- [ ] Create `app/api/v{N}/__init__.py`

### 2. Schema Definition

- [ ] Create `app/api/schemas/v{N}/users.py`
- [ ] Create `app/api/schemas/v{N}/pets.py`
- [ ] Create `app/api/schemas/v{N}/appointments.py`
- [ ] Define version-specific enums and data models
- [ ] Add proper validation and field descriptions
- [ ] Ensure backward compatibility with previous versions

### 3. API Routes Implementation

- [ ] Create `app/api/v{N}/users.py`
- [ ] Create `app/api/v{N}/pets.py`
- [ ] Create `app/api/v{N}/appointments.py`
- [ ] Implement all CRUD endpoints using shared controllers
- [ ] Add version-specific endpoints (if any)
- [ ] Update router configuration in `__init__.py`

### 4. Controller Updates (if needed)

- [ ] Add new methods for version-specific features
- [ ] Update existing methods to handle new parameters gracefully
- [ ] Ensure `**kwargs` handling for future compatibility
- [ ] Add version context support if needed

### 5. Service Updates (if needed)

- [ ] Add new service methods for version-specific features
- [ ] Update existing methods to handle new data fields
- [ ] Ensure database operations support new schema

### 6. Database Updates (if needed)

- [ ] Update model classes with new fields (nullable)
- [ ] Create Alembic migration script
- [ ] Run migration in development environment
- [ ] Test migration rollback capability

### 7. Main Application Updates

- [ ] Import new API router in `app/main.py`
- [ ] Add router to FastAPI app with correct prefix
- [ ] Update OpenAPI documentation configuration

### 8. Testing Implementation

- [ ] Create `tests/integration/v{N}/` directory
- [ ] Create unit tests for new schemas
- [ ] Create integration tests for all endpoints
- [ ] Create cross-version compatibility tests
- [ ] Test migration scenarios

### 9. Documentation Updates

- [ ] Update API documentation
- [ ] Document new features and changes
- [ ] Update version comparison table
- [ ] Create migration guide from previous version

### 10. Quality Assurance

- [ ] Run full test suite
- [ ] Test API endpoints manually
- [ ] Verify backward compatibility
- [ ] Performance testing with new features
- [ ] Security review of new endpoints

## File Templates

### Schema Template (`app/api/schemas/v{N}/users.py`)

```python
"""
V{N} User Schemas - [Brief description of new features]
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

from ..base import BaseSchema, TimestampMixin, IDMixin


class UserRole(str, Enum):
    """User roles for V{N}."""
    ADMIN = "admin"
    VETERINARIAN = "veterinarian"
    RECEPTIONIST = "receptionist"
    PET_OWNER = "pet_owner"
    # Add new roles here


class UserCreateV{N}(BaseSchema):
    """V{N} user creation schema."""
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    role: UserRole = UserRole.PET_OWNER
    
    # Previous version fields
    # ... (copy from previous version)
    
    # V{N} new fields
    # new_field: Optional[str] = Field(None, description="New field description")


class UserResponseV{N}(BaseSchema, IDMixin, TimestampMixin):
    """V{N} user response schema."""
    email: str
    first_name: str
    last_name: str
    phone_number: Optional[str]
    role: UserRole
    is_active: bool
    
    # Previous version fields
    # ... (copy from previous version)
    
    # V{N} new fields
    # new_field: Optional[str]

    class Config:
        from_attributes = True


class UserUpdateV{N}(BaseSchema):
    """V{N} user update schema."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[UserRole] = None
    
    # Previous version fields
    # ... (copy from previous version)
    
    # V{N} new fields
    # new_field: Optional[str] = None
```

### API Route Template (`app/api/v{N}/users.py`)

```python
"""
V{N} User API Endpoints - [Brief description of enhancements]
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.users.controller import UserController  # Same controller!
from app.api.schemas.v{N}.users import (
    UserCreateV{N}, 
    UserResponseV{N}, 
    UserUpdateV{N}
)
from app.app_helpers.dependency_helpers import get_controller
from app.app_helpers.response_helpers import success_response, created_response
from app.app_helpers.auth_helpers import get_current_user, require_role

router = APIRouter()


@router.get("/", response_model=dict)
async def list_users_v{N}(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    # V{N} new parameters
    # new_param: Optional[str] = None,
    controller: UserController = Depends(get_controller(UserController)),
    current_user = Depends(require_role(["admin"]))
):
    """V{N}: List users with [new features]."""
    result = await controller.list_users(
        page=page, 
        per_page=per_page, 
        search=search, 
        role=role,
        is_active=is_active,
        # V{N} parameters
        # new_param=new_param
    )

    return success_response(
        data=[UserResponseV{N}.from_orm(user).dict() for user in result["users"]],
        message="Users retrieved successfully",
        version="v{N}",
        pagination={
            "total": result["total"],
            "page": result["page"],
            "per_page": result["per_page"]
        }
    )


@router.post("/", response_model=dict)
async def create_user_v{N}(
    user_data: UserCreateV{N},
    controller: UserController = Depends(get_controller(UserController)),
    current_user = Depends(require_role(["admin"]))
):
    """V{N}: Create user with [new features]."""
    user = await controller.create_user(user_data)
    
    return created_response(
        data=UserResponseV{N}.from_orm(user).dict(),
        message="User created successfully",
        version="v{N}"
    )


@router.get("/{user_id}", response_model=dict)
async def get_user_v{N}(
    user_id: str,
    controller: UserController = Depends(get_controller(UserController)),
    current_user = Depends(get_current_user)
):
    """V{N}: Get user with [new features]."""
    user = await controller.get_user(user_id)
    
    return success_response(
        data=UserResponseV{N}.from_orm(user).dict(),
        message="User retrieved successfully",
        version="v{N}"
    )


@router.put("/{user_id}", response_model=dict)
async def update_user_v{N}(
    user_id: str,
    user_data: UserUpdateV{N},
    controller: UserController = Depends(get_controller(UserController)),
    current_user = Depends(get_current_user)
):
    """V{N}: Update user with [new features]."""
    user = await controller.update_user(user_id, user_data)
    
    return success_response(
        data=UserResponseV{N}.from_orm(user).dict(),
        message="User updated successfully",
        version="v{N}"
    )


# V{N} specific endpoints (if any)
# @router.post("/{user_id}/new-feature", response_model=dict)
# async def new_feature_v{N}(...):
#     """V{N}: New feature endpoint."""
#     pass
```

### Router Configuration Template (`app/api/v{N}/__init__.py`)

```python
"""
V{N} API Routes - Version-specific endpoints using shared controllers
"""
from fastapi import APIRouter

# Import routers
from app.api.v{N} import users, pets, appointments

api_router = APIRouter()

# Include routers
api_router.include_router(users.router, prefix="/users", tags=["users-v{N}"])
api_router.include_router(pets.router, prefix="/pets", tags=["pets-v{N}"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments-v{N}"])

@api_router.get("/")
async def api_root():
    """API v{N} root endpoint."""
    return {
        "message": "Veterinary Clinic Platform API v{N}",
        "features": ["Feature 1", "Feature 2", "Feature 3"]  # List new features
    }
```

### Test Template (`tests/integration/v{N}/test_v{N}_user_endpoints.py`)

```python
"""
Integration tests for V{N} User endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


class TestV{N}UserEndpoints:
    """Test V{N} user endpoints."""
    
    def test_create_user_with_new_features(self):
        """Test V{N} user creation with new features."""
        client = TestClient(app)
        
        user_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            # Add V{N} specific fields
        }
        
        response = client.post("/api/v{N}/users/", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["version"] == "v{N}"
        # Add V{N} specific assertions
    
    def test_list_users_with_new_filters(self):
        """Test V{N} user listing with new filters."""
        # Test implementation
        pass
    
    def test_new_v{N}_endpoint(self):
        """Test V{N} specific endpoint."""
        # Test implementation for new endpoints
        pass
```

## Migration Script Template

```python
"""
Alembic migration for V{N} features

Revision ID: [auto-generated]
Revises: [previous-revision]
Create Date: [auto-generated]
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '[auto-generated]'
down_revision = '[previous-revision]'
branch_labels = None
depends_on = None


def upgrade():
    """Add V{N} fields to existing tables."""
    # Add new columns
    op.add_column('users', sa.Column('new_field', sa.JSON(), nullable=True))
    
    # Add indexes if needed
    op.create_index('ix_users_new_field', 'users', ['new_field'], postgresql_using='gin')


def downgrade():
    """Remove V{N} fields."""
    # Remove indexes
    op.drop_index('ix_users_new_field', table_name='users')
    
    # Remove columns
    op.drop_column('users', 'new_field')
```

## Post-Implementation Checklist

- [ ] All tests pass
- [ ] API documentation updated
- [ ] Performance benchmarks completed
- [ ] Security review completed
- [ ] Deployment scripts updated
- [ ] Monitoring and logging configured
- [ ] Team training completed
- [ ] Version announcement prepared

## Notes

- Replace `{N}` with the actual version number (e.g., 3, 4, 5)
- Update feature descriptions with actual functionality
- Ensure all new fields are optional for backward compatibility
- Test thoroughly before deployment
- Document breaking changes (if any)
- Plan rollback strategy

This template ensures consistent implementation of new API versions while maintaining the clean, version-agnostic architecture.