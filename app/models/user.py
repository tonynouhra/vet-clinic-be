"""
User model and related enums for the Veterinary Clinic Backend.
Handles user authentication, roles, and profile information.
"""

from sqlalchemy import Column, String, Boolean, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
import uuid

from app.core.database import Base


class UserRole(str, Enum):
    """User roles in the veterinary clinic system."""
    ADMIN = "admin"
    VETERINARIAN = "veterinarian"
    RECEPTIONIST = "receptionist"
    PET_OWNER = "pet_owner"
    CLINIC_MANAGER = "clinic_manager"


class User(Base):
    """
    User model for authentication and profile management.
    Integrates with Clerk for authentication and supports role-based access control.
    """
    __tablename__ = "users"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Authentication fields
    clerk_id = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)

    # Profile fields
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)

    # Role and permissions
    role = Column(SQLEnum(UserRole), default=UserRole.PET_OWNER, nullable=False, index=True)

    # Additional profile data (V2+ fields)
    department = Column(String, nullable=True)  # For staff members
    preferences = Column(JSON, nullable=True, default=dict)  # User preferences
    notification_settings = Column(JSON, nullable=True, default=dict)  # Notification preferences
    timezone = Column(String, nullable=True, default="UTC")  # User timezone
    language = Column(String, nullable=True, default="en")  # Preferred language
    avatar_url = Column(String, nullable=True)  # Profile picture URL

    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    pets = relationship("Pet", back_populates="owner", lazy="dynamic")
    appointments = relationship("Appointment", back_populates="pet_owner", lazy="dynamic")
    veterinarian_profile = relationship("Veterinarian", back_populates="user", lazy="selectin", uselist=False)
    conversations = relationship(
        "Conversation",
        secondary="conversation_participants",
        back_populates="participants",
        lazy="selectin"
    )
    messages_sent = relationship("Message", back_populates="sender", lazy="dynamic")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_staff(self) -> bool:
        """Check if user is staff member."""
        return self.role in [UserRole.ADMIN, UserRole.VETERINARIAN, UserRole.RECEPTIONIST, UserRole.CLINIC_MANAGER]
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN
    
    @property
    def is_veterinarian(self) -> bool:
        """Check if user is veterinarian."""
        return self.role == UserRole.VETERINARIAN
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if user has specific permission.
        
        Args:
            permission: Permission to check
            
        Returns:
            bool: True if user has permission
        """
        # Basic role-based permissions
        role_permissions = {
            UserRole.ADMIN: ["*"],  # Admin has all permissions
            UserRole.VETERINARIAN: [
                "pets:read", "pets:write", "appointments:read", "appointments:write",
                "health_records:read", "health_records:write", "users:read"
            ],
            UserRole.RECEPTIONIST: [
                "appointments:read", "appointments:write", "users:read", "pets:read"
            ],
            UserRole.CLINIC_MANAGER: [
                "clinic:read", "clinic:write", "staff:read", "appointments:read",
                "reports:read"
            ],
            UserRole.PET_OWNER: [
                "pets:read", "pets:write", "appointments:read", "appointments:write",
                "profile:read", "profile:write"
            ]
        }
        
        user_permissions = role_permissions.get(self.role, [])
        
        # Admin has all permissions
        if "*" in user_permissions:
            return True
        
        return permission in user_permissions
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert user to dictionary representation.
        
        Args:
            include_sensitive: Whether to include sensitive fields
            
        Returns:
            dict: User data as dictionary
        """
        data = {
            "id": str(self.id),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "phone_number": self.phone_number,
            "role": self.role.value,
            "department": self.department,
            "timezone": self.timezone,
            "language": self.language,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "is_staff": self.is_staff,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        
        if include_sensitive:
            data.update({
                "clerk_id": self.clerk_id,
                "preferences": self.preferences,
                "notification_settings": self.notification_settings,
            })
        
        return data