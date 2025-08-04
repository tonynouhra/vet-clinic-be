"""
Version-agnostic User service for data access and core business logic.
Handles all database operations and business rules for users across all API versions.
"""

from typing import List, Tuple, Optional, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, delete
from sqlalchemy.orm import selectinload
from datetime import datetime
import logging

from app.models.user import User, UserRole
from app.core.exceptions import NotFoundError, ConflictError, ValidationError, handle_database_error

logger = logging.getLogger(__name__)


class UserService:
    """Version-agnostic service for user data access and core business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(
        self,
        page: int,
        size: int,
        search: Optional[str] = None,
        role: Optional[Union[UserRole, str]] = None,
        department: Optional[str] = None,  # V2 feature
        timezone: Optional[str] = None,    # V3 feature
        language: Optional[str] = None,    # V3 feature
        is_active: Optional[bool] = None,
        **kwargs  # Handle additional filters from future versions
    ) -> Tuple[List[User], int]:
        """
        Retrieve users with filtering and pagination for all API versions.
        
        Args:
            page: Page number (1-based)
            size: Page size
            search: Search term for name/email
            role: User role filter
            department: Department filter (V2+)
            timezone: Timezone filter (V3+)
            language: Language filter (V3+)
            is_active: Active status filter
            **kwargs: Additional filters from future versions
            
        Returns:
            Tuple[List[User], int]: (users, total_count)
        """
        try:
            # Build base query
            query = select(User)
            count_query = select(func.count(User.id))

            conditions = []

            # Search filter
            if search:
                search_term = f"%{search}%"
                conditions.append(
                    or_(
                        User.first_name.ilike(search_term),
                        User.last_name.ilike(search_term),
                        User.email.ilike(search_term)
                    )
                )

            # Role filter
            if role:
                if isinstance(role, str):
                    try:
                        role = UserRole(role)
                    except ValueError:
                        logger.warning(f"Invalid role filter: {role}")
                        role = None
                
                if role:
                    conditions.append(User.role == role)

            # Department filter (V2+)
            if department and hasattr(User, 'department'):
                conditions.append(User.department == department)

            # Timezone filter (V3+)
            if timezone and hasattr(User, 'timezone'):
                conditions.append(User.timezone == timezone)

            # Language filter (V3+)
            if language and hasattr(User, 'language'):
                conditions.append(User.language == language)

            # Active status filter
            if is_active is not None:
                conditions.append(User.is_active == is_active)

            # Future version filters handled automatically
            for field, value in kwargs.items():
                if value is not None and hasattr(User, field):
                    conditions.append(getattr(User, field) == value)

            # Apply conditions
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))

            # Get total count
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()

            # Apply pagination and ordering
            offset = (page - 1) * size
            query = query.order_by(User.created_at.desc()).offset(offset).limit(size)
            
            # Execute query
            result = await self.db.execute(query)
            users = result.scalars().all()

            return list(users), total

        except Exception as e:
            logger.error(f"Error listing users: {e}")
            raise handle_database_error(e)

    async def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        clerk_id: str,
        phone_number: Optional[str] = None,
        role: Optional[Union[UserRole, str]] = UserRole.PET_OWNER,
        **kwargs  # Handle version-specific fields
    ) -> User:
        """
        Create a new user entity with support for all API versions.
        
        Args:
            email: User email address
            first_name: User first name
            last_name: User last name
            clerk_id: Clerk user ID
            phone_number: Optional phone number
            role: User role
            **kwargs: Additional fields from different API versions
            
        Returns:
            User: Created user entity
        """
        try:
            # Normalize email
            email = email.lower().strip()
            
            # Handle role conversion
            if isinstance(role, str):
                try:
                    role = UserRole(role)
                except ValueError:
                    role = UserRole.PET_OWNER

            # Prepare user data
            user_data = {
                "email": email,
                "first_name": first_name.strip(),
                "last_name": last_name.strip(),
                "clerk_id": clerk_id,
                "phone_number": phone_number,
                "role": role,
            }

            # Add any additional fields that exist in the model
            for field, value in kwargs.items():
                if hasattr(User, field) and value is not None:
                    user_data[field] = value

            # Create user
            new_user = User(**user_data)
            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)

            logger.info(f"Created user: {new_user.id} ({new_user.email})")
            return new_user

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating user: {e}")
            raise handle_database_error(e)

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            Optional[User]: User entity or None if not found
        """
        try:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            raise handle_database_error(e)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email address
            
        Returns:
            Optional[User]: User entity or None if not found
        """
        try:
            email = email.lower().strip()
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            raise handle_database_error(e)

    async def get_user_by_clerk_id(self, clerk_id: str) -> Optional[User]:
        """
        Get user by Clerk ID.
        
        Args:
            clerk_id: Clerk user ID
            
        Returns:
            Optional[User]: User entity or None if not found
        """
        try:
            result = await self.db.execute(
                select(User).where(User.clerk_id == clerk_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by Clerk ID {clerk_id}: {e}")
            raise handle_database_error(e)

    async def update_user(self, user_id: str, **update_data) -> User:
        """
        Update user with support for all API versions.
        
        Args:
            user_id: User ID to update
            **update_data: Fields to update
            
        Returns:
            User: Updated user entity
            
        Raises:
            NotFoundError: If user not found
        """
        try:
            # Get existing user
            user = await self.get_user_by_id(user_id)
            if not user:
                raise NotFoundError(
                    message=f"User with ID {user_id} not found",
                    resource_type="User",
                    resource_id=user_id
                )

            # Prepare update data
            valid_update_data = {}
            for field, value in update_data.items():
                if hasattr(User, field) and value is not None:
                    # Handle special field processing
                    if field == "email":
                        value = value.lower().strip()
                    elif field == "role" and isinstance(value, str):
                        try:
                            value = UserRole(value)
                        except ValueError:
                            continue  # Skip invalid role values
                    
                    valid_update_data[field] = value

            # Update user
            if valid_update_data:
                valid_update_data["updated_at"] = datetime.utcnow()
                
                await self.db.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(**valid_update_data)
                )
                await self.db.commit()
                
                # Refresh user data
                await self.db.refresh(user)

            logger.info(f"Updated user: {user_id}")
            return user

        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating user {user_id}: {e}")
            raise handle_database_error(e)

    async def delete_user(self, user_id: str) -> bool:
        """
        Soft delete user (set is_active to False).
        
        Args:
            user_id: User ID to delete
            
        Returns:
            bool: True if user was deleted
            
        Raises:
            NotFoundError: If user not found
        """
        try:
            # Check if user exists
            user = await self.get_user_by_id(user_id)
            if not user:
                raise NotFoundError(
                    message=f"User with ID {user_id} not found",
                    resource_type="User",
                    resource_id=user_id
                )

            # Soft delete (set inactive)
            await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values(is_active=False, updated_at=datetime.utcnow())
            )
            await self.db.commit()

            logger.info(f"Soft deleted user: {user_id}")
            return True

        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")
            raise handle_database_error(e)

    async def update_last_login(self, user_id: str) -> None:
        """
        Update user's last login timestamp.
        
        Args:
            user_id: User ID
        """
        try:
            await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values(last_login=datetime.utcnow())
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {e}")
            # Don't raise exception for login timestamp updates

    async def get_users_by_role(self, role: Union[UserRole, str]) -> List[User]:
        """
        Get all users with specific role.
        
        Args:
            role: User role to filter by
            
        Returns:
            List[User]: Users with the specified role
        """
        try:
            if isinstance(role, str):
                try:
                    role = UserRole(role)
                except ValueError:
                    return []

            result = await self.db.execute(
                select(User)
                .where(and_(User.role == role, User.is_active == True))
                .order_by(User.created_at.desc())
            )
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting users by role {role}: {e}")
            raise handle_database_error(e)

    async def search_users(
        self,
        search_term: str,
        limit: int = 10,
        role_filter: Optional[Union[UserRole, str]] = None
    ) -> List[User]:
        """
        Search users by name or email.
        
        Args:
            search_term: Search term
            limit: Maximum number of results
            role_filter: Optional role filter
            
        Returns:
            List[User]: Matching users
        """
        try:
            search_pattern = f"%{search_term}%"
            conditions = [
                User.is_active == True,
                or_(
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern),
                    User.email.ilike(search_pattern)
                )
            ]

            if role_filter:
                if isinstance(role_filter, str):
                    try:
                        role_filter = UserRole(role_filter)
                    except ValueError:
                        role_filter = None
                
                if role_filter:
                    conditions.append(User.role == role_filter)

            result = await self.db.execute(
                select(User)
                .where(and_(*conditions))
                .order_by(User.first_name, User.last_name)
                .limit(limit)
            )
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error searching users: {e}")
            raise handle_database_error(e)