"""
User DELETE endpoints.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User, UserRole
from app.services.user_service import UserService
from app.app_helpers import (
    get_current_user,
    require_role,
    deleted_response,
    validate_uuid
)

router = APIRouter()


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a user account (hard delete).
    
    Requires system admin role. This is a permanent action.
    """
    # Validate UUID format
    user_uuid = validate_uuid(user_id, "user_id")
    
    # Prevent self-deletion
    if str(current_user.id) == user_id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )
    
    # Use service layer
    user_service = UserService(db)
    await user_service.delete_user(user_uuid)
    
    return deleted_response(
        message="User deleted successfully"
    )


@router.delete("/{user_id}/soft")
async def soft_delete_user(
    user_id: str,
    current_user: User = Depends(require_role(UserRole.CLINIC_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete a user account (deactivate).
    
    Requires clinic admin role or higher. This can be reversed.
    """
    # Validate UUID format
    user_uuid = validate_uuid(user_id, "user_id")
    
    # Prevent self-deletion
    if str(current_user.id) == user_id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )
    
    # Use service layer
    user_service = UserService(db)
    await user_service.soft_delete_user(user_uuid)
    
    return deleted_response(
        message="User account deactivated successfully"
    )


@router.delete("/{user_id}/roles/{role}")
async def remove_user_role(
    user_id: str,
    role: UserRole,
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a role from a user.
    
    Requires system admin role.
    """
    # Validate UUID format
    user_uuid = validate_uuid(user_id, "user_id")
    
    # Prevent removing roles from self
    if str(current_user.id) == user_id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove roles from your own account"
        )
    
    # Use service layer
    user_service = UserService(db)
    await user_service.remove_role(
        user_id=user_uuid,
        role=role,
        removed_by=current_user.id
    )
    
    return deleted_response(
        message=f"Role {role.value} removed from user successfully"
    )


@router.delete("/{user_id}/sessions")
async def revoke_user_sessions(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke all active sessions for a user.
    
    Users can revoke their own sessions, admins can revoke any user's sessions.
    """
    # Validate UUID format
    user_uuid = validate_uuid(user_id, "user_id")
    
    # Check permissions
    if (str(current_user.id) != user_id and 
        not current_user.has_role(UserRole.CLINIC_ADMIN)):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only revoke your own sessions."
        )
    
    # Use service layer
    user_service = UserService(db)
    revoked_count = await user_service.revoke_user_sessions(user_uuid)
    
    return deleted_response(
        message=f"Successfully revoked {revoked_count} active sessions"
    )


@router.delete("/{user_id}/data")
async def delete_user_data(
    user_id: str,
    data_type: str,  # Query parameter for type of data to delete
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete specific user data (GDPR compliance).
    
    Users can delete their own data, admins can delete any user's data.
    Supported data types: 'messages', 'appointments', 'health_records', 'all'
    """
    # Validate UUID format
    user_uuid = validate_uuid(user_id, "user_id")
    
    # Check permissions
    if (str(current_user.id) != user_id and 
        not current_user.has_role(UserRole.CLINIC_ADMIN)):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only delete your own data."
        )
    
    # Validate data type
    allowed_types = ['messages', 'appointments', 'health_records', 'all']
    if data_type not in allowed_types:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data type. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Use service layer
    user_service = UserService(db)
    deleted_count = await user_service.delete_user_data(
        user_id=user_uuid,
        data_type=data_type
    )
    
    return deleted_response(
        message=f"Successfully deleted {deleted_count} {data_type} records"
    )