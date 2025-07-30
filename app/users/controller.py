"""
Version-agnostic User Controller

This controller handles HTTP request processing and business logic orchestration
for user-related operations across all API versions. It accepts Union types for
different API version schemas and returns raw data that can be formatted by any version.
"""

from typing import List, Optional, Union, Dict, Any, Tuple
import uuid
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.exceptions import VetClinicException, NotFoundError, ValidationError
from app.models.user import User, UserRole
from .services import UserService


class UserController:
    """Version-agnostic controller for user-related operations."""

    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.service = UserService(db)
        self.db = db

    async def list_users(
        self,
        page: int = 1,
        per_page: int = 10,
        search: Optional[str] = None,
        role: Optional[Union[UserRole, str]] = None,
        is_active: Optional[bool] = None,
        include_roles: bool = False,  # V2 parameter
        **kwargs
    ) -> Tuple[List[User], int]:
        """
        List users with pagination and filtering.
        Handles business rules and validation before delegating to service.
        
        Args:
            page: Page number (1-based)
            per_page: Items per page
            search: Search term for name or email
            role: Filter by user role
            is_active: Filter by active status
            include_roles: Include role information (V2)
            **kwargs: Additional parameters for future versions
            
        Returns:
            Tuple of (users list, total count)
            
        Raises:
            HTTPException: For validation errors or business rule violations
        """
        try:
            # Validate pagination parameters
            if page < 1:
                raise ValidationError("Page must be greater than 0")
            if per_page < 1 or per_page > 100:
                raise ValidationError("Items per page must be between 1 and 100")
            
            # Delegate to service
            users, total = await self.service.list_users(
                page=page,
                per_page=per_page,
                search=search,
                role=role,
                is_active=is_active,
                include_roles=include_roles,
                **kwargs
            )
            
            return users, total
            
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def get_user_by_id(
        self,
        user_id: uuid.UUID,
        include_roles: bool = False,
        include_relationships: bool = False,
        **kwargs
    ) -> User:
        """
        Get user by ID with optional related data.
        
        Args:
            user_id: User UUID
            include_roles: Include role information (V2)
            include_relationships: Include pet/appointment relationships (V2)
            **kwargs: Additional parameters for future versions
            
        Returns:
            User object
            
        Raises:
            HTTPException: If user not found or validation errors
        """
        try:
            user = await self.service.get_user_by_id(
                user_id=user_id,
                include_roles=include_roles,
                include_relationships=include_relationships,
                **kwargs
            )
            return user
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def create_user(
        self,
        user_data: Union[BaseModel, Dict[str, Any]],
        created_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> User:
        """
        Create a new user.
        Accepts Union[UserCreateV1, UserCreateV2] for create operations.
        
        Args:
            user_data: User creation data (V1 or V2 schema)
            created_by: ID of user creating this user
            **kwargs: Additional parameters for future versions
            
        Returns:
            Created user object
            
        Raises:
            HTTPException: For validation errors or business rule violations
        """
        try:
            # Extract data from schema or dict
            if isinstance(user_data, BaseModel):
                data = user_data.model_dump(exclude_unset=True)
            else:
                data = user_data
            
            # Business rule validation
            await self._validate_user_creation(data, created_by)
            
            # Extract common fields
            email = data.get("email")
            first_name = data.get("first_name")
            last_name = data.get("last_name")
            phone_number = data.get("phone_number")
            role = data.get("role", UserRole.PET_OWNER)
            
            # Extract V2 fields if present
            bio = data.get("bio")
            profile_image_url = data.get("profile_image_url")
            department = data.get("department")
            preferences = data.get("preferences")
            clerk_id = data.get("clerk_id")
            
            # Create user
            user = await self.service.create_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                role=role,
                clerk_id=clerk_id,
                bio=bio,
                profile_image_url=profile_image_url,
                department=department,
                preferences=preferences,
                **kwargs
            )
            
            return user
            
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def update_user(
        self,
        user_id: uuid.UUID,
        user_data: Union[BaseModel, Dict[str, Any]],
        updated_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> User:
        """
        Update user information.
        Accepts Union[UserUpdateV1, UserUpdateV2] for update operations.
        
        Args:
            user_id: User UUID
            user_data: User update data (V1 or V2 schema)
            updated_by: ID of user making the update
            **kwargs: Additional parameters for future versions
            
        Returns:
            Updated user object
            
        Raises:
            HTTPException: For validation errors or business rule violations
        """
        try:
            # Extract data from schema or dict
            if isinstance(user_data, BaseModel):
                data = user_data.model_dump(exclude_unset=True)
            else:
                data = user_data
            
            # Business rule validation
            await self._validate_user_update(user_id, data, updated_by)
            
            # Update user
            user = await self.service.update_user(user_id=user_id, **data, **kwargs)
            
            return user
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def delete_user(
        self,
        user_id: uuid.UUID,
        deleted_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Delete a user.
        
        Args:
            user_id: User UUID
            deleted_by: ID of user performing the deletion
            **kwargs: Additional parameters for future versions
            
        Returns:
            Success confirmation
            
        Raises:
            HTTPException: For validation errors or business rule violations
        """
        try:
            # Business rule validation
            await self._validate_user_deletion(user_id, deleted_by)
            
            # Delete user
            await self.service.delete_user(user_id)
            
            return {"success": True, "message": "User deleted successfully"}
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def activate_user(
        self,
        user_id: uuid.UUID,
        activated_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> User:
        """
        Activate a user account.
        
        Args:
            user_id: User UUID
            activated_by: ID of user performing the activation
            **kwargs: Additional parameters for future versions
            
        Returns:
            Activated user object
        """
        try:
            # Business rule validation
            await self._validate_user_status_change(user_id, activated_by)
            
            user = await self.service.activate_user(user_id)
            return user
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def deactivate_user(
        self,
        user_id: uuid.UUID,
        deactivated_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> User:
        """
        Deactivate a user account.
        
        Args:
            user_id: User UUID
            deactivated_by: ID of user performing the deactivation
            **kwargs: Additional parameters for future versions
            
        Returns:
            Deactivated user object
        """
        try:
            # Business rule validation
            await self._validate_user_status_change(user_id, deactivated_by)
            
            user = await self.service.deactivate_user(user_id)
            return user
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def assign_role(
        self,
        user_id: uuid.UUID,
        role: Union[UserRole, str],
        assigned_by: uuid.UUID,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Assign a role to a user.
        
        Args:
            user_id: User UUID
            role: Role to assign
            assigned_by: ID of user assigning the role
            **kwargs: Additional parameters for future versions
            
        Returns:
            Success confirmation
        """
        try:
            # Business rule validation
            await self._validate_role_assignment(user_id, role, assigned_by)
            
            await self.service.assign_role(user_id, role, assigned_by)
            
            return {"success": True, "message": f"Role {role} assigned successfully"}
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def remove_role(
        self,
        user_id: uuid.UUID,
        role: Union[UserRole, str],
        removed_by: uuid.UUID,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Remove a role from a user.
        
        Args:
            user_id: User UUID
            role: Role to remove
            removed_by: ID of user removing the role
            **kwargs: Additional parameters for future versions
            
        Returns:
            Success confirmation
        """
        try:
            # Business rule validation
            await self._validate_role_removal(user_id, role, removed_by)
            
            await self.service.remove_role(user_id, role, removed_by)
            
            return {"success": True, "message": f"Role {role} removed successfully"}
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    # Private helper methods for business rule validation

    async def _validate_user_creation(
        self,
        data: Dict[str, Any],
        created_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for user creation."""
        # Validate required fields
        required_fields = ["email", "first_name", "last_name"]
        for field in required_fields:
            if not data.get(field):
                raise ValidationError(f"{field} is required")
        
        # Validate email format
        email = data.get("email", "")
        if "@" not in email or "." not in email:
            raise ValidationError("Invalid email format")
        
        # Validate role if provided
        role = data.get("role")
        if role and isinstance(role, str):
            try:
                UserRole(role)
            except ValueError:
                raise ValidationError(f"Invalid role: {role}")

    async def _validate_user_update(
        self,
        user_id: uuid.UUID,
        data: Dict[str, Any],
        updated_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for user updates."""
        # Validate email format if provided
        email = data.get("email")
        if email and ("@" not in email or "." not in email):
            raise ValidationError("Invalid email format")
        
        # Additional business rules can be added here
        pass

    async def _validate_user_deletion(
        self,
        user_id: uuid.UUID,
        deleted_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for user deletion."""
        # Check if user exists
        await self.service.get_user_by_id(user_id)
        
        # Prevent self-deletion
        if deleted_by and user_id == deleted_by:
            raise ValidationError("Users cannot delete themselves")
        
        # Additional business rules can be added here
        pass

    async def _validate_user_status_change(
        self,
        user_id: uuid.UUID,
        changed_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for user status changes."""
        # Check if user exists
        await self.service.get_user_by_id(user_id)
        
        # Prevent self status changes in some cases
        if changed_by and user_id == changed_by:
            raise ValidationError("Users cannot change their own status")
        
        # Additional business rules can be added here
        pass

    async def _validate_role_assignment(
        self,
        user_id: uuid.UUID,
        role: Union[UserRole, str],
        assigned_by: uuid.UUID
    ) -> None:
        """Validate business rules for role assignment."""
        # Check if user exists
        await self.service.get_user_by_id(user_id)
        
        # Validate role
        if isinstance(role, str):
            try:
                UserRole(role)
            except ValueError:
                raise ValidationError(f"Invalid role: {role}")
        
        # Additional authorization checks can be added here
        pass

    async def _validate_role_removal(
        self,
        user_id: uuid.UUID,
        role: Union[UserRole, str],
        removed_by: uuid.UUID
    ) -> None:
        """Validate business rules for role removal."""
        # Check if user exists
        await self.service.get_user_by_id(user_id)
        
        # Validate role
        if isinstance(role, str):
            try:
                UserRole(role)
            except ValueError:
                raise ValidationError(f"Invalid role: {role}")
        
        # Additional authorization checks can be added here
        pass