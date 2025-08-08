"""
V1 Authentication Schemas - Authentication and authorization schemas for API version 1.

These schemas define the structure of authentication-related requests and responses
for V1 endpoints including login, registration, and token management.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from pydantic import Field, EmailStr, validator

from app.models.user import UserRole
from app.api.schemas.validators import (
    validate_email,
    validate_phone,
    email_field,
    phone_field,
    non_empty_string_field,
    password_field
)
from . import (
    BaseSchema,
    TimestampMixin,
    IDMixin,
    create_v1_response
)


# Authentication request schemas
class LoginRequestV1(BaseSchema):
    """Schema for user login request in V1."""
    email: str = email_field("User email address")
    password: str = password_field("User password")


class RegisterRequestV1(BaseSchema):
    """Schema for user registration request in V1."""
    email: str = email_field("User email address")
    password: str = password_field("User password")
    confirm_password: str = password_field("Password confirmation")
    first_name: str = non_empty_string_field("User first name")
    last_name: str = non_empty_string_field("User last name")
    phone_number: Optional[str] = phone_field("User phone number", default=None)
    role: Optional[UserRole] = Field(UserRole.PET_OWNER, description="User role")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        """Validate that passwords match."""
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class PasswordResetRequestV1(BaseSchema):
    """Schema for password reset request in V1."""
    email: str = email_field("User email address")


class PasswordResetConfirmV1(BaseSchema):
    """Schema for password reset confirmation in V1."""
    token: str = Field(description="Password reset token", min_length=1)
    new_password: str = password_field("New password")
    confirm_password: str = password_field("Password confirmation")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        """Validate that passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class ChangePasswordV1(BaseSchema):
    """Schema for password change request in V1."""
    current_password: str = password_field("Current password")
    new_password: str = password_field("New password")
    confirm_password: str = password_field("Password confirmation")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        """Validate that passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


# Authentication response schemas
class TokenResponseV1(BaseSchema):
    """Schema for token response in V1."""
    access_token: str = Field(description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(description="Token expiration time in seconds")
    refresh_token: Optional[str] = Field(None, description="Refresh token")


class UserProfileV1(BaseSchema):
    """Schema for user profile in authentication responses."""
    id: uuid.UUID = Field(description="User unique identifier")
    email: str = Field(description="User email address")
    first_name: str = Field(description="User first name")
    last_name: str = Field(description="User last name")
    phone_number: Optional[str] = Field(None, description="User phone number")
    role: UserRole = Field(description="User role")
    is_active: bool = Field(description="User active status")
    is_verified: bool = Field(description="User verification status")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(description="Account creation timestamp")
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"


class LoginResponseV1(BaseSchema):
    """Schema for login response in V1."""
    user: UserProfileV1 = Field(description="User profile information")
    token: TokenResponseV1 = Field(description="Authentication token")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    session_id: Optional[str] = Field(None, description="Session identifier")


class RegisterResponseV1(BaseSchema):
    """Schema for registration response in V1."""
    user: UserProfileV1 = Field(description="Created user profile")
    message: str = Field(description="Registration success message")
    verification_required: bool = Field(description="Whether email verification is required")


class RefreshTokenRequestV1(BaseSchema):
    """Schema for token refresh request in V1."""
    refresh_token: str = Field(description="Refresh token", min_length=1)


class LogoutRequestV1(BaseSchema):
    """Schema for logout request in V1."""
    session_id: Optional[str] = Field(None, description="Session ID to logout")
    logout_all_sessions: bool = Field(False, description="Logout from all sessions")


# Session management schemas
class SessionInfoV1(BaseSchema):
    """Schema for session information in V1."""
    session_id: str = Field(description="Session identifier")
    user_id: uuid.UUID = Field(description="User identifier")
    created_at: datetime = Field(description="Session creation time")
    last_activity: datetime = Field(description="Last activity time")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    is_active: bool = Field(description="Session active status")


class ActiveSessionsResponseV1(BaseSchema):
    """Schema for active sessions response in V1."""
    sessions: List[SessionInfoV1] = Field(description="List of active sessions")
    total: int = Field(description="Total number of active sessions")


# Permission and role management schemas
class PermissionCheckV1(BaseSchema):
    """Schema for permission check request in V1."""
    permission: str = Field(description="Permission to check", min_length=1)


class PermissionResponseV1(BaseSchema):
    """Schema for permission check response in V1."""
    permission: str = Field(description="Checked permission")
    has_permission: bool = Field(description="Whether user has the permission")
    reason: Optional[str] = Field(None, description="Reason if permission denied")


class RolePermissionsV1(BaseSchema):
    """Schema for role permissions in V1."""
    role: UserRole = Field(description="User role")
    permissions: List[str] = Field(description="List of permissions for the role")


# Success and error response schemas
class AuthSuccessResponseV1(BaseSchema):
    """Schema for successful authentication operations in V1."""
    success: bool = Field(True, description="Operation success flag")
    message: str = Field(description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")


class AuthErrorResponseV1(BaseSchema):
    """Schema for authentication operation errors in V1."""
    success: bool = Field(False, description="Operation success flag")
    message: str = Field(description="Error message")
    error_code: Optional[str] = Field(None, description="Specific error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")


# Response models using helper functions
LoginResponseModelV1 = create_v1_response(LoginResponseV1)
RegisterResponseModelV1 = create_v1_response(RegisterResponseV1)
TokenResponseModelV1 = create_v1_response(TokenResponseV1)
ActiveSessionsResponseModelV1 = create_v1_response(ActiveSessionsResponseV1)
PermissionResponseModelV1 = create_v1_response(PermissionResponseV1)
RolePermissionsModelV1 = create_v1_response(RolePermissionsV1)


# Export all schemas
__all__ = [
    "LoginRequestV1",
    "RegisterRequestV1",
    "PasswordResetRequestV1",
    "PasswordResetConfirmV1",
    "ChangePasswordV1",
    "TokenResponseV1",
    "UserProfileV1",
    "LoginResponseV1",
    "RegisterResponseV1",
    "RefreshTokenRequestV1",
    "LogoutRequestV1",
    "SessionInfoV1",
    "ActiveSessionsResponseV1",
    "PermissionCheckV1",
    "PermissionResponseV1",
    "RolePermissionsV1",
    "AuthSuccessResponseV1",
    "AuthErrorResponseV1",
    "LoginResponseModelV1",
    "RegisterResponseModelV1",
    "TokenResponseModelV1",
    "ActiveSessionsResponseModelV1",
    "PermissionResponseModelV1",
    "RolePermissionsModelV1",
]