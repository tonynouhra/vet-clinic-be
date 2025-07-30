"""
User service layer - Business logic for user operations.
"""
from typing import Optional, Tuple, List
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from fastapi import HTTPException, status

from app.models import User, UserRole, UserSession
from app.core.database import get_db


class UserService:
    """Service class for user-related business logic."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def list_users(
        self,
        page: int = 1,
        size: int = 20,
        search: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[User], int]:
        """
        List users with pagination and filtering.
        
        Args:
            page: Page number (1-based)
            size: Items per page
            search: Search term for name or email
            role: Filter by user role
            is_active: Filter by active status
            
        Returns:
            Tuple of (users list, total count)
        """
        # Build query
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
            # TODO: Implement role filtering with proper join
            pass
        
        if is_active is not None:
            conditions.append(User.is_active == is_active)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        # Execute query
        result = await self.db.execute(query)
        users = result.scalars().all()
        
        return list(users), total
    
    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        """
        Get user by ID.
        
        Args:
            user_id: User UUID
            
        Returns:
            User object
            
        Raises:
            HTTPException: If user not found
        """
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user
    
    async def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        phone_number: Optional[str] = None,
        role: UserRole = UserRole.PET_OWNER,
        created_by: Optional[uuid.UUID] = None
    ) -> User:
        """
        Create a new user.
        
        Args:
            email: User email
            first_name: User first name
            last_name: User last name
            phone_number: Optional phone number
            role: User role
            created_by: ID of user creating this user
            
        Returns:
            Created user object
            
        Raises:
            HTTPException: If email already exists
        """
        # Check if email already exists
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        new_user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            clerk_id=f"temp_{uuid.uuid4()}"  # TODO: Integrate with Clerk
        )
        
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        
        # TODO: Assign role using proper role assignment
        
        return new_user
    
    async def register_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        phone_number: Optional[str] = None,
        clerk_id: str = None
    ) -> User:
        """
        Register a new user (self-registration).
        
        Args:
            email: User email
            first_name: User first name
            last_name: User last name
            phone_number: Optional phone number
            clerk_id: Clerk user ID
            
        Returns:
            Registered user object
        """
        return await self.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            role=UserRole.PET_OWNER
        )
    
    async def update_user(
        self,
        user_id: uuid.UUID,
        update_data: dict,
        updated_by: Optional[uuid.UUID] = None
    ) -> User:
        """
        Update user information.
        
        Args:
            user_id: User UUID
            update_data: Dictionary of fields to update
            updated_by: ID of user making the update
            
        Returns:
            Updated user object
        """
        user = await self.get_user_by_id(user_id)
        
        # Update fields
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def delete_user(self, user_id: uuid.UUID) -> None:
        """
        Hard delete a user.
        
        Args:
            user_id: User UUID
        """
        user = await self.get_user_by_id(user_id)
        await self.db.delete(user)
        await self.db.commit()
    
    async def soft_delete_user(self, user_id: uuid.UUID) -> None:
        """
        Soft delete a user (deactivate).
        
        Args:
            user_id: User UUID
        """
        await self.update_user(user_id, {"is_active": False})
    
    async def activate_user(self, user_id: uuid.UUID) -> User:
        """
        Activate a user account.
        
        Args:
            user_id: User UUID
            
        Returns:
            Activated user object
        """
        return await self.update_user(user_id, {"is_active": True})
    
    async def deactivate_user(self, user_id: uuid.UUID) -> User:
        """
        Deactivate a user account.
        
        Args:
            user_id: User UUID
            
        Returns:
            Deactivated user object
        """
        return await self.update_user(user_id, {"is_active": False})
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email
            
        Returns:
            User object or None if not found
        """
        query = select(User).where(User.email == email.lower())
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_pets(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        size: int = 20
    ) -> Tuple[List, int]:
        """
        Get pets owned by a user.
        
        Args:
            user_id: User UUID
            page: Page number
            size: Items per page
            
        Returns:
            Tuple of (pets list, total count)
        """
        # TODO: Implement with proper Pet model relationship
        return [], 0
    
    async def get_user_appointments(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        size: int = 20,
        status: Optional[str] = None
    ) -> Tuple[List, int]:
        """
        Get appointments for a user.
        
        Args:
            user_id: User UUID
            page: Page number
            size: Items per page
            status: Optional status filter
            
        Returns:
            Tuple of (appointments list, total count)
        """
        # TODO: Implement with proper Appointment model relationship
        return [], 0
    
    async def assign_role(
        self,
        user_id: uuid.UUID,
        role: UserRole,
        assigned_by: uuid.UUID
    ) -> None:
        """
        Assign a role to a user.
        
        Args:
            user_id: User UUID
            role: Role to assign
            assigned_by: ID of user assigning the role
        """
        # TODO: Implement role assignment with user_roles table
        pass
    
    async def remove_role(
        self,
        user_id: uuid.UUID,
        role: UserRole,
        removed_by: uuid.UUID
    ) -> None:
        """
        Remove a role from a user.
        
        Args:
            user_id: User UUID
            role: Role to remove
            removed_by: ID of user removing the role
        """
        # TODO: Implement role removal with user_roles table
        pass
    
    async def revoke_user_sessions(self, user_id: uuid.UUID) -> int:
        """
        Revoke all active sessions for a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            Number of sessions revoked
        """
        # TODO: Implement session revocation
        return 0
    
    async def delete_user_data(
        self,
        user_id: uuid.UUID,
        data_type: str
    ) -> int:
        """
        Delete specific user data for GDPR compliance.
        
        Args:
            user_id: User UUID
            data_type: Type of data to delete
            
        Returns:
            Number of records deleted
        """
        # TODO: Implement data deletion based on type
        return 0
    
    async def update_user_profile(
        self,
        user_id: uuid.UUID,
        profile_data: dict
    ) -> User:
        """
        Update user profile information.
        
        Args:
            user_id: User UUID
            profile_data: Profile data to update
            
        Returns:
            Updated user object
        """
        return await self.update_user(user_id, profile_data)
    
    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str
    ) -> None:
        """
        Change user password.
        
        Args:
            user_id: User UUID
            current_password: Current password
            new_password: New password
        """
        # TODO: Implement password change with proper hashing and validation
        pass
    
    async def update_user_preferences(
        self,
        user_id: uuid.UUID,
        preferences: dict
    ) -> User:
        """
        Update user preferences.
        
        Args:
            user_id: User UUID
            preferences: Preferences data
            
        Returns:
            Updated user object
        """
        # TODO: Implement preferences update (might be JSON field)
        return await self.update_user(user_id, {"preferences": preferences})