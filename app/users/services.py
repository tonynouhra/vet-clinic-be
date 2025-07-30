"""
Version-agnostic User Service

This service handles data access and core business logic for user-related
operations across all API versions. It supports dynamic parameters to
accommodate different API version requirements.
"""

from typing import List, Tuple, Optional, Dict, Any, Union
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, insert, delete
from sqlalchemy.orm import selectinload

from app.models.user import User, UserRole, user_roles
from app.core.exceptions import VetClinicException, NotFoundError, ValidationError


class UserService:
    """Version-agnostic service for user data access and core business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(
        self,
        page: int = 1,
        per_page: int = 10,
        search: Optional[str] = None,
        role: Optional[Union[UserRole, str]] = None,
        is_active: Optional[bool] = None,
        department: Optional[str] = None,  # V2 parameter
        include_roles: bool = False,  # V2 parameter
        **kwargs
    ) -> Tuple[List[User], int]:
        """
        List users with pagination and filtering.
        Supports dynamic parameters for different API versions.
        
        Args:
            page: Page number (1-based)
            per_page: Items per page
            search: Search term for name or email
            role: Filter by user role (supports V1 and V2)
            is_active: Filter by active status
            department: Filter by department (V2 only)
            include_roles: Include role information (V2 only)
            **kwargs: Additional parameters for future versions
            
        Returns:
            Tuple of (users list, total count)
        """
        try:
            # Build base query
            query = select(User)
            count_query = select(func.count(User.id))
            
            # Apply filters
            conditions = []
            
            if search:
                search_term = f"%{search}%"
                conditions.append(
                    or_(
                        User.first_name.ilike(search_term),
                        User.last_name.ilike(search_term),
                        User.email.ilike(search_term)
                    )
                )
            
            if role:
                # Handle both string and enum role filtering
                if isinstance(role, str):
                    try:
                        role = UserRole(role)
                    except ValueError:
                        raise ValidationError(f"Invalid role: {role}")
                
                # Join with user_roles table for role filtering
                query = query.join(user_roles).where(user_roles.c.role == role)
                count_query = count_query.join(user_roles).where(user_roles.c.role == role)
            
            if is_active is not None:
                conditions.append(User.is_active == is_active)
            
            # V2 specific filters
            if department and 'department' in kwargs:
                # Placeholder for department filtering - would need department field in model
                pass
            
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
            
            # Add role information if requested (V2)
            if include_roles:
                query = query.options(selectinload(User.roles))
            
            # Get total count
            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Apply pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page).order_by(User.created_at.desc())
            
            # Execute query
            result = await self.db.execute(query)
            users = result.scalars().all()
            
            return list(users), total
            
        except Exception as e:
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to list users: {str(e)}")

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
            NotFoundError: If user not found
        """
        try:
            query = select(User).where(User.id == user_id)
            
            # Add optional relationships based on version needs
            if include_roles:
                query = query.options(selectinload(User.roles))
            
            if include_relationships:
                query = query.options(
                    selectinload(User.pets),
                    selectinload(User.appointments)
                )
            
            result = await self.db.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise NotFoundError(f"User with id {user_id} not found")
            
            return user
            
        except Exception as e:
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to get user by id: {str(e)}")

    async def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        phone_number: Optional[str] = None,
        role: Optional[Union[UserRole, str]] = UserRole.PET_OWNER,
        clerk_id: Optional[str] = None,
        bio: Optional[str] = None,
        profile_image_url: Optional[str] = None,
        department: Optional[str] = None,  # V2 parameter
        preferences: Optional[Dict[str, Any]] = None,  # V2 parameter
        **kwargs
    ) -> User:
        """
        Create a new user.
        Supports dynamic parameters for different API versions.
        
        Args:
            email: User email
            first_name: User first name
            last_name: User last name
            phone_number: Optional phone number
            role: User role (V1 and V2)
            clerk_id: Clerk user ID
            bio: User biography (V2)
            profile_image_url: Profile image URL (V2)
            department: User department (V2)
            preferences: User preferences (V2)
            **kwargs: Additional parameters for future versions
            
        Returns:
            Created user object
            
        Raises:
            ValidationError: If email already exists or validation fails
        """
        try:
            # Validate email uniqueness
            existing_user = await self.get_user_by_email(email)
            if existing_user:
                raise ValidationError("Email already registered")
            
            # Handle role parameter
            if isinstance(role, str):
                try:
                    role = UserRole(role)
                except ValueError:
                    raise ValidationError(f"Invalid role: {role}")
            
            # Create user data
            user_data = {
                "email": email.lower().strip(),
                "first_name": first_name.strip(),
                "last_name": last_name.strip(),
                "phone_number": phone_number.strip() if phone_number else None,
                "clerk_id": clerk_id or f"temp_{uuid.uuid4()}",  # TODO: Integrate with Clerk
            }
            
            # Add optional V2 parameters
            if bio:
                user_data["bio"] = bio.strip()
            if profile_image_url:
                user_data["profile_image_url"] = profile_image_url
            
            # Create new user
            new_user = User(**user_data)
            
            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)
            
            # Assign role
            if role:
                await self.assign_role(new_user.id, role, new_user.id)
            
            return new_user
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to create user: {str(e)}")

    async def update_user(
        self,
        user_id: uuid.UUID,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        bio: Optional[str] = None,
        profile_image_url: Optional[str] = None,
        is_active: Optional[bool] = None,
        department: Optional[str] = None,  # V2 parameter
        preferences: Optional[Dict[str, Any]] = None,  # V2 parameter
        **kwargs
    ) -> User:
        """
        Update user information.
        Supports dynamic parameters for different API versions.
        
        Args:
            user_id: User UUID
            email: New email address
            first_name: New first name
            last_name: New last name
            phone_number: New phone number
            bio: New biography (V2)
            profile_image_url: New profile image URL (V2)
            is_active: New active status
            department: New department (V2)
            preferences: New preferences (V2)
            **kwargs: Additional parameters for future versions
            
        Returns:
            Updated user object
        """
        try:
            user = await self.get_user_by_id(user_id)
            
            # Update fields if provided
            update_data = {}
            if email is not None:
                # Check email uniqueness if changing
                if email.lower() != user.email:
                    existing_user = await self.get_user_by_email(email)
                    if existing_user:
                        raise ValidationError("Email already registered")
                update_data["email"] = email.lower().strip()
            
            if first_name is not None:
                update_data["first_name"] = first_name.strip()
            if last_name is not None:
                update_data["last_name"] = last_name.strip()
            if phone_number is not None:
                update_data["phone_number"] = phone_number.strip() if phone_number else None
            if bio is not None:
                update_data["bio"] = bio.strip() if bio else None
            if profile_image_url is not None:
                update_data["profile_image_url"] = profile_image_url
            if is_active is not None:
                update_data["is_active"] = is_active
            
            # Apply updates
            for field, value in update_data.items():
                setattr(user, field, value)
            
            await self.db.commit()
            await self.db.refresh(user)
            
            return user
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to update user: {str(e)}")

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email
            
        Returns:
            User object or None if not found
        """
        try:
            query = select(User).where(User.email == email.lower().strip())
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            raise VetClinicException(f"Failed to get user by email: {str(e)}")

    async def assign_role(
        self,
        user_id: uuid.UUID,
        role: Union[UserRole, str],
        assigned_by: uuid.UUID
    ) -> None:
        """
        Assign a role to a user.
        
        Args:
            user_id: User UUID
            role: Role to assign
            assigned_by: ID of user assigning the role
        """
        try:
            if isinstance(role, str):
                role = UserRole(role)
            
            # Check if role already assigned
            existing_query = select(user_roles).where(
                and_(
                    user_roles.c.user_id == user_id,
                    user_roles.c.role == role
                )
            )
            result = await self.db.execute(existing_query)
            if result.first():
                return  # Role already assigned
            
            # Insert new role assignment
            insert_stmt = insert(user_roles).values(
                user_id=user_id,
                role=role,
                assigned_by=assigned_by
            )
            await self.db.execute(insert_stmt)
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            raise VetClinicException(f"Failed to assign role: {str(e)}")

    async def remove_role(
        self,
        user_id: uuid.UUID,
        role: Union[UserRole, str],
        removed_by: uuid.UUID
    ) -> None:
        """
        Remove a role from a user.
        
        Args:
            user_id: User UUID
            role: Role to remove
            removed_by: ID of user removing the role
        """
        try:
            if isinstance(role, str):
                role = UserRole(role)
            
            delete_stmt = delete(user_roles).where(
                and_(
                    user_roles.c.user_id == user_id,
                    user_roles.c.role == role
                )
            )
            await self.db.execute(delete_stmt)
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            raise VetClinicException(f"Failed to remove role: {str(e)}")

    async def delete_user(self, user_id: uuid.UUID) -> None:
        """
        Hard delete a user and related data.
        
        Args:
            user_id: User UUID
        """
        try:
            user = await self.get_user_by_id(user_id)
            
            # Delete role assignments first
            delete_roles_stmt = delete(user_roles).where(user_roles.c.user_id == user_id)
            await self.db.execute(delete_roles_stmt)
            
            # Delete user
            await self.db.delete(user)
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to delete user: {str(e)}")

    async def activate_user(self, user_id: uuid.UUID) -> User:
        """Activate a user account."""
        return await self.update_user(user_id, is_active=True)

    async def deactivate_user(self, user_id: uuid.UUID) -> User:
        """Deactivate a user account."""
        return await self.update_user(user_id, is_active=False)