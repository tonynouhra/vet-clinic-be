"""
Database models package.
"""
# Import all models here to ensure they are registered with SQLAlchemy
from .user import User, UserSession, UserRole, user_roles
from .pet import Pet, HealthRecord, Reminder, PetGender, PetSize, HealthRecordType
from .clinic import (
    Clinic, ClinicOperatingHours, Veterinarian, VeterinarianAvailability,
    ClinicReview, VeterinarianReview, ClinicType, VeterinarianSpecialty,
    DayOfWeek, veterinarian_specialties
)
from .appointment import (
    Appointment, AppointmentSlot, AppointmentStatus, AppointmentType,
    AppointmentPriority
)
from .communication import (
    Conversation, Message, MessageReaction, ChatBot, NotificationPreference,
    ConversationType, MessageType, MessageStatus, conversation_participants
)

# Export all models for easy importing
__all__ = [
    # User models
    "User",
    "UserSession", 
    "UserRole",
    "user_roles",
    
    # Pet models
    "Pet",
    "HealthRecord",
    "Reminder",
    "PetGender",
    "PetSize", 
    "HealthRecordType",
    
    # Clinic models
    "Clinic",
    "ClinicOperatingHours",
    "Veterinarian",
    "VeterinarianAvailability",
    "ClinicReview",
    "VeterinarianReview",
    "ClinicType",
    "VeterinarianSpecialty",
    "DayOfWeek",
    "veterinarian_specialties",
    
    # Appointment models
    "Appointment",
    "AppointmentSlot",
    "AppointmentStatus",
    "AppointmentType",
    "AppointmentPriority",
    
    # Communication models
    "Conversation",
    "Message",
    "MessageReaction",
    "ChatBot",
    "NotificationPreference",
    "ConversationType",
    "MessageType",
    "MessageStatus",
    "conversation_participants",
]