"""
Database models for the Veterinary Clinic Backend.
Contains SQLAlchemy models for all entities in the system.
"""

from .user import User, UserRole
from .pet import Pet, PetGender, HealthRecord, HealthRecordType
from .appointment import Appointment, AppointmentStatus, AppointmentType
from .clinic import Clinic, Veterinarian, VeterinarianSpecialty
from .communication import Conversation, Message, MessageType

__all__ = [
    # User models
    "User",
    "UserRole",
    
    # Pet models
    "Pet",
    "PetGender",
    "HealthRecord",
    "HealthRecordType",
    
    # Appointment models
    "Appointment",
    "AppointmentStatus",
    "AppointmentType",
    
    # Clinic models
    "Clinic",
    "Veterinarian",
    "VeterinarianSpecialty",
    
    # Communication models
    "Conversation",
    "Message",
    "MessageType",
]