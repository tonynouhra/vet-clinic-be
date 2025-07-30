"""
V1 User Schemas - Basic user management schemas for API version 1.

These schemas define the structure of user-related requests and responses
for V1 endpoints with basic user functionality.
"""

from typing import Optional, List
from datetime import datetime
import uuid
from pydantic import Field, EmailStr

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
    create_v1_response,
    create_v1_list_response
)


# Base User schemas
class UserBaseV1(BaseSchema):
    """Base user schema with common fields for V1."""
    email: str = email_field("User email address")
    first_name: str = non_empty_string_field("User first name")
    last_name: str = non_empty_string_field("User last name")
    phone_number: Optional[str] = phone_field("User phone number", default=None)


class UserCreateV1(UserBaseV1):
    """Schema for creating a user in V1."""
    role: Optional[UserRole] = Field(UserRole.PET_OWNER, description="User role")


class UserUpdateV1(BaseSchema):
    """Schema for updating a user in V1."""
    email: Optional[str] = email_field("New email address", default=None)
    first_name: Optional[str] = Field(None, description="New first name", min_length=1)
    last_name: Optional[str] = Field(None, description="New last name", min_length=1)
    phone_number: Optional[str] = phone_field("New phone number", default=None)


class UserResponseV1(UserBaseV1, IDMixin, TimestampMixin):
    """Schema for user response in V1."""
    id: uuid.UUID = Field(description="User unique identifier")
    is_active: bool = Field(description="User active status")
    is_verified: bool = Field(description="User verification status")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"


# List and pagination schemas
class UserListRequestV1(PaginationRequest):
    """Schema for user list request in V1."""
    search: Optional[str] = Field(None, description="Search term for name or email")
    role: Optional[UserRole] = Field(None, description="Filter by user role")
    is_active: Optional[bool] = Field(None, description="Filter by active status")


# Authentication related schemas
class UserLoginV1(BaseSchema):
    """Schema for user login in V1."""
    email: str = email_field("User email address")
    password: str = Field(description="User password", min_length=8)


class UserRegisterV1(UserCreateV1):
    """Schema for user registration in V1."""
    password: str = Field(description="User password", min_length=8)
    confirm_password: str = Field(description="Password confirmation", min_length=8)
    
    def validate_passwords_match(self):
        """Validate that passwords match."""
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


# Role management schemas
class RoleAssignmentV1(BaseSchema):
    """Schema for role assignment in V1."""
    role: UserRole = Field(description="Role to assign")


# Response models using helper functions
UserResponseModelV1 = create_v1_response(UserResponseV1)
UserListResponseModelV1 = create_v1_list_response(UserResponseV1)

# Success response for operations
class UserOperationSuccessV1(BaseSchema):
    """Schema for successful user operations in V1."""
    success: bool = Field(True, description="Operation success flag")
    message: str = Field(description="Success message")
    user_id: Optional[uuid.UUID] = Field(None, description="User ID if applicable")


# Error response specific to user operations
class UserErrorResponseV1(BaseSchema):
    """Schema for user operation errors in V1."""
    success: bool = Field(False, description="Operation success flag")
    message: str = Field(description="Error message")
    error_code: Optional[str] = Field(None, description="Specific error code")
    field_errors: Optional[List[str]] = Field(None, description="Field-specific errors")


# Export all schemas
__all__ = [
    "UserBaseV1",
    "UserCreateV1",
    "UserUpdateV1",
    "UserResponseV1",
    "UserListRequestV1",
    "UserLoginV1",
    "UserRegisterV1",
    "RoleAssignmentV1",
    "UserResponseModelV1",
    "UserListResponseModelV1",
    "UserOperationSuccessV1",
    "UserErrorResponseV1",
]