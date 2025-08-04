"""
Version-agnostic User controller for HTTP request processing and business logic orchestration.
Handles user-related operations across all API versions with shared business logic.
"""

from typing import List, Optional, Union, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

from app.models.user import User, UserRole
from app.core.exceptions import ValidationError, ConflictError, NotFoundError, BusinessLogicError
from app.app_helpers.validation_helpers import validate_pagination_params, validate_email, validate_uuid
from .services import UserService

logger = logging.getLogger(__name__)


class UserController:
    """Version-agnostic controller for user-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = UserService(db)
        self.current_user: Optional[Dict[str, Any]] = None

    async def list_users(
        self,
        page: int = 1,
        size: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
        department: Optional[str] = None,  # V2 parameter
        timezone: Optional[str] = None,    # V3 parameter
        language: Optional[str] = None,    # V3 parameter
        is_active: Optional[bool] = None,
        **kwargs  # Handle any additional parameters from future versions
    ) -> Dict[str, Any]:
        """
        Handle user listing for all API versions.
        
        Args:
            page: Page number
            size: Page size
            search: Search term
            role: Role filter
            department: Department filter (V2+)
            timezone: Timezone filter (V3+)
            language: Language filter (V3+)
            is_active: Active status filter
            **kwargs: Additional parameters from future versions
            
        Returns:
            Dict containing users and pagination info
        """
        try:
            # Validate pagination
            page, size = validate_pagination_params(page, size)

            # Validate role if provided
            role_enum = None
            if role:
                try:
                    role_enum = UserRole(role)
                except ValueError:
                    raise ValidationError(
                        message="Invalid role value",
                        field="role",
                        value=role,
                        details={"valid_roles": [r.value for r in UserRole]}
                    )

            # Delegate to service
            users, total = await self.service.list_users(
                page=page,
                size=size,
                search=search,
                role=role_enum,
                department=department,
                timezone=timezone,
                language=language,
                is_active=is_active,
                **kwargs
            )

            return {
                "users": users,
                "total": total,
                "page": page,
                "size": size
            }

        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in list_users: {e}")
            raise BusinessLogicError(f"Failed to list users: {str(e)}")

    async def create_user(
        self,
        user_data: Union[Any, Dict[str, Any]]  # Can be any version's schema
    ) -> User:
        """
        Handle user creation for all API versions.
        
        Args:
            user_data: User creation data (any version schema)
            
        Returns:
            User: Created user entity
        """
        try:
            # Extract data from schema or dict
            if hasattr(user_data, 'dict'):
                # Pydantic model
                data = user_data.dict()
            else:
                # Dictionary
                data = user_data

            # Validate required fields
            email = data.get("email")
            first_name = data.get("first_name")
            last_name = data.get("last_name")
            clerk_id = data.get("clerk_id")

            if not all([email, first_name, last_name]):
                raise ValidationError("Email, first_name, and last_name are required")

            # Validate email format
            email = validate_email(email)

            # Check for existing user
            existing_user = await self.service.get_user_by_email(email)
            if existing_user:
                raise ConflictError(
                    message="User with this email already exists",
                    conflicting_resource="email",
                    details={"email": email}
                )

            # Check for existing Clerk ID if provided
            if clerk_id:
                existing_clerk_user = await self.service.get_user_by_clerk_id(clerk_id)
                if existing_clerk_user:
                    raise ConflictError(
                        message="User with this Clerk ID already exists",
                        conflicting_resource="clerk_id",
                        details={"clerk_id": clerk_id}
                    )

            # Extract common fields present in all versions
            create_params = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "clerk_id": clerk_id or f"temp_{datetime.utcnow().timestamp()}",
            }

            # Handle optional fields present in all versions
            if data.get("phone_number"):
                create_params["phone_number"] = data["phone_number"]

            # Handle version-specific fields dynamically
            version_fields = [
                "role", "department", "preferences", "notification_settings",
                "timezone", "language", "avatar_url"
            ]
            
            for field in version_fields:
                if field in data and data[field] is not None:
                    create_params[field] = data[field]

            # Delegate to service
            user = await self.service.create_user(**create_params)
            
            logger.info(f"User created successfully: {user.id}")
            return user

        except (ValidationError, ConflictError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in create_user: {e}")
            raise BusinessLogicError(f"Failed to create user: {str(e)}")

    async def get_user(self, user_id: str) -> User:
        """
        Handle user retrieval for all API versions.
        
        Args:
            user_id: User ID
            
        Returns:
            User: User entity
            
        Raises:
            NotFoundError: If user not found
        """
        try:
            # Validate UUID format
            validate_uuid(user_id, "user_id")

            # Get user from service
            user = await self.service.get_user_by_id(user_id)
            if not user:
                raise NotFoundError(
                    message="User not found",
                    resource_type="User",
                    resource_id=user_id
                )

            return user

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            logger.error(f"Error in get_user: {e}")
            raise BusinessLogicError(f"Failed to get user: {str(e)}")

    async def update_user(
        self,
        user_id: str,
        user_data: Union[Any, Dict[str, Any]]  # Can be any version's schema
    ) -> User:
        """
        Handle user updates for all API versions.
        
        Args:
            user_id: User ID to update
            user_data: Update data (any version schema)
            
        Returns:
            User: Updated user entity
        """
        try:
            # Validate UUID format
            validate_uuid(user_id, "user_id")

            # Extract data from schema or dict
            if hasattr(user_data, 'dict'):
                # Pydantic model - only include set fields
                data = user_data.dict(exclude_unset=True)
            else:
                # Dictionary
                data = user_data

            # Validate email if being updated
            if "email" in data:
                data["email"] = validate_email(data["email"])
                
                # Check for email conflicts
                existing_user = await self.service.get_user_by_email(data["email"])
                if existing_user and str(existing_user.id) != user_id:
                    raise ConflictError(
                        message="User with this email already exists",
                        conflicting_resource="email",
                        details={"email": data["email"]}
                    )

            # Business rule: Only allow certain fields to be updated
            allowed_fields = {
                "first_name", "last_name", "phone_number", "role", "department",
                "preferences", "notification_settings", "timezone", "language",
                "avatar_url", "is_active"
            }
            
            update_params = {
                field: value for field, value in data.items()
                if field in allowed_fields and value is not None
            }

            if not update_params:
                raise ValidationError("No valid fields provided for update")

            # Authorization check: Users can only update their own profile unless admin
            if self.current_user:
                current_user_id = self.current_user.get("user_id")
                current_user_role = self.current_user.get("role")
                
                # Non-admin users can only update their own profile
                if current_user_role != "admin" and current_user_id != user_id:
                    raise BusinessLogicError(
                        "You can only update your own profile",
                        rule="profile_ownership"
                    )
                
                # Non-admin users cannot change their role
                if "role" in update_params and current_user_role != "admin":
                    raise BusinessLogicError(
                        "Only administrators can change user roles",
                        rule="role_change_permission"
                    )

            # Delegate to service
            user = await self.service.update_user(user_id, **update_params)
            
            logger.info(f"User updated successfully: {user_id}")
            return user

        except (ValidationError, ConflictError, NotFoundError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in update_user: {e}")
            raise BusinessLogicError(f"Failed to update user: {str(e)}")

    async def delete_user(self, user_id: str) -> bool:
        """
        Handle user deletion for all API versions.
        
        Args:
            user_id: User ID to delete
            
        Returns:
            bool: True if user was deleted
        """
        try:
            # Validate UUID format
            validate_uuid(user_id, "user_id")

            # Authorization check: Only admins can delete users
            if self.current_user:
                current_user_role = self.current_user.get("role")
                if current_user_role != "admin":
                    raise BusinessLogicError(
                        "Only administrators can delete users",
                        rule="delete_permission"
                    )

            # Business rule: Cannot delete yourself
            if self.current_user and self.current_user.get("user_id") == user_id:
                raise BusinessLogicError(
                    "You cannot delete your own account",
                    rule="self_deletion_prevention"
                )

            # Delegate to service
            result = await self.service.delete_user(user_id)
            
            logger.info(f"User deleted successfully: {user_id}")
            return result

        except (ValidationError, NotFoundError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in delete_user: {e}")
            raise BusinessLogicError(f"Failed to delete user: {str(e)}")

    async def get_current_user_profile(self) -> User:
        """
        Get current authenticated user's profile.
        
        Returns:
            User: Current user entity
        """
        try:
            if not self.current_user:
                raise BusinessLogicError("No authenticated user context")

            user_id = self.current_user.get("user_id")
            if not user_id:
                raise BusinessLogicError("Invalid user context")

            return await self.get_user(user_id)

        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Error in get_current_user_profile: {e}")
            raise BusinessLogicError(f"Failed to get user profile: {str(e)}")

    async def search_users(
        self,
        search_term: str,
        limit: int = 10,
        role_filter: Optional[str] = None
    ) -> List[User]:
        """
        Search users by name or email.
        
        Args:
            search_term: Search term
            limit: Maximum results
            role_filter: Optional role filter
            
        Returns:
            List[User]: Matching users
        """
        try:
            if not search_term or len(search_term.strip()) < 2:
                raise ValidationError(
                    "Search term must be at least 2 characters long",
                    field="search_term",
                    value=search_term
                )

            # Validate role filter if provided
            role_enum = None
            if role_filter:
                try:
                    role_enum = UserRole(role_filter)
                except ValueError:
                    raise ValidationError(
                        message="Invalid role filter",
                        field="role_filter",
                        value=role_filter
                    )

            # Delegate to service
            users = await self.service.search_users(
                search_term=search_term.strip(),
                limit=min(limit, 50),  # Cap at 50 results
                role_filter=role_enum
            )

            return users

        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in search_users: {e}")
            raise BusinessLogicError(f"Failed to search users: {str(e)}")

    async def update_last_login(self, user_id: str) -> None:
        """
        Update user's last login timestamp.
        
        Args:
            user_id: User ID
        """
        try:
            await self.service.update_last_login(user_id)
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            # Don't raise exception for login timestamp updates