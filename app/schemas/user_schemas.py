"""
User-related Pydantic schemas for request/response validation.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.models import UserRole


class UserBaseSchema(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=1000)
    profile_image_url: Optional[str] = Field(None, max_length=500)


class UserCreateSchema(UserBaseSchema):
    """Schema for creating a new user."""
    clerk_id: Optional[str] = Field(None, description="Clerk user ID for authentication")
    role: Optional[UserRole] = Field(UserRole.PET_OWNER, description="User role")
    
    class Config:
        use_enum_values = True


class UserUpdateSchema(BaseModel):
    """Schema for updating user information."""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=1000)
    profile_image_url: Optional[str] = Field(None, max_length=500)


class UserResponseSchema(UserBaseSchema):
    """Schema for user response data."""
    id: str
    clerk_id: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, user):
        """Create schema from ORM model."""
        return cls(
            id=str(user.id),
            clerk_id=user.clerk_id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone_number=user.phone_number,
            bio=user.bio,
            profile_image_url=user.profile_image_url,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at
        )


class UserListResponseSchema(BaseModel):
    """Schema for user list response."""
    users: list[UserResponseSchema]
    total: int
    page: int
    size: int
    total_pages: int


class UserProfileSchema(BaseModel):
    """Schema for user profile information."""
    bio: Optional[str] = Field(None, max_length=1000)
    profile_image_url: Optional[str] = Field(None, max_length=500)
    preferences: Optional[dict] = Field(None, description="User preferences as JSON")


class PasswordChangeSchema(BaseModel):
    """Schema for password change request."""
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    def validate_passwords_match(self):
        """Validate that new password and confirmation match."""
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirmation do not match")
        return self


class UserPreferencesSchema(BaseModel):
    """Schema for user preferences."""
    notifications: Optional[dict] = Field(None, description="Notification preferences")
    privacy: Optional[dict] = Field(None, description="Privacy settings")
    language: Optional[str] = Field("en", description="Preferred language")
    timezone: Optional[str] = Field("UTC", description="User timezone")


class RoleAssignmentSchema(BaseModel):
    """Schema for role assignment."""
    role: UserRole
    
    class Config:
        use_enum_values = True


class UserSessionSchema(BaseModel):
    """Schema for user session information."""
    id: str
    user_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Optional[str] = None
    is_active: bool
    created_at: datetime
    expires_at: datetime
    last_accessed_at: datetime
    
    class Config:
        from_attributes = True


class UserStatsSchema(BaseModel):
    """Schema for user statistics."""
    total_pets: int = 0
    total_appointments: int = 0
    upcoming_appointments: int = 0
    total_messages: int = 0
    account_age_days: int = 0
    last_activity: Optional[datetime] = None