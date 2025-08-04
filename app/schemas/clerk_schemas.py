"""
Clerk-related Pydantic schemas for authentication and user data synchronization.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
from app.models.user import UserRole


class ClerkEmailAddress(BaseModel):
    """Schema for Clerk email address object."""
    id: str
    email_address: EmailStr
    verification: Optional[Dict[str, Any]] = None
    linked_to: Optional[List[Dict[str, Any]]] = None


class ClerkPhoneNumber(BaseModel):
    """Schema for Clerk phone number object."""
    id: str
    phone_number: str
    verification: Optional[Dict[str, Any]] = None
    linked_to: Optional[List[Dict[str, Any]]] = None


class ClerkUser(BaseModel):
    """
    Pydantic model for Clerk user data from API responses.
    Represents the complete user object returned by Clerk API.
    """
    id: str = Field(..., description="Clerk user ID")
    email_addresses: List[ClerkEmailAddress] = Field(default_factory=list)
    phone_numbers: List[ClerkPhoneNumber] = Field(default_factory=list)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    image_url: Optional[str] = None
    has_image: bool = False
    public_metadata: Dict[str, Any] = Field(default_factory=dict)
    private_metadata: Dict[str, Any] = Field(default_factory=dict)
    unsafe_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: int = Field(..., description="Unix timestamp of creation")
    updated_at: int = Field(..., description="Unix timestamp of last update")
    last_sign_in_at: Optional[int] = Field(None, description="Unix timestamp of last sign in")
    banned: bool = False
    locked: bool = False
    lockout_expires_in_seconds: Optional[int] = None
    verification_attempts_remaining: int = 3
    
    @property
    def primary_email(self) -> Optional[str]:
        """Get the primary email address."""
        if self.email_addresses:
            return self.email_addresses[0].email_address
        return None
    
    @property
    def primary_phone(self) -> Optional[str]:
        """Get the primary phone number."""
        if self.phone_numbers:
            return self.phone_numbers[0].phone_number
        return None
    
    @property
    def created_at_datetime(self) -> datetime:
        """Convert created_at timestamp to datetime."""
        return datetime.utcfromtimestamp(self.created_at / 1000)
    
    @property
    def updated_at_datetime(self) -> datetime:
        """Convert updated_at timestamp to datetime."""
        return datetime.utcfromtimestamp(self.updated_at / 1000)
    
    @property
    def last_sign_in_datetime(self) -> Optional[datetime]:
        """Convert last_sign_in_at timestamp to datetime."""
        if self.last_sign_in_at:
            return datetime.utcfromtimestamp(self.last_sign_in_at / 1000)
        return None


class ClerkUserRole(BaseModel):
    """Schema for role mapping from Clerk metadata to internal roles."""
    clerk_role: str = Field(..., description="Role from Clerk metadata")
    internal_role: UserRole = Field(..., description="Mapped internal role")
    
    class Config:
        use_enum_values = True


class ClerkWebhookEvent(BaseModel):
    """Schema for Clerk webhook events."""
    type: str = Field(..., description="Event type (e.g., user.created, user.updated)")
    object: str = Field(..., description="Object type (e.g., event)")
    data: Dict[str, Any] = Field(..., description="Event data containing user information")
    timestamp: int = Field(..., description="Unix timestamp of the event")
    
    @property
    def timestamp_datetime(self) -> datetime:
        """Convert timestamp to datetime."""
        return datetime.utcfromtimestamp(self.timestamp / 1000)


class ClerkUserSyncRequest(BaseModel):
    """Schema for user synchronization requests."""
    clerk_user: ClerkUser
    force_update: bool = Field(False, description="Force update even if user exists")
    sync_metadata: bool = Field(True, description="Sync metadata fields")


class ClerkUserSyncResponse(BaseModel):
    """Schema for user synchronization responses."""
    success: bool
    user_id: Optional[str] = None
    action: str = Field(..., description="Action taken: created, updated, or skipped")
    message: str
    errors: List[str] = Field(default_factory=list)


class ClerkTokenValidationRequest(BaseModel):
    """Schema for token validation requests."""
    token: str = Field(..., description="JWT token to validate")
    verify_signature: bool = Field(True, description="Whether to verify token signature")


class ClerkTokenValidationResponse(BaseModel):
    """Schema for token validation responses."""
    valid: bool
    user_id: Optional[str] = None
    clerk_user: Optional[ClerkUser] = None
    error: Optional[str] = None
    expires_at: Optional[datetime] = None


class ClerkRoleMapping(BaseModel):
    """Configuration for mapping Clerk roles to internal roles."""
    mappings: Dict[str, UserRole] = Field(
        default_factory=lambda: {
            "admin": UserRole.ADMIN,
            "veterinarian": UserRole.VETERINARIAN,
            "receptionist": UserRole.RECEPTIONIST,
            "clinic_manager": UserRole.CLINIC_MANAGER,
            "pet_owner": UserRole.PET_OWNER,
            "staff": UserRole.RECEPTIONIST,  # Default staff role
        }
    )
    default_role: UserRole = Field(UserRole.PET_OWNER, description="Default role for unmapped users")
    
    def get_internal_role(self, clerk_role: Optional[str]) -> UserRole:
        """
        Map Clerk role to internal role.
        
        Args:
            clerk_role: Role from Clerk metadata
            
        Returns:
            UserRole: Mapped internal role
        """
        if not clerk_role:
            return self.default_role
        
        return self.mappings.get(clerk_role.lower(), self.default_role)
    
    class Config:
        use_enum_values = True


class ClerkUserTransform(BaseModel):
    """Schema for transforming Clerk user data to internal user format."""
    
    @staticmethod
    def to_user_create_data(clerk_user: ClerkUser, role_mapping: ClerkRoleMapping) -> Dict[str, Any]:
        """
        Transform ClerkUser to user creation data.
        
        Args:
            clerk_user: Clerk user data
            role_mapping: Role mapping configuration
            
        Returns:
            Dict containing user creation data
        """
        # Extract role from public metadata
        clerk_role = clerk_user.public_metadata.get("role")
        internal_role = role_mapping.get_internal_role(clerk_role)
        
        return {
            "clerk_id": clerk_user.id,
            "email": clerk_user.primary_email,
            "first_name": clerk_user.first_name or "",
            "last_name": clerk_user.last_name or "",
            "phone_number": clerk_user.primary_phone,
            "role": internal_role,
            "avatar_url": clerk_user.image_url,
            "is_active": not clerk_user.banned and not clerk_user.locked,
            "is_verified": True,  # Assume Clerk users are verified
            "preferences": clerk_user.private_metadata.get("preferences", {}),
            "notification_settings": clerk_user.private_metadata.get("notifications", {}),
            "timezone": clerk_user.private_metadata.get("timezone", "UTC"),
            "language": clerk_user.private_metadata.get("language", "en"),
        }
    
    @staticmethod
    def to_user_update_data(clerk_user: ClerkUser, role_mapping: ClerkRoleMapping) -> Dict[str, Any]:
        """
        Transform ClerkUser to user update data.
        
        Args:
            clerk_user: Clerk user data
            role_mapping: Role mapping configuration
            
        Returns:
            Dict containing user update data
        """
        # Extract role from public metadata
        clerk_role = clerk_user.public_metadata.get("role")
        internal_role = role_mapping.get_internal_role(clerk_role)
        
        update_data = {}
        
        # Only include fields that have values
        if clerk_user.primary_email:
            update_data["email"] = clerk_user.primary_email
        
        if clerk_user.first_name:
            update_data["first_name"] = clerk_user.first_name
        
        if clerk_user.last_name:
            update_data["last_name"] = clerk_user.last_name
        
        if clerk_user.primary_phone:
            update_data["phone_number"] = clerk_user.primary_phone
        
        if clerk_user.image_url:
            update_data["avatar_url"] = clerk_user.image_url
        
        # Always update role and status
        update_data.update({
            "role": internal_role,
            "is_active": not clerk_user.banned and not clerk_user.locked,
            "preferences": clerk_user.private_metadata.get("preferences", {}),
            "notification_settings": clerk_user.private_metadata.get("notifications", {}),
            "timezone": clerk_user.private_metadata.get("timezone", "UTC"),
            "language": clerk_user.private_metadata.get("language", "en"),
        })
        
        return update_data


class ClerkUserValidation(BaseModel):
    """Validation utilities for Clerk user data."""
    
    @staticmethod
    def validate_user_data(clerk_user: ClerkUser) -> List[str]:
        """
        Validate Clerk user data for completeness and correctness.
        
        Args:
            clerk_user: Clerk user data to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check required fields
        if not clerk_user.id:
            errors.append("Clerk user ID is required")
        
        if not clerk_user.primary_email:
            errors.append("Primary email address is required")
        
        if not clerk_user.first_name:
            errors.append("First name is required")
        
        if not clerk_user.last_name:
            errors.append("Last name is required")
        
        # Validate email format (basic check since Clerk should handle this)
        if clerk_user.primary_email and "@" not in clerk_user.primary_email:
            errors.append("Invalid email format")
        
        # Validate phone number format if provided
        if clerk_user.primary_phone:
            phone = clerk_user.primary_phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            if not phone.replace("+", "").isdigit():
                errors.append("Invalid phone number format")
        
        # Validate timestamps
        if clerk_user.created_at <= 0:
            errors.append("Invalid created_at timestamp")
        
        if clerk_user.updated_at <= 0:
            errors.append("Invalid updated_at timestamp")
        
        if clerk_user.last_sign_in_at is not None and clerk_user.last_sign_in_at <= 0:
            errors.append("Invalid last_sign_in_at timestamp")
        
        return errors
    
    @staticmethod
    def validate_role_metadata(public_metadata: Dict[str, Any]) -> List[str]:
        """
        Validate role information in public metadata.
        
        Args:
            public_metadata: Clerk public metadata
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        role = public_metadata.get("role")
        if role:
            valid_roles = ["admin", "veterinarian", "receptionist", "clinic_manager", "pet_owner", "staff"]
            if role.lower() not in valid_roles:
                errors.append(f"Invalid role '{role}'. Must be one of: {', '.join(valid_roles)}")
        
        return errors