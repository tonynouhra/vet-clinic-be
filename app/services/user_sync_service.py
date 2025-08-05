"""
User synchronization service for Clerk authentication integration.
Handles creating, updating, and deleting local users based on Clerk data.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.schemas.clerk_schemas import (
    ClerkUser,
    ClerkRoleMapping,
    ClerkUserTransform,
    ClerkUserValidation,
    ClerkUserSyncResponse
)
from app.core.exceptions import AuthenticationError
from app.services.auth_cache_service import get_auth_cache_service

logger = logging.getLogger(__name__)


class UserSyncService:
    """Service for synchronizing users between Clerk and local database."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.role_mapping = ClerkRoleMapping()
        self.cache_service = get_auth_cache_service()

    async def create_user_from_clerk(self, clerk_user: ClerkUser) -> User:
        """
        Create a new local user from Clerk user data.

        Args:
            clerk_user: Clerk user data

        Returns:
            Created User object

        Raises:
            HTTPException: If user creation fails or validation errors
        """
        try:
            # Validate Clerk user data
            validation_errors = ClerkUserValidation.validate_user_data(clerk_user)
            if validation_errors:
                logger.error("Clerk user validation failed: %s", validation_errors)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid Clerk user data: {', '.join(validation_errors)}"
                )

            # Check if user already exists
            existing_user = await self.get_user_by_clerk_id(clerk_user.id)
            if existing_user:
                logger.warning("User with Clerk ID %s already exists", clerk_user.id)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User already exists"
                )

            # Check if email is already in use
            if clerk_user.primary_email:
                existing_email_user = await self.get_user_by_email(clerk_user.primary_email)
                if existing_email_user:
                    logger.warning("User with email %s already exists", clerk_user.primary_email)
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Email already in use"
                    )

            # Transform Clerk data to user creation data
            user_data = ClerkUserTransform.to_user_create_data(clerk_user, self.role_mapping)

            # Create new user
            new_user = User(**user_data)
            
            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)

            # Cache the new user data
            await self.cache_service.cache_user_data(new_user)

            logger.info("Created user from Clerk: %s (%s)", new_user.email, new_user.id)
            return new_user

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to create user from Clerk data: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            ) from e

    async def update_user_from_clerk(self, user: User, clerk_user: ClerkUser) -> User:
        """
        Update existing local user with Clerk user data.

        Args:
            user: Existing User object
            clerk_user: Updated Clerk user data

        Returns:
            Updated User object

        Raises:
            HTTPException: If update fails or validation errors
        """
        try:
            # Validate Clerk user data
            validation_errors = ClerkUserValidation.validate_user_data(clerk_user)
            if validation_errors:
                logger.error("Clerk user validation failed: %s", validation_errors)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid Clerk user data: {', '.join(validation_errors)}"
                )

            # Transform Clerk data to user update data
            update_data = ClerkUserTransform.to_user_update_data(clerk_user, self.role_mapping)

            # Check if email is changing and if new email is available
            if "email" in update_data and update_data["email"] != user.email:
                existing_email_user = await self.get_user_by_email(update_data["email"])
                if existing_email_user and existing_email_user.id != user.id:
                    logger.warning("Email %s already in use by another user", update_data["email"])
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Email already in use"
                    )

            # Update user fields
            for field, value in update_data.items():
                if hasattr(user, field):
                    setattr(user, field, value)

            # Update timestamp
            user.updated_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(user)

            # Update cache with new user data
            await self.cache_service.cache_user_data(user)

            logger.info("Updated user from Clerk: %s (%s)", user.email, user.id)
            return user

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to update user from Clerk data: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            ) from e

    async def handle_user_deletion(self, clerk_id: str) -> None:
        """
        Handle user deletion from Clerk.
        Performs soft delete by deactivating the user and cleaning up sensitive data.

        Args:
            clerk_id: Clerk user ID

        Raises:
            HTTPException: If deletion handling fails
        """
        try:
            user = await self.get_user_by_clerk_id(clerk_id)
            if not user:
                logger.warning("User with Clerk ID %s not found for deletion", clerk_id)
                return

            # Soft delete: deactivate user and clear sensitive data
            user.is_active = False
            user.is_verified = False
            
            # Clear sensitive personal data while keeping essential records
            user.phone_number = None
            user.avatar_url = None
            user.preferences = {}
            user.notification_settings = {}
            
            # Keep email and name for audit trail but mark as deleted
            user.email = f"deleted_{user.id}@deleted.local"
            user.first_name = "Deleted"
            user.last_name = "User"
            
            user.updated_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(user)

            # Invalidate all cache entries for this user
            await self.cache_service.invalidate_user_related_cache(clerk_id, str(user.id))

            logger.info("Handled user deletion for Clerk ID: %s (User ID: %s)", clerk_id, user.id)

        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to handle user deletion for Clerk ID %s: %s", clerk_id, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to handle user deletion"
            ) from e

    async def sync_user_data(
        self, 
        clerk_user: ClerkUser, 
        force_update: bool = False
    ) -> ClerkUserSyncResponse:
        """
        Synchronize user data between Clerk and local database.
        Creates new user if doesn't exist, updates if exists.

        Args:
            clerk_user: Clerk user data
            force_update: Force update even if data hasn't changed

        Returns:
            ClerkUserSyncResponse with sync results
        """
        try:
            # Check if user exists
            existing_user = await self.get_user_by_clerk_id(clerk_user.id)

            if existing_user:
                # User exists, check if update is needed
                if force_update or self._should_update_user(existing_user, clerk_user):
                    updated_user = await self.update_user_from_clerk(existing_user, clerk_user)
                    return ClerkUserSyncResponse(
                        success=True,
                        user_id=str(updated_user.id),
                        action="updated",
                        message=f"User {updated_user.email} updated successfully"
                    )
                else:
                    return ClerkUserSyncResponse(
                        success=True,
                        user_id=str(existing_user.id),
                        action="skipped",
                        message=f"User {existing_user.email} is up to date"
                    )
            else:
                # User doesn't exist, create new
                new_user = await self.create_user_from_clerk(clerk_user)
                return ClerkUserSyncResponse(
                    success=True,
                    user_id=str(new_user.id),
                    action="created",
                    message=f"User {new_user.email} created successfully"
                )

        except HTTPException as e:
            return ClerkUserSyncResponse(
                success=False,
                action="failed",
                message=str(e.detail),
                errors=[str(e.detail)]
            )
        except Exception as e:
            logger.error("User sync failed for Clerk ID %s: %s", clerk_user.id, str(e))
            return ClerkUserSyncResponse(
                success=False,
                action="failed",
                message="User synchronization failed",
                errors=[str(e)]
            )

    async def get_user_by_clerk_id(self, clerk_id: str) -> Optional[User]:
        """
        Get user by Clerk ID.

        Args:
            clerk_id: Clerk user ID

        Returns:
            User object or None if not found
        """
        try:
            query = select(User).where(User.clerk_id == clerk_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get user by Clerk ID %s: %s", clerk_id, str(e))
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User email

        Returns:
            User object or None if not found
        """
        try:
            query = select(User).where(User.email == email.lower())
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get user by email %s: %s", email, str(e))
            return None

    async def get_users_by_role(self, role: UserRole) -> List[User]:
        """
        Get all users with a specific role.

        Args:
            role: User role to filter by

        Returns:
            List of User objects
        """
        try:
            query = select(User).where(and_(User.role == role, User.is_active == True))
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error("Failed to get users by role %s: %s", role, str(e))
            return []

    async def cleanup_inactive_users(self, days_inactive: int = 90) -> int:
        """
        Clean up users who have been inactive for a specified period.
        This is a maintenance operation for data cleanup.

        Args:
            days_inactive: Number of days of inactivity before cleanup

        Returns:
            Number of users cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_inactive)
            
            query = select(User).where(
                and_(
                    User.is_active == False,
                    User.updated_at < cutoff_date,
                    User.email.like("deleted_%@deleted.local")
                )
            )
            
            result = await self.db.execute(query)
            inactive_users = result.scalars().all()
            
            cleanup_count = 0
            for user in inactive_users:
                # Additional cleanup - remove remaining data
                user.preferences = {}
                user.notification_settings = {}
                cleanup_count += 1
            
            if cleanup_count > 0:
                await self.db.commit()
                logger.info("Cleaned up %d inactive users", cleanup_count)
            
            return cleanup_count

        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to cleanup inactive users: %s", str(e))
            return 0

    def _should_update_user(self, user: User, clerk_user: ClerkUser) -> bool:
        """
        Check if user should be updated based on Clerk data.

        Args:
            user: Existing User object
            clerk_user: Clerk user data

        Returns:
            True if user should be updated
        """
        # Check if basic fields have changed
        if user.email != clerk_user.primary_email:
            return True
        
        if user.first_name != clerk_user.first_name:
            return True
        
        if user.last_name != clerk_user.last_name:
            return True
        
        if user.phone_number != clerk_user.primary_phone:
            return True
        
        if user.avatar_url != clerk_user.image_url:
            return True
        
        # Check role changes
        clerk_role = clerk_user.public_metadata.get("role")
        internal_role = self.role_mapping.get_internal_role(clerk_role)
        if user.role != internal_role:
            return True
        
        # Check status changes
        is_active = not clerk_user.banned and not clerk_user.locked
        if user.is_active != is_active:
            return True
        
        # Check if Clerk data is newer
        if clerk_user.updated_at_datetime > user.updated_at:
            return True
        
        return False

    async def validate_user_permissions(self, user: User, required_permission: str) -> bool:
        """
        Validate if user has required permission.

        Args:
            user: User object
            required_permission: Permission to check

        Returns:
            True if user has permission
        """
        try:
            return user.has_permission(required_permission)
        except Exception as e:
            logger.error("Failed to validate user permissions: %s", str(e))
            return False

    async def get_sync_statistics(self) -> Dict[str, Any]:
        """
        Get synchronization statistics for monitoring.

        Returns:
            Dictionary with sync statistics
        """
        try:
            # Count users by role
            role_counts = {}
            for role in UserRole:
                users = await self.get_users_by_role(role)
                role_counts[role.value] = len(users)
            
            # Count active vs inactive users
            active_query = select(User).where(User.is_active == True)
            active_result = await self.db.execute(active_query)
            active_count = len(list(active_result.scalars().all()))
            
            inactive_query = select(User).where(User.is_active == False)
            inactive_result = await self.db.execute(inactive_query)
            inactive_count = len(list(inactive_result.scalars().all()))
            
            return {
                "total_users": active_count + inactive_count,
                "active_users": active_count,
                "inactive_users": inactive_count,
                "users_by_role": role_counts,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get sync statistics: %s", str(e))
            return {
                "error": str(e),
                "last_updated": datetime.utcnow().isoformat()
            }


# Import timedelta for cleanup function
from datetime import timedelta