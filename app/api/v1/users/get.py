"""
User GET endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User, UserRole
from app.services.user_service import UserService
from app.app_helpers import (
    get_current_user,
    require_role,
    success_response,
    paginated_response,
    validate_uuid,
    validate_pagination_params
)

router = APIRouter()


@router.get("/")
async def list_users(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(require_role(UserRole.CLINIC_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    List users with pagination and filtering.
    
    Requires clinic admin role or higher.
    """
    # Validate pagination parameters
    page, size = validate_pagination_params(page, size)
    
    # Use service layer for business logic
    user_service = UserService(db)
    users, total = await user_service.list_users(
        page=page,
        size=size,
        search=search,
        role=role,
        is_active=is_active
    )
    
    return paginated_response(
        data=[user.dict() for user in users],
        total=total,
        page=page,
        size=size,
        message="Users retrieved successfully"
    )


@router.get("/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's profile information.
    """
    return success_response(
        data=current_user.dict(),
        message="User profile retrieved successfully"
    )


@router.get("/{user_id}")
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user by ID.
    
    Users can only access their own profile unless they have admin privileges.
    """
    # Validate UUID format
    user_uuid = validate_uuid(user_id, "user_id")
    
    # Check permissions
    if (str(current_user.id) != user_id and 
        not current_user.has_role(UserRole.CLINIC_ADMIN)):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only access your own profile."
        )
    
    # Use service layer
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_uuid)
    
    return success_response(
        data=user.dict(),
        message="User retrieved successfully"
    )


@router.get("/{user_id}/pets")
async def get_user_pets(
    user_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get pets owned by a specific user.
    
    Users can only access their own pets unless they have admin privileges.
    """
    # Validate UUID and permissions
    user_uuid = validate_uuid(user_id, "user_id")
    
    if (str(current_user.id) != user_id and 
        not current_user.has_role(UserRole.CLINIC_ADMIN)):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only access your own pets."
        )
    
    # Validate pagination
    page, size = validate_pagination_params(page, size)
    
    # Use service layer
    user_service = UserService(db)
    pets, total = await user_service.get_user_pets(
        user_id=user_uuid,
        page=page,
        size=size
    )
    
    return paginated_response(
        data=[pet.dict() for pet in pets],
        total=total,
        page=page,
        size=size,
        message="User pets retrieved successfully"
    )


@router.get("/{user_id}/appointments")
async def get_user_appointments(
    user_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by appointment status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get appointments for a specific user.
    
    Users can only access their own appointments unless they have admin privileges.
    """
    # Validate UUID and permissions
    user_uuid = validate_uuid(user_id, "user_id")
    
    if (str(current_user.id) != user_id and 
        not current_user.has_role(UserRole.CLINIC_ADMIN)):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only access your own appointments."
        )
    
    # Validate pagination
    page, size = validate_pagination_params(page, size)
    
    # Use service layer
    user_service = UserService(db)
    appointments, total = await user_service.get_user_appointments(
        user_id=user_uuid,
        page=page,
        size=size,
        status=status
    )
    
    return paginated_response(
        data=[appointment.dict() for appointment in appointments],
        total=total,
        page=page,
        size=size,
        message="User appointments retrieved successfully"
    )