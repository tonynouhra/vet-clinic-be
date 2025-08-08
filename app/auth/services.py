"""
Version-agnostic Authentication service for data access and core business logic.
Handles all authentication operations and business rules across all API versions.
"""

import hashlib
import secrets
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta
import logging

from app.models.user import User, UserRole
from app.core.exceptions import (
    AuthenticationError, 
    ValidationError, 
    ConflictError,
    handle_database_error
)
from app.core.config import get_settings
from app.services.session_service import get_session_service
from app.app_helpers.auth_helpers import create_access_token, get_user_permissions

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthService:
    """Version-agnostic service for authentication data access and core business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_service = get_session_service()

    def _hash_password(self, password: str) -> str:
        """
        Hash password using SHA-256 with salt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        # Generate a random salt
        salt = secrets.token_hex(16)
        
        # Hash password with salt
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        
        # Return salt + hash
        return f"{salt}:{password_hash}"

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            password: Plain text password
            hashed_password: Stored hash
            
        Returns:
            True if password matches
        """
        try:
            if ":" not in hashed_password:
                return False
            
            salt, stored_hash = hashed_password.split(":", 1)
            password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            
            return password_hash == stored_hash
        except Exception:
            return False

    async def create_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone_number: Optional[str] = None,
        role: UserRole = UserRole.PET_OWNER,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> User:
        """
        Create a new user for local development/testing.
        
        Note: In production, users are created through Clerk's frontend SDK.
        This method is primarily for development and testing scenarios.
        
        Args:
            email: User email
            password: Plain text password (not stored, used for Clerk integration)
            first_name: User first name
            last_name: User last name
            phone_number: Optional phone number
            role: User role
            ip_address: Registration IP address
            user_agent: Registration user agent
            
        Returns:
            Created user entity
        """
        try:
            # Normalize email
            email = email.lower().strip()
            
            # Generate temporary clerk_id for development/testing
            clerk_id = f"temp_{secrets.token_hex(8)}"
            
            # Create user (without password_hash since we use Clerk)
            user_data = {
                "email": email,
                "first_name": first_name.strip(),
                "last_name": last_name.strip(),
                "phone_number": phone_number,
                "role": role,
                "clerk_id": clerk_id,
                "is_active": True,
                "is_verified": False  # Email verification required
            }

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

    async def authenticate_user(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate user for development/testing.
        
        Note: In production, authentication is handled by Clerk's frontend SDK.
        This method is primarily for development and testing scenarios.
        
        Args:
            email: User email
            password: Plain text password (for development testing)
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Dict containing authentication result
        """
        try:
            # Normalize email
            email = email.lower().strip()
            
            # Get user by email
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {
                    "success": False,
                    "message": "Invalid email or password"
                }
            
            # Check if user is active
            if not user.is_active:
                return {
                    "success": False,
                    "message": "Account is deactivated"
                }
            
            # For development/testing, accept any password for temp users
            # In production, this would be handled by Clerk
            if not user.clerk_id.startswith("temp_"):
                return {
                    "success": False,
                    "message": "Authentication must be done through Clerk"
                }
            
            # Update last login
            await self.db.execute(
                update(User)
                .where(User.id == user.id)
                .values(last_login=datetime.utcnow())
            )
            await self.db.commit()
            
            # Create session
            permissions = get_user_permissions(user.role.value)
            session_data = await self.session_service.create_session(
                user_id=str(user.id),
                clerk_id=user.clerk_id,
                email=user.email,
                role=user.role.value,
                permissions=permissions,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Create access token
            access_token = create_access_token(
                user_id=str(user.id),
                email=user.email,
                role=user.role.value,
                clerk_id=user.clerk_id,
                permissions=permissions
            )
            
            return {
                "success": True,
                "user": user,
                "session": {
                    "session_id": session_data["session_id"],
                    "access_token": access_token,
                    "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    "refresh_token": None  # Implement refresh tokens later
                }
            }
            
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return {
                "success": False,
                "message": "Authentication failed"
            }

    async def logout_session(self, session_id: str) -> bool:
        """
        Logout from a specific session.
        
        Args:
            session_id: Session ID to logout
            
        Returns:
            True if session was logged out
        """
        try:
            return await self.session_service.invalidate_session(session_id)
        except Exception as e:
            logger.error(f"Error logging out session: {e}")
            return False

    async def logout_all_sessions(
        self, 
        user_id: str, 
        exclude_session: Optional[str] = None
    ) -> int:
        """
        Logout from all user sessions.
        
        Args:
            user_id: User ID
            exclude_session: Session to exclude from logout
            
        Returns:
            Number of sessions logged out
        """
        try:
            return await self.session_service.invalidate_user_sessions(
                user_id, exclude_session
            )
        except Exception as e:
            logger.error(f"Error logging out all sessions: {e}")
            return 0

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dict containing new token information
        """
        # TODO: Implement refresh token logic
        # For now, return error as refresh tokens are not implemented
        return {
            "success": False,
            "message": "Refresh tokens not implemented yet"
        }

    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Change user password.
        
        Note: In production, password changes are handled by Clerk.
        This method is for development/testing scenarios.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            
        Returns:
            Dict containing password change result
        """
        try:
            # Get user
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {
                    "success": False,
                    "message": "User not found"
                }
            
            # For production users with real Clerk IDs, redirect to Clerk
            if not user.clerk_id.startswith("temp_"):
                return {
                    "success": False,
                    "message": "Password changes must be done through Clerk"
                }
            
            # For development/testing users, simulate password change
            # Update user timestamp to indicate change
            await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values(updated_at=datetime.utcnow())
            )
            await self.db.commit()
            
            # Invalidate all sessions except current one (force re-login)
            await self.session_service.invalidate_user_sessions(str(user_id))
            
            return {
                "success": True,
                "message": "Password changed successfully"
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error changing password: {e}")
            return {
                "success": False,
                "message": "Failed to change password"
            }

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email
            
        Returns:
            User entity or None
        """
        try:
            email = email.lower().strip()
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of active sessions
        """
        try:
            return await self.session_service.get_user_sessions(user_id)
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []

    async def request_password_reset(self, email: str) -> Dict[str, Any]:
        """
        Request password reset for user.
        
        Args:
            email: User email
            
        Returns:
            Dict containing reset request result
        """
        try:
            # Get user by email
            user = await self.get_user_by_email(email)
            
            # Always return success to prevent email enumeration
            # In a real implementation, send email if user exists
            if user:
                # Generate reset token
                reset_token = secrets.token_urlsafe(32)
                
                # Store reset token with expiration (implement in database)
                # For now, just log it
                logger.info(f"Password reset requested for {email}, token: {reset_token}")
                
                # TODO: Send email with reset link
            
            return {
                "success": True,
                "message": "Password reset instructions sent"
            }
            
        except Exception as e:
            logger.error(f"Error requesting password reset: {e}")
            return {
                "success": True,  # Always return success
                "message": "Password reset instructions sent"
            }

    async def confirm_password_reset(
        self, 
        token: str, 
        new_password: str
    ) -> Dict[str, Any]:
        """
        Confirm password reset with token.
        
        Args:
            token: Reset token
            new_password: New password
            
        Returns:
            Dict containing reset confirmation result
        """
        try:
            # TODO: Implement token validation and password reset
            # For now, return error as this is not fully implemented
            return {
                "success": False,
                "message": "Password reset not fully implemented yet"
            }
            
        except Exception as e:
            logger.error(f"Error confirming password reset: {e}")
            return {
                "success": False,
                "message": "Password reset failed"
            }

    async def update_user_profile(
        self,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user profile information.
        
        Args:
            user_id: User ID
            update_data: Data to update
            
        Returns:
            Dict containing update result
        """
        try:
            # Get user
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {
                    "success": False,
                    "message": "User not found"
                }
            
            # Update user fields
            for field, value in update_data.items():
                if hasattr(user, field):
                    setattr(user, field, value)
            
            # Update timestamp
            user.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(user)
            
            return {
                "success": True,
                "user": user,
                "message": "Profile updated successfully"
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating user profile: {e}")
            return {
                "success": False,
                "message": "Failed to update profile"
            }

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User entity or None
        """
        try:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    async def deactivate_user(self, user_id: str) -> Dict[str, Any]:
        """
        Deactivate user account.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict containing deactivation result
        """
        try:
            # Get user
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {
                    "success": False,
                    "message": "User not found"
                }
            
            # Deactivate user
            user.is_active = False
            user.updated_at = datetime.utcnow()
            
            await self.db.commit()
            
            # Invalidate all user sessions
            await self.session_service.invalidate_user_sessions(str(user_id))
            
            return {
                "success": True,
                "message": "User deactivated successfully"
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deactivating user: {e}")
            return {
                "success": False,
                "message": "Failed to deactivate user"
            }