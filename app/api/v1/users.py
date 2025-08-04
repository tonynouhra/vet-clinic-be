"""
V1 User API Endpoints

This module contains all user-related API endpoints for version 1.
Uses the shared UserController with V1-specific schemas and response formatting.
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User, UserRole
from app.users.controller import UserController
from app.api.deps import get_current_user, require_role
from app.app_helpers.dependency_helpers import get_controller
from app.api.schemas.v1.users import (
    UserCreateV1,
    UserUpdateV1,
    UserResponseV1,
    UserListRequestV1,
    UserResponseModelV1,
    UserListResponseModelV1,
    UserOperationSuccessV1,
    RoleAssignmentV1
)

router = APIRouter(prefix="/users", tags=["users-v1"])


# Helper function to convert User model to V1 response
def user_to_v1_response(user: User) -> UserResponseV1:
    """Convert User model to V1 response schema."""
    return UserResponseV1(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number,
        is_active=user.is_active,
        is_verified=user.is_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.get("/", response_model=UserListResponseModelV1)
async def list_users(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(require_role(UserRole.CLINIC_MANAGER)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    List users with pagination and filtering.
    
    Requires clinic admin role or higher.
    """
    users, total = await controller.list_users(
        page=page,
        per_page=per_page,
        search=search,
        role=role,
        is_active=is_active,
        include_roles=False  # V1 doesn't include roles
    )
    
    # Convert to V1 response format
    user_responses = [user_to_v1_response(user) for user in users]
    
    # Calculate pagination metadata
    pages = (total + per_page - 1) // per_page
    
    return {
        "success": True,
        "data": user_responses,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages
        },
        "version": "v1"
    }


@router.post("/", response_model=UserResponseModelV1, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateV1,
    current_user: User = Depends(require_role(UserRole.CLINIC_MANAGER)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Create a new user.
    
    Requires clinic admin role or higher.
    """
    user = await controller.create_user(
        user_data=user_data,
        created_by=current_user.id
    )
    
    return {
        "success": True,
        "data": user_to_v1_response(user),
        "version": "v1"
    }


@router.get("/{user_id}", response_model=UserResponseModelV1)
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Get user by ID.
    
    Users can view their own profile, admins can view any profile.
    """
    # Check authorization
    if user_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.CLINIC_MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )
    
    user = await controller.get_user_by_id(
        user_id=user_id,
        include_roles=False,  # V1 doesn't include roles
        include_relationships=False  # V1 doesn't include relationships
    )
    
    return {
        "success": True,
        "data": user_to_v1_response(user),
        "version": "v1"
    }


@router.put("/{user_id}", response_model=UserResponseModelV1)
async def update_user(
    user_id: uuid.UUID,
    user_data: UserUpdateV1,
    current_user: User = Depends(get_current_user),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Update user information.
    
    Users can update their own profile, admins can update any profile.
    """
    # Check authorization
    if user_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.CLINIC_MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    user = await controller.update_user(
        user_id=user_id,
        user_data=user_data,
        updated_by=current_user.id
    )
    
    return {
        "success": True,
        "data": user_to_v1_response(user),
        "version": "v1"
    }


@router.delete("/{user_id}", response_model=UserOperationSuccessV1)
async def delete_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Delete a user.
    
    Requires system admin role.
    """
    result = await controller.delete_user(
        user_id=user_id,
        deleted_by=current_user.id
    )
    
    return UserOperationSuccessV1(
        success=result["success"],
        message=result["message"],
        user_id=user_id
    )


@router.post("/{user_id}/activate", response_model=UserResponseModelV1)
async def activate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.CLINIC_MANAGER)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Activate a user account.
    
    Requires clinic admin role or higher.
    """
    user = await controller.activate_user(
        user_id=user_id,
        activated_by=current_user.id
    )
    
    return {
        "success": True,
        "data": user_to_v1_response(user),
        "version": "v1"
    }


@router.post("/{user_id}/deactivate", response_model=UserResponseModelV1)
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.CLINIC_MANAGER)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Deactivate a user account.
    
    Requires clinic admin role or higher.
    """
    user = await controller.deactivate_user(
        user_id=user_id,
        deactivated_by=current_user.id
    )
    
    return {
        "success": True,
        "data": user_to_v1_response(user),
        "version": "v1"
    }


@router.post("/{user_id}/roles", response_model=UserOperationSuccessV1)
async def assign_role(
    user_id: uuid.UUID,
    role_data: RoleAssignmentV1,
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Assign a role to a user.
    
    Requires system admin role.
    """
    result = await controller.assign_role(
        user_id=user_id,
        role=role_data.role,
        assigned_by=current_user.id
    )
    
    return UserOperationSuccessV1(
        success=result["success"],
        message=result["message"],
        user_id=user_id
    )


@router.delete("/{user_id}/roles/{role}", response_model=UserOperationSuccessV1)
async def remove_role(
    user_id: uuid.UUID,
    role: UserRole,
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Remove a role from a user.
    
    Requires system admin role.
    """
    result = await controller.remove_role(
        user_id=user_id,
        role=role,
        removed_by=current_user.id
    )
    
    return UserOperationSuccessV1(
        success=result["success"],
        message=result["message"],
        user_id=user_id
    )