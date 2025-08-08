"""
Version-agnostic Authentication controller for HTTP request processing and business logic orchestration.
Handles authentication-related operations across all API versions with shared business logic.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import logging

from app.models.user import User, UserRole
from app.core.exceptions import (
    ValidationError, 
    ConflictError, 
    NotFoundError, 
    BusinessLogicError,
    AuthenticationError,
    AuthorizationError
)
from app.app_helpers.validation_helpers import validate_email, validate_uuid
from app.app_helpers.auth_helpers import (
    create_access_token, 
    get_user_permissions,
    ROLE_PERMISSIONS
)
from .services import AuthService

logger = logging.getLogger(__name__)


class AuthController:
    """Version-agnostic controller for authentication-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = AuthService(db)
        self.current_user: Optional[Dict[str, Any]] = None

    async def register_user(
        self,
        registration_data: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle user registration for all API versions.
        
        Args:
            registration_data: Registration data (any version schema)
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Dict containing registration result
        """
        try:
            # Extract and validate required fields
            email = registration_data.get("email")
            password = registration_data.get("password")
            confirm_password = registration_data.get("confirm_password")
            first_name = registration_data.get("first_name")
            last_name = registration_data.get("last_name")

            if not all([email, password, first_name, last_name]):
                raise ValidationError("Email, password, first_name, and last_name are required")

            # Validate email format
            email = validate_email(email)

            # Validate password confirmation
            if password != confirm_password:
                raise ValidationError("Passwords do not match")

            # Validate password strength
            if len(password) < 8:
                raise ValidationError("Password must be at least 8 characters long")

            # Check for existing user
            existing_user = await self.service.get_user_by_email(email)
            if existing_user:
                raise ConflictError(
                    message="User with this email already exists",
                    conflicting_resource="email",
                    details={"email": email}
                )

            # Extract optional fields
            phone_number = registration_data.get("phone_number")
            role = registration_data.get("role", UserRole.PET_OWNER)
            
            # Convert role string to enum if needed
            if isinstance(role, str):
                try:
                    role = UserRole(role)
                except ValueError:
                    role = UserRole.PET_OWNER

            # Create user through service
            user = await self.service.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                role=role,
                ip_address=ip_address,
                user_agent=user_agent
            )

            logger.info(f"User registered successfully: {user.id}")
            
            return {
                "user": user,
                "message": "User registered successfully",
                "verification_required": True  # Email verification required
            }

        except (ValidationError, ConflictError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in register_user: {e}")
            raise BusinessLogicError(f"Failed to register user: {str(e)}")

    async def login_user(
        self,
        login_data: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle user login for all API versions.
        
        Args:
            login_data: Login data (any version schema)
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Dict containing login result with token and user info
        """
        try:
            # Extract credentials
            email = login_data.get("email")
            password = login_data.get("password")

            if not all([email, password]):
                raise ValidationError("Email and password are required")

            # Validate email format
            email = validate_email(email)

            # Authenticate user
            auth_result = await self.service.authenticate_user(
                email=email,
                password=password,
                ip_address=ip_address,
                user_agent=user_agent
            )

            if not auth_result["success"]:
                raise AuthenticationError(auth_result["message"])

            user = auth_result["user"]
            session_data = auth_result["session"]

            # Get user permissions
            permissions = get_user_permissions(user.role.value)

            # Create response
            response = {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone_number": user.phone_number,
                    "role": user.role.value,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "last_login": user.last_login,
                    "created_at": user.created_at
                },
                "token": {
                    "access_token": session_data["access_token"],
                    "token_type": "bearer",
                    "expires_in": session_data["expires_in"],
                    "refresh_token": session_data.get("refresh_token")
                },
                "permissions": permissions,
                "session_id": session_data["session_id"]
            }

            logger.info(f"User logged in successfully: {user.id}")
            return response

        except (ValidationError, AuthenticationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in login_user: {e}")
            raise BusinessLogicError(f"Failed to login user: {str(e)}")

    async def logout_user(
        self,
        logout_data: Dict[str, Any],
        current_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle user logout for all API versions.
        
        Args:
            logout_data: Logout data (any version schema)
            current_user_id: Current user ID
            
        Returns:
            Dict containing logout result
        """
        try:
            session_id = logout_data.get("session_id")
            logout_all_sessions = logout_data.get("logout_all_sessions", False)

            if logout_all_sessions and current_user_id:
                # Logout from all sessions
                invalidated_count = await self.service.logout_all_sessions(
                    user_id=current_user_id,
                    exclude_session=session_id
                )
                message = f"Logged out from {invalidated_count} sessions"
            elif session_id:
                # Logout from specific session
                success = await self.service.logout_session(session_id)
                message = "Logged out successfully" if success else "Session not found"
            else:
                raise ValidationError("Session ID is required for logout")

            return {
                "success": True,
                "message": message
            }

        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in logout_user: {e}")
            raise BusinessLogicError(f"Failed to logout user: {str(e)}")

    async def refresh_token(
        self,
        refresh_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle token refresh for all API versions.
        
        Args:
            refresh_data: Refresh token data
            
        Returns:
            Dict containing new token information
        """
        try:
            refresh_token = refresh_data.get("refresh_token")
            
            if not refresh_token:
                raise ValidationError("Refresh token is required")

            # Refresh token through service
            token_result = await self.service.refresh_access_token(refresh_token)

            if not token_result["success"]:
                raise AuthenticationError(token_result["message"])

            return {
                "access_token": token_result["access_token"],
                "token_type": "bearer",
                "expires_in": token_result["expires_in"],
                "refresh_token": token_result.get("refresh_token")
            }

        except (ValidationError, AuthenticationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in refresh_token: {e}")
            raise BusinessLogicError(f"Failed to refresh token: {str(e)}")

    async def change_password(
        self,
        password_data: Dict[str, Any],
        current_user_id: str
    ) -> Dict[str, Any]:
        """
        Handle password change for all API versions.
        
        Args:
            password_data: Password change data
            current_user_id: Current user ID
            
        Returns:
            Dict containing password change result
        """
        try:
            current_password = password_data.get("current_password")
            new_password = password_data.get("new_password")
            confirm_password = password_data.get("confirm_password")

            if not all([current_password, new_password, confirm_password]):
                raise ValidationError("Current password, new password, and confirmation are required")

            # Validate password confirmation
            if new_password != confirm_password:
                raise ValidationError("New passwords do not match")

            # Validate password strength
            if len(new_password) < 8:
                raise ValidationError("New password must be at least 8 characters long")

            # Change password through service
            result = await self.service.change_password(
                user_id=current_user_id,
                current_password=current_password,
                new_password=new_password
            )

            if not result["success"]:
                raise AuthenticationError(result["message"])

            return {
                "success": True,
                "message": "Password changed successfully"
            }

        except (ValidationError, AuthenticationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in change_password: {e}")
            raise BusinessLogicError(f"Failed to change password: {str(e)}")

    async def get_user_sessions(self, user_id: str) -> Dict[str, Any]:
        """
        Get active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict containing user sessions
        """
        try:
            sessions = await self.service.get_user_sessions(user_id)
            
            return {
                "sessions": sessions,
                "total": len(sessions)
            }

        except Exception as e:
            logger.error(f"Error in get_user_sessions: {e}")
            raise BusinessLogicError(f"Failed to get user sessions: {str(e)}")

    async def check_permission(
        self,
        permission: str,
        user_role: str
    ) -> Dict[str, Any]:
        """
        Check if user has a specific permission.
        
        Args:
            permission: Permission to check
            user_role: User role
            
        Returns:
            Dict containing permission check result
        """
        try:
            user_permissions = get_user_permissions(user_role)
            has_permission = "*" in user_permissions or permission in user_permissions
            
            reason = None
            if not has_permission:
                reason = f"Role '{user_role}' does not have permission '{permission}'"

            return {
                "permission": permission,
                "has_permission": has_permission,
                "reason": reason
            }

        except Exception as e:
            logger.error(f"Error in check_permission: {e}")
            raise BusinessLogicError(f"Failed to check permission: {str(e)}")

    async def get_role_permissions(self, role: str) -> Dict[str, Any]:
        """
        Get permissions for a specific role.
        
        Args:
            role: User role
            
        Returns:
            Dict containing role permissions
        """
        try:
            # Validate role
            try:
                role_enum = UserRole(role)
            except ValueError:
                raise ValidationError(f"Invalid role: {role}")

            permissions = get_user_permissions(role)
            
            return {
                "role": role,
                "permissions": permissions
            }

        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in get_role_permissions: {e}")
            raise BusinessLogicError(f"Failed to get role permissions: {str(e)}")

    async def request_password_reset(
        self,
        reset_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle password reset request.
        
        Args:
            reset_data: Password reset request data
            
        Returns:
            Dict containing reset request result
        """
        try:
            email = reset_data.get("email")
            
            if not email:
                raise ValidationError("Email is required")

            # Validate email format
            email = validate_email(email)

            # Request password reset through service
            result = await self.service.request_password_reset(email)

            return {
                "success": True,
                "message": "Password reset instructions sent to your email"
            }

        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in request_password_reset: {e}")
            raise BusinessLogicError(f"Failed to request password reset: {str(e)}")

    async def confirm_password_reset(
        self,
        reset_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle password reset confirmation.
        
        Args:
            reset_data: Password reset confirmation data
            
        Returns:
            Dict containing reset confirmation result
        """
        try:
            token = reset_data.get("token")
            new_password = reset_data.get("new_password")
            confirm_password = reset_data.get("confirm_password")

            if not all([token, new_password, confirm_password]):
                raise ValidationError("Token, new password, and confirmation are required")

            # Validate password confirmation
            if new_password != confirm_password:
                raise ValidationError("Passwords do not match")

            # Validate password strength
            if len(new_password) < 8:
                raise ValidationError("Password must be at least 8 characters long")

            # Confirm password reset through service
            result = await self.service.confirm_password_reset(token, new_password)

            if not result["success"]:
                raise AuthenticationError(result["message"])

            return {
                "success": True,
                "message": "Password reset successfully"
            }

        except (ValidationError, AuthenticationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in confirm_password_reset: {e}")
            raise BusinessLogicError(f"Failed to confirm password reset: {str(e)}")

    async def update_user_profile(
        self,
        profile_data: Dict[str, Any],
        current_user_id: str,
        target_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update user profile information.
        
        Args:
            profile_data: Profile data to update
            current_user_id: Current user ID
            target_user_id: Target user ID (for admin updates)
            
        Returns:
            Dict containing updated user profile
        """
        try:
            user_id = target_user_id or current_user_id
            
            # Validate user ID
            user_id = validate_uuid(user_id, "user_id")
            
            # Extract updatable fields
            allowed_fields = [
                "first_name", "last_name", "phone_number", 
                "timezone", "language", "preferences", "notification_settings"
            ]
            
            update_data = {}
            for field in allowed_fields:
                if field in profile_data:
                    value = profile_data[field]
                    
                    # Validate specific fields
                    if field in ["first_name", "last_name"] and value:
                        value = value.strip()
                        if not value:
                            raise ValidationError(f"{field} cannot be empty")
                    
                    update_data[field] = value
            
            # Only admins can update role
            if "role" in profile_data and target_user_id:
                # This would require admin permission check
                update_data["role"] = profile_data["role"]
            
            if not update_data:
                raise ValidationError("No valid fields provided for update")
            
            # Update user through service
            result = await self.service.update_user_profile(user_id, update_data)
            
            if not result["success"]:
                raise BusinessLogicError(result["message"])
            
            return {
                "success": True,
                "user": result["user"],
                "message": "Profile updated successfully"
            }
            
        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in update_user_profile: {e}")
            raise BusinessLogicError(f"Failed to update user profile: {str(e)}")

    async def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict containing user information
        """
        try:
            # Validate user ID
            user_id = validate_uuid(user_id, "user_id")
            
            # Get user through service
            user = await self.service.get_user_by_id(user_id)
            
            if not user:
                raise BusinessLogicError("User not found")
            
            return {
                "success": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone_number": user.phone_number,
                    "role": user.role,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "last_login": user.last_login,
                    "created_at": user.created_at
                }
            }
            
        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in get_user_by_id: {e}")
            raise BusinessLogicError(f"Failed to get user: {str(e)}")

    async def deactivate_user(
        self,
        user_id: str,
        current_user_id: str
    ) -> Dict[str, Any]:
        """
        Deactivate user account.
        
        Args:
            user_id: User ID to deactivate
            current_user_id: Current user ID
            
        Returns:
            Dict containing deactivation result
        """
        try:
            # Validate user ID
            user_id = validate_uuid(user_id, "user_id")
            
            # Prevent self-deactivation
            if user_id == current_user_id:
                raise ValidationError("Cannot deactivate your own account")
            
            # Deactivate user through service
            result = await self.service.deactivate_user(user_id)
            
            if not result["success"]:
                raise BusinessLogicError(result["message"])
            
            return {
                "success": True,
                "message": "User account deactivated successfully"
            }
            
        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"Error in deactivate_user: {e}")
            raise BusinessLogicError(f"Failed to deactivate user: {str(e)}")