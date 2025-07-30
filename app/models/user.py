"""
User models with Clerk integration and role-based access control.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserRole(str, Enum):
    """User role enumeration."""
    PET_OWNER = "pet_owner"
    VETERINARIAN = "veterinarian"
    CLINIC_ADMIN = "clinic_admin"
    SYSTEM_ADMIN = "system_admin"


# Association table for many-to-many relationship between users and roles
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('role', ENUM(UserRole), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), server_default=func.now()),
    Column('assigned_by', UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
)


class User(Base):
    """User model with Clerk integration."""
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Clerk integration
    clerk_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Basic user information
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=True)
    
    # Profile information
    profile_image_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Note: roles relationship is handled through the user_roles association table
    # The roles are accessed via the user_roles table directly
    
    # Relationship to pets (for pet owners)
    pets = relationship("Pet", back_populates="owner", lazy="selectin")
    
    # Relationship to appointments (as pet owner)
    appointments = relationship("Appointment", back_populates="pet_owner", lazy="selectin")
    
    # Relationship to veterinarian profile (if user is a veterinarian)
    veterinarian_profile = relationship("Veterinarian", back_populates="user", uselist=False, lazy="selectin")
    
    # Relationship to conversations
    conversations = relationship("Conversation", secondary="conversation_participants", back_populates="participants", lazy="selectin")
    
    # Relationship to messages sent
    messages_sent = relationship("Message", back_populates="sender", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, clerk_id={self.clerk_id})>"
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role."""
        # This would need to be implemented with a database query
        # For now, return False as placeholder
        return False
    
    def is_pet_owner(self) -> bool:
        """Check if user is a pet owner."""
        return self.has_role(UserRole.PET_OWNER)
    
    def is_veterinarian(self) -> bool:
        """Check if user is a veterinarian."""
        return self.has_role(UserRole.VETERINARIAN)
    
    def is_clinic_admin(self) -> bool:
        """Check if user is a clinic admin."""
        return self.has_role(UserRole.CLINIC_ADMIN)
    
    def is_system_admin(self) -> bool:
        """Check if user is a system admin."""
        return self.has_role(UserRole.SYSTEM_ADMIN)


class UserSession(Base):
    """User session model for tracking active sessions."""
    
    __tablename__ = "user_sessions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Session information
    session_token = Column(String(500), unique=True, nullable=False, index=True)
    refresh_token = Column(String(500), unique=True, nullable=True, index=True)
    
    # Session metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    device_info = Column(Text, nullable=True)
    
    # Session status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, is_active={self.is_active})>"
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at