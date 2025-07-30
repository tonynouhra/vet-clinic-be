"""
V2 User Schemas - Enhanced user management schemas for API version 2.

These schemas define the structure of user-related requests and responses
for V2 endpoints with enhanced features like roles, departments, preferences,
and additional profile information.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from pydantic import Field, EmailStr, HttpUrl

from app.models.user import UserRole
from app.api.schemas.validators import (
    validate_email,
    validate_phone,
    email_field,
    phone_field,
    non_empty_string_field,
    positive_int_field
)
from . import (
    BaseSchema,
    TimestampMixin,
    IDMixin,
    PaginationRequest,
    create_v2_response,
    create_v2_list_response
)


# Enhanced User schemas for V2
class UserBaseV2(BaseSchema):
    """Base user schema with common fields for V2."""
    email: str = email_field("User email address")
    first_name: str = non_empty_string_field("User first name")
    last_name: str = non_empty_string_field("User last name")
    phone_number: Optional[str] = phone_field("User phone number", default=None)
    bio: Optional[str] = Field(None, description="User biography", max_length=500)
    profile_image_url: Optional[HttpUrl] = Field(None, description="Profile image URL")


class UserCreateV2(UserBaseV2):
    """Schema for creating a user in V2 with enhanced fields."""
    role: Optional[UserRole] = Field(UserRole.PET_OWNER, description="User role")
    department: Optional[str] = Field(None, description="User department", max_length=100)
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    clerk_id: Optional[str] = Field(None, description="Clerk user ID")


class UserUpdateV2(BaseSchema):
    """Schema for updating a user in V2 with enhanced fields."""
    email: Optional[str] = email_field("New email address", default=None)
    first_name: Optional[str] = Field(None, description="New first name", min_length=1)
    last_name: Optional[str] = Field(None, description="New last name", min_length=1)
    phone_number: Optional[str] = phone_field("New phone number", default=None)
    bio: Optional[str] = Field(None, description="New biography", max_length=500)
    profile_image_url: Optional[HttpUrl] = Field(None, description="New profile image URL")
    department: Optional[str] = Field(None, description="New department", max_length=100)
    preferences: Optional[Dict[str, Any]] = Field(None, description="New preferences")


class UserRoleInfoV2(BaseSchema):
    """Schema for user role information in V2."""
    role: UserRole = Field(description="User role")
    assigned_at: datetime = Field(description="Role assignment timestamp")
    assigned_by: Optional[uuid.UUID] = Field(None, description="ID of user who assigned the role")


class UserResponseV2(UserBaseV2, IDMixin, TimestampMixin):
    """Schema for user response in V2 with enhanced fields."""
    id: uuid.UUID = Field(description="User unique identifier")
    is_active: bool = Field(description="User active status")
    is_verified: bool = Field(description="User verification status")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    department: Optional[str] = Field(None, description="User department")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    
    # Enhanced V2 fields
    roles: Optional[List[UserRoleInfoV2]] = Field(None, description="User roles with assignment info")
    pets_count: Optional[int] = Field(None, description="Number of pets owned")
    appointments_count: Optional[int] = Field(None, description="Number of appointments")
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def primary_role(self) -> Optional[UserRole]:
        """Get user's primary role."""
        if self.roles:
            return self.roles[0].role
        return None


# Enhanced list and pagination schemas
class UserListRequestV2(PaginationRequest):
    """Schema for user list request in V2 with enhanced filtering."""
    search: Optional[str] = Field(None, description="Search term for name or email")
    role: Optional[UserRole] = Field(None, description="Filter by user role")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    department: Optional[str] = Field(None, description="Filter by department")
    include_roles: bool = Field(False, description="Include role information in response")
    include_relationships: bool = Field(False, description="Include pet/appointment counts")


# Authentication related schemas for V2
class UserLoginV2(BaseSchema):
    """Schema for user login in V2."""
    email: str = email_field("User email address")
    password: str = Field(description="User password", min_length=8)
    remember_me: bool = Field(False, description="Remember me option")


class UserRegisterV2(UserCreateV2):
    """Schema for user registration in V2 with enhanced fields."""
    password: str = Field(description="User password", min_length=8)
    confirm_password: str = Field(description="Password confirmation", min_length=8)
    terms_accepted: bool = Field(description="Terms and conditions accepted")
    newsletter_subscription: bool = Field(False, description="Newsletter subscription preference")
    
    def validate_passwords_match(self):
        """Validate that passwords match."""
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self
    
    def validate_terms_accepted(self):
        """Validate that terms are accepted."""
        if not self.terms_accepted:
            raise ValueError("Terms and conditions must be accepted")
        return self


# Enhanced role management schemas
class RoleAssignmentV2(BaseSchema):
    """Schema for role assignment in V2 with additional metadata."""
    role: UserRole = Field(description="Role to assign")
    department: Optional[str] = Field(None, description="Department for the role")
    notes: Optional[str] = Field(None, description="Assignment notes", max_length=200)


class MultipleRoleAssignmentV2(BaseSchema):
    """Schema for assigning multiple roles in V2."""
    roles: List[RoleAssignmentV2] = Field(description="List of roles to assign")


# Profile management schemas
class UserProfileUpdateV2(BaseSchema):
    """Schema for updating user profile in V2."""
    bio: Optional[str] = Field(None, description="User biography", max_length=500)
    profile_image_url: Optional[HttpUrl] = Field(None, description="Profile image URL")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")


class UserPreferencesV2(BaseSchema):
    """Schema for user preferences in V2."""
    theme: Optional[str] = Field("light", description="UI theme preference")
    language: Optional[str] = Field("en", description="Language preference")
    notifications: Optional[Dict[str, bool]] = Field(None, description="Notification preferences")
    privacy: Optional[Dict[str, bool]] = Field(None, description="Privacy settings")


# Enhanced statistics and analytics schemas
class UserStatsV2(BaseSchema):
    """Schema for user statistics in V2."""
    total_pets: int = Field(description="Total number of pets")
    total_appointments: int = Field(description="Total number of appointments")
    active_appointments: int = Field(description="Number of active appointments")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    registration_date: datetime = Field(description="User registration date")
    account_age_days: int = Field(description="Account age in days")


# Response models using helper functions
UserResponseModelV2 = create_v2_response(UserResponseV2)
UserListResponseModelV2 = create_v2_list_response(UserResponseV2)
UserStatsResponseModelV2 = create_v2_response(UserStatsV2)

# Enhanced success response for operations
class UserOperationSuccessV2(BaseSchema):
    """Schema for successful user operations in V2."""
    success: bool = Field(True, description="Operation success flag")
    message: str = Field(description="Success message")
    user_id: Optional[uuid.UUID] = Field(None, description="User ID if applicable")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Operation timestamp")
    affected_roles: Optional[List[UserRole]] = Field(None, description="Roles affected by the operation")


# Enhanced error response specific to user operations
class UserErrorResponseV2(BaseSchema):
    """Schema for user operation errors in V2."""
    success: bool = Field(False, description="Operation success flag")
    message: str = Field(description="Error message")
    error_code: Optional[str] = Field(None, description="Specific error code")
    field_errors: Optional[Dict[str, List[str]]] = Field(None, description="Field-specific errors")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


# Batch operations schemas
class BatchUserCreateV2(BaseSchema):
    """Schema for batch user creation in V2."""
    users: List[UserCreateV2] = Field(description="List of users to create")
    default_role: UserRole = Field(UserRole.PET_OWNER, description="Default role for all users")
    send_invitations: bool = Field(True, description="Send invitation emails")


class BatchUserUpdateV2(BaseSchema):
    """Schema for batch user updates in V2."""
    user_ids: List[uuid.UUID] = Field(description="List of user IDs to update")
    updates: UserUpdateV2 = Field(description="Updates to apply to all users")


class BatchOperationResultV2(BaseSchema):
    """Schema for batch operation results in V2."""
    success: bool = Field(description="Overall operation success")
    total_requested: int = Field(description="Total number of operations requested")
    successful: int = Field(description="Number of successful operations")
    failed: int = Field(description="Number of failed operations")
    errors: List[Dict[str, Any]] = Field(description="List of errors encountered")
    processed_ids: List[uuid.UUID] = Field(description="List of successfully processed user IDs")


# Export all schemas
__all__ = [
    "UserBaseV2",
    "UserCreateV2",
    "UserUpdateV2",
    "UserRoleInfoV2",
    "UserResponseV2",
    "UserListRequestV2",
    "UserLoginV2",
    "UserRegisterV2",
    "RoleAssignmentV2",
    "MultipleRoleAssignmentV2",
    "UserProfileUpdateV2",
    "UserPreferencesV2",
    "UserStatsV2",
    "UserResponseModelV2",
    "UserListResponseModelV2",
    "UserStatsResponseModelV2",
    "UserOperationSuccessV2",
    "UserErrorResponseV2",
    "BatchUserCreateV2",
    "BatchUserUpdateV2",
    "BatchOperationResultV2",
]