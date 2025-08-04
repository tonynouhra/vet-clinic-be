"""
Pet models with health record relationships.
"""
import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Date, Float, Integer, Boolean, Table
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


# Association table for pet-veterinarian many-to-many relationship
pet_veterinarians = Table(
    'pet_veterinarians',
    Base.metadata,
    Column('pet_id', UUID(as_uuid=True), ForeignKey('pets.id', ondelete='CASCADE'), primary_key=True),
    Column('veterinarian_id', UUID(as_uuid=True), ForeignKey('veterinarians.id', ondelete='CASCADE'), primary_key=True),
    Column('relationship_type', String(50), nullable=True),  # primary, specialist, emergency, consultant, etc.
    Column('is_primary', Boolean, default=False, nullable=False),  # Mark primary veterinarian
    Column('notes', Text, nullable=True),  # Additional notes about the relationship
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
)


class PetGender(str, Enum):
    """Pet gender enumeration."""
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class PetSize(str, Enum):
    """Pet size enumeration."""
    EXTRA_SMALL = "extra_small"  # < 5 lbs
    SMALL = "small"              # 5-25 lbs
    MEDIUM = "medium"            # 25-60 lbs
    LARGE = "large"              # 60-100 lbs
    EXTRA_LARGE = "extra_large"  # > 100 lbs


class HealthRecordType(str, Enum):
    """Health record type enumeration."""
    VACCINATION = "vaccination"
    MEDICATION = "medication"
    TREATMENT = "treatment"
    SURGERY = "surgery"
    CHECKUP = "checkup"
    EMERGENCY = "emergency"
    DENTAL = "dental"
    GROOMING = "grooming"
    OTHER = "other"


class Pet(Base):
    """Pet model with comprehensive profile information."""
    
    __tablename__ = "pets"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to owner
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Basic pet information
    name = Column(String(100), nullable=False)
    species = Column(String(50), nullable=False)  # Dog, Cat, Bird, etc.
    breed = Column(String(100), nullable=True)
    mixed_breed = Column(Boolean, default=False, nullable=False)
    
    # Physical characteristics
    gender = Column(ENUM(PetGender), nullable=False)
    size = Column(ENUM(PetSize), nullable=True)
    weight = Column(Float, nullable=True)  # in pounds
    color = Column(String(100), nullable=True)
    
    # Age information
    birth_date = Column(Date, nullable=True)
    age_years = Column(Integer, nullable=True)
    age_months = Column(Integer, nullable=True)
    is_age_estimated = Column(Boolean, default=False, nullable=False)
    
    # Identification
    microchip_id = Column(String(50), nullable=True, unique=True, index=True)
    registration_number = Column(String(100), nullable=True)
    
    # Medical information
    medical_notes = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    current_medications = Column(Text, nullable=True)
    special_needs = Column(Text, nullable=True)
    
    # Behavioral information
    temperament = Column(String(200), nullable=True)
    behavioral_notes = Column(Text, nullable=True)
    
    # Profile media
    profile_image_url = Column(String(500), nullable=True)
    additional_photos = Column(JSON, nullable=True)  # Array of photo URLs
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_deceased = Column(Boolean, default=False, nullable=False)
    deceased_date = Column(Date, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="pets", lazy="selectin")
    health_records = relationship("HealthRecord", back_populates="pet", lazy="selectin", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="pet", lazy="selectin")
    reminders = relationship("Reminder", back_populates="pet", lazy="selectin", cascade="all, delete-orphan")
    
    # Many-to-many relationship with veterinarians
    veterinarians = relationship("Veterinarian", secondary="pet_veterinarians", back_populates="pets", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<Pet(id={self.id}, name={self.name}, species={self.species}, owner_id={self.owner_id})>"
    
    @property
    def age_display(self) -> str:
        """Get formatted age display."""
        if self.age_years is not None and self.age_months is not None:
            if self.age_years > 0:
                return f"{self.age_years} years, {self.age_months} months"
            else:
                return f"{self.age_months} months"
        elif self.age_years is not None:
            return f"{self.age_years} years"
        elif self.age_months is not None:
            return f"{self.age_months} months"
        elif self.birth_date:
            # Calculate age from birth date
            today = date.today()
            age = today - self.birth_date
            years = age.days // 365
            months = (age.days % 365) // 30
            if years > 0:
                return f"{years} years, {months} months"
            else:
                return f"{months} months"
        return "Unknown"


class HealthRecord(Base):
    """Health record model for tracking pet medical history."""
    
    __tablename__ = "health_records"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to pet
    pet_id = Column(UUID(as_uuid=True), ForeignKey("pets.id"), nullable=False, index=True)
    
    # Foreign key to veterinarian (optional)
    veterinarian_id = Column(UUID(as_uuid=True), ForeignKey("veterinarians.id"), nullable=True, index=True)
    
    # Record information
    record_type = Column(ENUM(HealthRecordType), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Date information
    record_date = Column(Date, nullable=False, index=True)
    next_due_date = Column(Date, nullable=True, index=True)  # For recurring items like vaccinations
    
    # Medical details
    diagnosis = Column(Text, nullable=True)
    treatment = Column(Text, nullable=True)
    medication_name = Column(String(200), nullable=True)
    dosage = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    duration = Column(String(100), nullable=True)
    
    # Additional information
    cost = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True)  # Array of file URLs
    record_metadata = Column(JSON, nullable=True)  # Additional structured data
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    pet = relationship("Pet", back_populates="health_records", lazy="selectin")
    veterinarian = relationship("Veterinarian", back_populates="health_records", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<HealthRecord(id={self.id}, pet_id={self.pet_id}, type={self.record_type}, title={self.title})>"


class Reminder(Base):
    """Reminder model for automated pet care notifications."""
    
    __tablename__ = "reminders"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to pet
    pet_id = Column(UUID(as_uuid=True), ForeignKey("pets.id"), nullable=False, index=True)
    
    # Foreign key to health record (optional)
    health_record_id = Column(UUID(as_uuid=True), ForeignKey("health_records.id"), nullable=True, index=True)
    
    # Reminder information
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    reminder_type = Column(String(50), nullable=False)  # vaccination, medication, checkup, etc.
    
    # Scheduling
    due_date = Column(Date, nullable=False, index=True)
    reminder_date = Column(Date, nullable=False, index=True)  # When to send reminder
    
    # Recurrence
    is_recurring = Column(Boolean, default=False, nullable=False)
    recurrence_interval_days = Column(Integer, nullable=True)
    
    # Status
    is_completed = Column(Boolean, default=False, nullable=False)
    is_sent = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    pet = relationship("Pet", back_populates="reminders", lazy="selectin")
    health_record = relationship("HealthRecord", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Reminder(id={self.id}, pet_id={self.pet_id}, title={self.title}, due_date={self.due_date})>"