"""
User POST endpoints.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User, UserRole
from app.services.user_service import UserService
from app.schemas.user_schemas import UserCreateSchema, UserResponseSchema
from app.app_helpers import (
    get_current_user,
    require_role,
    created_response,
    validate_email,
    validate_phone
)

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateSchema,
    current_user: User = Depends(require_role(UserRole.CLINIC_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user.
    
    Requires clinic admin role or higher.
    """
    # Validate input data
    validated_email = validate_email(user_data.email)
    validated_phone = validate_phone(user_data.phone_number) if user_data.phone_number else None
    
    # Use service layer for business logic
    user_service = UserService(db)
    new_user = await user_service.create_user(
        email=validated_email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone_number=validated_phone,
        role=user_data.role,
        created_by=current_user.id
    )
    
    return created_response(
        data=UserResponseSchema.from_orm(new_user).dict(),
        message="User created successfully"
    )


@router.post("/register")
async def register_user(
    user_data: UserCreateSchema,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user (public endpoint for self-registration).
    
    This endpoint allows users to register themselves as pet owners.
    """
    # Validate input data
    validated_email = validate_email(user_data.email)
    validated_phone = validate_phone(user_data.phone_number) if user_data.phone_number else None
    
    # Force role to pet_owner for self-registration
    if user_data.role and user_data.role != UserRole.PET_OWNER:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-registration is only allowed for pet owners"
        )
    
    # Use service layer
    user_service = UserService(db)
    new_user = await user_service.register_user(
        email=validated_email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone_number=validated_phone,
        clerk_id=user_data.clerk_id
    )
    
    return created_response(
        data=UserResponseSchema.from_orm(new_user).dict(),
        message="User registered successfully"
    )


@router.post("/{user_id}/roles")
async def assign_user_role(
    user_id: str,
    role_data: dict,  # Should be a proper schema
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Assign a role to a user.
    
    Requires system admin role.
    """
    from app.app_helpers import validate_uuid
    
    # Validate UUID format
    user_uuid = validate_uuid(user_id, "user_id")
    
    # Extract role from request
    role = UserRole(role_data.get("role"))
    
    # Use service layer
    user_service = UserService(db)
    await user_service.assign_role(
        user_id=user_uuid,
        role=role,
        assigned_by=current_user.id
    )
    
    return created_response(
        data={"user_id": user_id, "role": role.value},
        message="Role assigned successfully"
    )


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: User = Depends(require_role(UserRole.CLINIC_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Activate a user account.
    
    Requires clinic admin role or higher.
    """
    from app.app_helpers import validate_uuid
    
    # Validate UUID format
    user_uuid = validate_uuid(user_id, "user_id")
    
    # Use service layer
    user_service = UserService(db)
    user = await user_service.activate_user(user_uuid)
    
    return created_response(
        data=UserResponseSchema.from_orm(user).dict(),
        message="User activated successfully"
    )


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(require_role(UserRole.CLINIC_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate a user account.
    
    Requires clinic admin role or higher.
    """
    from app.app_helpers import validate_uuid
    
    # Validate UUID format
    user_uuid = validate_uuid(user_id, "user_id")
    
    # Prevent self-deactivation
    if str(current_user.id) == user_id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account"
        )
    
    # Use service layer
    user_service = UserService(db)
    user = await user_service.deactivate_user(user_uuid)
    
    return created_response(
        data=UserResponseSchema.from_orm(user).dict(),
        message="User deactivated successfully"
    )