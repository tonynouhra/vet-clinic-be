"""
Communication models for chat and messaging functionality.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Integer, Table
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ConversationType(str, Enum):
    """Conversation type enumeration."""
    DIRECT_MESSAGE = "direct_message"
    GROUP_CHAT = "group_chat"
    SUPPORT_CHAT = "support_chat"
    AI_CHAT = "ai_chat"


class MessageType(str, Enum):
    """Message type enumeration."""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"
    SYSTEM = "system"
    AI_RESPONSE = "ai_response"


class MessageStatus(str, Enum):
    """Message status enumeration."""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


# Association table for conversation participants
conversation_participants = Table(
    'conversation_participants',
    Base.metadata,
    Column('conversation_id', UUID(as_uuid=True), ForeignKey('conversations.id'), primary_key=True),
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('joined_at', DateTime(timezone=True), server_default=func.now()),
    Column('left_at', DateTime(timezone=True), nullable=True),
    Column('is_admin', Boolean, default=False),
    Column('is_muted', Boolean, default=False),
    Column('last_read_at', DateTime(timezone=True), nullable=True)
)


class Conversation(Base):
    """Conversation model for chat functionality."""
    
    __tablename__ = "conversations"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Conversation details
    conversation_type = Column(ENUM(ConversationType), nullable=False, index=True)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    
    # Group chat specific fields
    is_group = Column(Boolean, default=False, nullable=False)
    max_participants = Column(Integer, nullable=True)
    
    # Conversation settings
    is_active = Column(Boolean, default=True, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    is_muted = Column(Boolean, default=False, nullable=False)
    
    # AI chat settings
    ai_enabled = Column(Boolean, default=False, nullable=False)
    ai_model = Column(String(100), nullable=True)
    ai_context = Column(JSON, nullable=True)
    
    # Metadata
    conversation_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    participants = relationship(
        "User",
        secondary=conversation_participants,
        back_populates="conversations",
        lazy="selectin"
    )
    messages = relationship("Message", back_populates="conversation", lazy="selectin", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, type={self.conversation_type}, title={self.title})>"
    
    @property
    def participant_count(self) -> int:
        """Get number of active participants."""
        return len(self.participants)
    
    @property
    def last_message(self) -> Optional["Message"]:
        """Get the last message in the conversation."""
        if self.messages:
            return max(self.messages, key=lambda m: m.created_at)
        return None
    
    def add_participant(self, user_id: uuid.UUID, is_admin: bool = False) -> bool:
        """Add a participant to the conversation."""
        # This would be implemented with proper SQLAlchemy session handling
        # For now, just return True as placeholder
        return True
    
    def remove_participant(self, user_id: uuid.UUID) -> bool:
        """Remove a participant from the conversation."""
        # This would be implemented with proper SQLAlchemy session handling
        # For now, just return True as placeholder
        return True


class Message(Base):
    """Message model for chat messages."""
    
    __tablename__ = "messages"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Message content
    message_type = Column(ENUM(MessageType), default=MessageType.TEXT, nullable=False, index=True)
    content = Column(Text, nullable=True)
    
    # File attachments
    attachments = Column(JSON, nullable=True)  # Array of file URLs and metadata
    
    # Message metadata
    message_metadata = Column(JSON, nullable=True)
    
    # Reply functionality
    reply_to_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True, index=True)
    
    # Message status
    status = Column(ENUM(MessageStatus), default=MessageStatus.SENT, nullable=False, index=True)
    
    # AI-specific fields
    is_ai_generated = Column(Boolean, default=False, nullable=False)
    ai_confidence_score = Column(Integer, nullable=True)  # 0-100
    ai_model_used = Column(String(100), nullable=True)
    
    # Moderation
    is_flagged = Column(Boolean, default=False, nullable=False)
    flagged_reason = Column(String(200), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages", lazy="selectin")
    sender = relationship("User", back_populates="messages_sent", lazy="selectin")
    reply_to = relationship("Message", remote_side=[id], lazy="selectin")
    reactions = relationship("MessageReaction", back_populates="message", lazy="selectin", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, sender_id={self.sender_id}, type={self.message_type})>"
    
    @property
    def is_read(self) -> bool:
        """Check if message has been read."""
        return self.status == MessageStatus.READ
    
    @property
    def is_delivered(self) -> bool:
        """Check if message has been delivered."""
        return self.status in [MessageStatus.DELIVERED, MessageStatus.READ]
    
    def mark_as_delivered(self) -> None:
        """Mark message as delivered."""
        if self.status == MessageStatus.SENT:
            self.status = MessageStatus.DELIVERED
            self.delivered_at = datetime.utcnow()
    
    def mark_as_read(self) -> None:
        """Mark message as read."""
        if self.status in [MessageStatus.SENT, MessageStatus.DELIVERED]:
            self.status = MessageStatus.READ
            self.read_at = datetime.utcnow()
    
    def soft_delete(self) -> None:
        """Soft delete the message."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()


class MessageReaction(Base):
    """Message reaction model for emoji reactions."""
    
    __tablename__ = "message_reactions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Reaction details
    emoji = Column(String(10), nullable=False)  # Unicode emoji
    emoji_name = Column(String(50), nullable=True)  # Human-readable name
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    message = relationship("Message", back_populates="reactions", lazy="selectin")
    user = relationship("User", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<MessageReaction(id={self.id}, message_id={self.message_id}, user_id={self.user_id}, emoji={self.emoji})>"


class ChatBot(Base):
    """AI Chatbot configuration model."""
    
    __tablename__ = "chatbots"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Bot information
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # AI configuration
    model_name = Column(String(100), nullable=False)
    system_prompt = Column(Text, nullable=True)
    max_tokens = Column(Integer, default=1000, nullable=False)
    temperature = Column(Integer, default=70, nullable=False)  # 0-100
    
    # Bot capabilities
    can_handle_emergencies = Column(Boolean, default=False, nullable=False)
    specialties = Column(JSON, nullable=True)  # Array of specialties
    knowledge_base = Column(JSON, nullable=True)  # Knowledge base references
    
    # Bot settings
    is_active = Column(Boolean, default=True, nullable=False)
    is_available_24_7 = Column(Boolean, default=True, nullable=False)
    response_delay_seconds = Column(Integer, default=2, nullable=False)
    
    # Usage statistics
    total_conversations = Column(Integer, default=0, nullable=False)
    total_messages = Column(Integer, default=0, nullable=False)
    average_response_time = Column(Integer, nullable=True)  # in milliseconds
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_active_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<ChatBot(id={self.id}, name={self.name}, model={self.model_name}, active={self.is_active})>"
    
    def increment_usage(self) -> None:
        """Increment usage statistics."""
        self.total_messages += 1
        self.last_active_at = datetime.utcnow()


class NotificationPreference(Base):
    """User notification preferences for chat and messaging."""
    
    __tablename__ = "notification_preferences"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Chat notifications
    chat_notifications_enabled = Column(Boolean, default=True, nullable=False)
    chat_sound_enabled = Column(Boolean, default=True, nullable=False)
    chat_desktop_notifications = Column(Boolean, default=True, nullable=False)
    chat_mobile_push = Column(Boolean, default=True, nullable=False)
    
    # Message notifications
    message_notifications_enabled = Column(Boolean, default=True, nullable=False)
    message_email_notifications = Column(Boolean, default=False, nullable=False)
    message_sms_notifications = Column(Boolean, default=False, nullable=False)
    
    # AI chat notifications
    ai_chat_notifications = Column(Boolean, default=True, nullable=False)
    ai_response_notifications = Column(Boolean, default=False, nullable=False)
    
    # Quiet hours
    quiet_hours_enabled = Column(Boolean, default=False, nullable=False)
    quiet_hours_start = Column(String(5), nullable=True)  # HH:MM format
    quiet_hours_end = Column(String(5), nullable=True)    # HH:MM format
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<NotificationPreference(id={self.id}, user_id={self.user_id}, chat_enabled={self.chat_notifications_enabled})>"