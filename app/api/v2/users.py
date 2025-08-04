"""
V2 User API Endpoints

This module contains all user-related API endpoints for version 2.
Uses the shared UserController with V2-specific schemas and enhanced features
like role information, relationships, and advanced filtering.
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
from app.api.schemas.v2.users import (
    UserCreateV2,
    UserUpdateV2,
    UserResponseV2,
    UserListRequestV2,
    UserResponseModelV2,
    UserListResponseModelV2,
    UserOperationSuccessV2,
    RoleAssignmentV2,
    MultipleRoleAssignmentV2,
    UserProfileUpdateV2,
    UserStatsV2,
    UserStatsResponseModelV2,
    BatchUserCreateV2,
    BatchUserUpdateV2,
    BatchOperationResultV2
)

router = APIRouter(prefix="/users", tags=["users-v2"])


# Helper function to convert User model to V2 response
def user_to_v2_response(user: User, include_stats: bool = False) -> UserResponseV2:
    """Convert User model to V2 response schema with enhanced fields."""
    response_data = {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone_number": user.phone_number,
        "bio": user.bio,
        "profile_image_url": user.profile_image_url,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }
    
    # Add enhanced V2 fields if available
    if hasattr(user, 'roles') and user.roles:
        response_data["roles"] = [
            {
                "role": role.role,
                "assigned_at": role.assigned_at,
                "assigned_by": role.assigned_by
            }
            for role in user.roles
        ]
    
    if include_stats:
        response_data["pets_count"] = len(user.pets) if hasattr(user, 'pets') and user.pets else 0
        response_data["appointments_count"] = len(user.appointments) if hasattr(user, 'appointments') and user.appointments else 0
    
    return UserResponseV2(**response_data)


@router.get("/", response_model=UserListResponseModelV2)
async def list_users(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    department: Optional[str] = Query(None, description="Filter by department"),
    include_roles: bool = Query(False, description="Include role information"),
    include_relationships: bool = Query(False, description="Include pet/appointment counts"),
    current_user: User = Depends(require_role(UserRole.CLINIC_MANAGER)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    List users with pagination and enhanced filtering.
    
    V2 includes enhanced filtering options, role information, and relationship counts.
    Requires clinic admin role or higher.
    """
    users, total = await controller.list_users(
        page=page,
        per_page=per_page,
        search=search,
        role=role,
        is_active=is_active,
        department=department,
        include_roles=include_roles,
        include_relationships=include_relationships
    )
    
    # Convert to V2 response format
    user_responses = [
        user_to_v2_response(user, include_stats=include_relationships) 
        for user in users
    ]
    
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
        "version": "v2"
    }


@router.post("/", response_model=UserResponseModelV2, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateV2,
    current_user: User = Depends(require_role(UserRole.CLINIC_MANAGER)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Create a new user with enhanced V2 fields.
    
    V2 supports additional fields like bio, profile image, department, and preferences.
    Requires clinic admin role or higher.
    """
    user = await controller.create_user(
        user_data=user_data,
        created_by=current_user.id
    )
    
    return {
        "success": True,
        "data": user_to_v2_response(user),
        "version": "v2"
    }


@router.get("/{user_id}", response_model=UserResponseModelV2)
async def get_user(
    user_id: uuid.UUID,
    include_roles: bool = Query(True, description="Include role information"),
    include_relationships: bool = Query(True, description="Include pet/appointment counts"),
    current_user: User = Depends(get_current_user),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Get user by ID with enhanced V2 information.
    
    V2 includes role information and relationship counts by default.
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
        include_roles=include_roles,
        include_relationships=include_relationships
    )
    
    return {
        "success": True,
        "data": user_to_v2_response(user, include_stats=include_relationships),
        "version": "v2"
    }


@router.put("/{user_id}", response_model=UserResponseModelV2)
async def update_user(
    user_id: uuid.UUID,
    user_data: UserUpdateV2,
    current_user: User = Depends(get_current_user),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Update user information with enhanced V2 fields.
    
    V2 supports updating additional fields like bio, profile image, department, and preferences.
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
        "data": user_to_v2_response(user),
        "version": "v2"
    }


@router.patch("/{user_id}/profile", response_model=UserResponseModelV2)
async def update_user_profile(
    user_id: uuid.UUID,
    profile_data: UserProfileUpdateV2,
    current_user: User = Depends(get_current_user),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Update user profile information (V2 specific endpoint).
    
    Allows updating profile-specific fields like bio, image, and preferences.
    """
    # Check authorization - users can only update their own profile
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's profile"
        )
    
    user = await controller.update_user(
        user_id=user_id,
        user_data=profile_data,
        updated_by=current_user.id
    )
    
    return {
        "success": True,
        "data": user_to_v2_response(user),
        "version": "v2"
    }


@router.delete("/{user_id}", response_model=UserOperationSuccessV2)
async def delete_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Delete a user with enhanced V2 response.
    
    Requires system admin role.
    """
    result = await controller.delete_user(
        user_id=user_id,
        deleted_by=current_user.id
    )
    
    return UserOperationSuccessV2(
        success=result["success"],
        message=result["message"],
        user_id=user_id
    )


@router.post("/{user_id}/activate", response_model=UserResponseModelV2)
async def activate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.CLINIC_MANAGER)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Activate a user account with enhanced V2 response.
    
    Requires clinic admin role or higher.
    """
    user = await controller.activate_user(
        user_id=user_id,
        activated_by=current_user.id
    )
    
    return {
        "success": True,
        "data": user_to_v2_response(user),
        "version": "v2"
    }


@router.post("/{user_id}/deactivate", response_model=UserResponseModelV2)
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.CLINIC_MANAGER)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Deactivate a user account with enhanced V2 response.
    
    Requires clinic admin role or higher.
    """
    user = await controller.deactivate_user(
        user_id=user_id,
        deactivated_by=current_user.id
    )
    
    return {
        "success": True,
        "data": user_to_v2_response(user),
        "version": "v2"
    }


@router.post("/{user_id}/roles", response_model=UserOperationSuccessV2)
async def assign_role(
    user_id: uuid.UUID,
    role_data: RoleAssignmentV2,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Assign a role to a user with enhanced V2 features.
    
    V2 supports additional metadata like department and notes.
    Requires system admin role.
    """
    result = await controller.assign_role(
        user_id=user_id,
        role=role_data.role,
        assigned_by=current_user.id
    )
    
    return UserOperationSuccessV2(
        success=result["success"],
        message=result["message"],
        user_id=user_id,
        affected_roles=[role_data.role]
    )


@router.post("/{user_id}/roles/batch", response_model=UserOperationSuccessV2)
async def assign_multiple_roles(
    user_id: uuid.UUID,
    roles_data: MultipleRoleAssignmentV2,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Assign multiple roles to a user (V2 specific endpoint).
    
    Allows batch role assignment with individual metadata.
    Requires system admin role.
    """
    assigned_roles = []
    for role_assignment in roles_data.roles:
        await controller.assign_role(
            user_id=user_id,
            role=role_assignment.role,
            assigned_by=current_user.id
        )
        assigned_roles.append(role_assignment.role)
    
    return UserOperationSuccessV2(
        success=True,
        message=f"Successfully assigned {len(assigned_roles)} roles",
        user_id=user_id,
        affected_roles=assigned_roles
    )


@router.delete("/{user_id}/roles/{role}", response_model=UserOperationSuccessV2)
async def remove_role(
    user_id: uuid.UUID,
    role: UserRole,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Remove a role from a user with enhanced V2 response.
    
    Requires system admin role.
    """
    result = await controller.remove_role(
        user_id=user_id,
        role=role,
        removed_by=current_user.id
    )
    
    return UserOperationSuccessV2(
        success=result["success"],
        message=result["message"],
        user_id=user_id,
        affected_roles=[role]
    )


@router.get("/{user_id}/stats", response_model=UserStatsResponseModelV2)
async def get_user_stats(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Get user statistics (V2 specific endpoint).
    
    Provides detailed statistics about user activity and usage.
    Users can view their own stats, admins can view any user's stats.
    """
    # Check authorization
    if user_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.CLINIC_MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user's statistics"
        )
    
    user = await controller.get_user_by_id(
        user_id=user_id,
        include_relationships=True
    )
    
    # Calculate statistics
    from datetime import datetime, timedelta
    account_age = (datetime.utcnow() - user.created_at).days
    
    stats = UserStatsV2(
        total_pets=len(user.pets) if hasattr(user, 'pets') and user.pets else 0,
        total_appointments=len(user.appointments) if hasattr(user, 'appointments') and user.appointments else 0,
        active_appointments=0,  # Would need to filter by status
        last_activity=user.last_login_at,
        registration_date=user.created_at,
        account_age_days=account_age
    )
    
    return {
        "success": True,
        "data": stats,
        "version": "v2"
    }


@router.post("/batch", response_model=BatchOperationResultV2)
async def batch_create_users(
    batch_data: BatchUserCreateV2,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    controller: UserController = Depends(get_controller(UserController))
):
    """
    Batch create users (V2 specific endpoint).
    
    Allows creating multiple users in a single operation.
    Requires system admin role.
    """
    results = {
        "success": True,
        "total_requested": len(batch_data.users),
        "successful": 0,
        "failed": 0,
        "errors": [],
        "processed_ids": []
    }
    
    for i, user_data in enumerate(batch_data.users):
        try:
            # Set default role if not specified
            if not user_data.role:
                user_data.role = batch_data.default_role
            
            user = await controller.create_user(
                user_data=user_data,
                created_by=current_user.id
            )
            
            results["successful"] += 1
            results["processed_ids"].append(user.id)
            
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({
                "index": i,
                "email": user_data.email,
                "error": str(e)
            })
    
    results["success"] = results["failed"] == 0
    
    return results