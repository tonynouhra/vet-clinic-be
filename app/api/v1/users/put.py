"""
User PUT endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User, UserRole
from app.services.user_service import UserService
from app.schemas.user_schemas import UserUpdateSchema, UserResponseSchema
from app.app_helpers import (
    get_current_user,
    require_role,
    updated_response,
    validate_uuid,
    validate_email,
    validate_phone
)

router = APIRouter()


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    user_data: UserUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user information.
    
    Users can update their own profile, admins can update any user.
    """
    # Validate UUID format
    user_uuid = validate_uuid(user_id, "user_id")
    
    # Check permissions
    if (str(current_user.id) != user_id and 
        not current_user.has_role(UserRole.CLINIC_ADMIN)):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only update your own profile."
        )
    
    # Validate input data
    update_data = {}
    if user_data.email:
        update_data["email"] = validate_email(user_data.email)
    if user_data.phone_number:
        update_data["phone_number"] = validate_phone(user_data.phone_number)
    if user_data.first_name:
        update_data["first_name"] = user_data.first_name
    if user_data.last_name:
        update_data["last_name"] = user_data.last_name
    if user_data.bio is not None:
        update_data["bio"] = user_data.bio
    if user_data.profile_image_url:
        update_data["profile_image_url"] = user_data.profile_image_url
    
    # Use service layer
    user_service = UserService(db)
    updated_user = await user_service.update_user(
        user_id=user_uuid,
        update_data=update_data,
        updated_by=current_user.id
    )
    
    return updated_response(
        data=UserResponseSchema.from_orm(updated_user).dict(),
        message="User updated successfully"
    )


@router.put("/{user_id}/profile")
async def update_user_profile(
    user_id: str,
    profile_data: dict,  # Should be a proper ProfileUpdateSchema
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user profile information (bio, preferences, etc.).
    
    Users can only update their own profile.
    """
    # Validate UUID format
    user_uuid = validate_uuid(user_id, "user_id")
    
    # Check permissions - only allow users to update their own profile
    if str(current_user.id) != user_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only update your own profile."
        )
    
    # Use service layer
    user_service = UserService(db)
    updated_user = await user_service.update_user_profile(
        user_id=user_uuid,
        profile_data=profile_data
    )
    
    return updated_response(
        data=UserResponseSchema.from_orm(updated_user).dict(),
        message="User profile updated successfully"
    )


@router.put("/{user_id}/password")
async def change_user_password(
    user_id: str,
    password_data: dict,  # Should be a proper PasswordChangeSchema
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user password.
    
    Users can only change their own password.
    """
    # Validate UUID format
    user_uuid = validate_uuid(user_id, "user_id")
    
    # Check permissions - only allow users to change their own password
    if str(current_user.id) != user_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only change your own password."
        )
    
    # Extract password data
    current_password = password_data.get("current_password")
    new_password = password_data.get("new_password")
    
    if not current_password or not new_password:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both current_password and new_password are required"
        )
    
    # Use service layer
    user_service = UserService(db)
    await user_service.change_password(
        user_id=user_uuid,
        current_password=current_password,
        new_password=new_password
    )
    
    return updated_response(
        data=None,
        message="Password changed successfully"
    )


@router.put("/{user_id}/preferences")
async def update_user_preferences(
    user_id: str,
    preferences_data: dict,  # Should be a proper PreferencesSchema
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user preferences (notifications, privacy settings, etc.).
    
    Users can only update their own preferences.
    """
    # Validate UUID format
    user_uuid = validate_uuid(user_id, "user_id")
    
    # Check permissions
    if str(current_user.id) != user_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only update your own preferences."
        )
    
    # Use service layer
    user_service = UserService(db)
    updated_user = await user_service.update_user_preferences(
        user_id=user_uuid,
        preferences=preferences_data
    )
    
    return updated_response(
        data=UserResponseSchema.from_orm(updated_user).dict(),
        message="User preferences updated successfully"
    )