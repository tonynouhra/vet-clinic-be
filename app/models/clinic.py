"""
Clinic and Veterinarian models with location data.
"""
import uuid
from datetime import datetime, time
from enum import Enum
from typing import List, Optional

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Float, Boolean, Time, Integer, Table
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ClinicType(str, Enum):
    """Clinic type enumeration."""
    GENERAL_PRACTICE = "general_practice"
    SPECIALTY_CLINIC = "specialty_clinic"
    EMERGENCY_CLINIC = "emergency_clinic"
    ANIMAL_HOSPITAL = "animal_hospital"
    MOBILE_CLINIC = "mobile_clinic"


class VeterinarianSpecialty(str, Enum):
    """Veterinarian specialty enumeration."""
    GENERAL_PRACTICE = "general_practice"
    SURGERY = "surgery"
    INTERNAL_MEDICINE = "internal_medicine"
    CARDIOLOGY = "cardiology"
    DERMATOLOGY = "dermatology"
    ONCOLOGY = "oncology"
    ORTHOPEDICS = "orthopedics"
    OPHTHALMOLOGY = "ophthalmology"
    DENTISTRY = "dentistry"
    EMERGENCY_CRITICAL_CARE = "emergency_critical_care"
    EXOTIC_ANIMALS = "exotic_animals"
    BEHAVIOR = "behavior"
    NUTRITION = "nutrition"
    RADIOLOGY = "radiology"
    ANESTHESIOLOGY = "anesthesiology"


class DayOfWeek(str, Enum):
    """Day of week enumeration."""
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


# Association table for veterinarian specialties
veterinarian_specialties = Table(
    'veterinarian_specialties',
    Base.metadata,
    Column('veterinarian_id', UUID(as_uuid=True), ForeignKey('veterinarians.id'), primary_key=True),
    Column('specialty', ENUM(VeterinarianSpecialty), primary_key=True),
    Column('certification_date', DateTime(timezone=True), nullable=True),
    Column('certification_body', String(200), nullable=True)
)


class Clinic(Base):
    """Clinic model with location and service information."""
    
    __tablename__ = "clinics"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic clinic information
    name = Column(String(200), nullable=False, index=True)
    clinic_type = Column(ENUM(ClinicType), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Contact information
    phone_number = Column(String(20), nullable=False)
    email = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    
    # Location information
    address_line1 = Column(String(200), nullable=False)
    address_line2 = Column(String(200), nullable=True)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(50), nullable=False, index=True)
    zip_code = Column(String(20), nullable=False, index=True)
    country = Column(String(50), nullable=False, default="United States")
    
    # Geographic coordinates for location-based searches
    latitude = Column(Float, nullable=True, index=True)
    longitude = Column(Float, nullable=True, index=True)
    
    # Services and facilities
    services_offered = Column(JSON, nullable=True)  # Array of services
    facilities = Column(JSON, nullable=True)  # Array of facilities
    equipment = Column(JSON, nullable=True)  # Array of equipment
    
    # Business information
    license_number = Column(String(100), nullable=True)
    accreditation = Column(JSON, nullable=True)  # Array of accreditations
    
    # Media
    logo_url = Column(String(500), nullable=True)
    photos = Column(JSON, nullable=True)  # Array of photo URLs
    
    # Emergency services
    is_emergency_clinic = Column(Boolean, default=False, nullable=False)
    emergency_phone = Column(String(20), nullable=True)
    is_24_hour = Column(Boolean, default=False, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_accepting_new_patients = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    veterinarians = relationship("Veterinarian", back_populates="clinic", lazy="selectin")
    appointments = relationship("Appointment", back_populates="clinic", lazy="selectin")
    operating_hours = relationship("ClinicOperatingHours", back_populates="clinic", lazy="selectin", cascade="all, delete-orphan")
    reviews = relationship("ClinicReview", back_populates="clinic", lazy="selectin", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Clinic(id={self.id}, name={self.name}, city={self.city}, state={self.state})>"
    
    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        address_parts = [self.address_line1]
        if self.address_line2:
            address_parts.append(self.address_line2)
        address_parts.extend([self.city, self.state, self.zip_code])
        return ", ".join(address_parts)
    
    @property
    def average_rating(self) -> Optional[float]:
        """Calculate average rating from reviews."""
        if not self.reviews:
            return None
        total_rating = sum(review.rating for review in self.reviews if review.rating)
        return total_rating / len(self.reviews) if self.reviews else None


class ClinicOperatingHours(Base):
    """Clinic operating hours model."""
    
    __tablename__ = "clinic_operating_hours"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to clinic
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True)
    
    # Day and hours
    day_of_week = Column(ENUM(DayOfWeek), nullable=False)
    is_open = Column(Boolean, default=True, nullable=False)
    open_time = Column(Time, nullable=True)
    close_time = Column(Time, nullable=True)
    
    # Break times (for lunch breaks, etc.)
    break_start_time = Column(Time, nullable=True)
    break_end_time = Column(Time, nullable=True)
    
    # Special notes
    notes = Column(String(200), nullable=True)
    
    # Relationships
    clinic = relationship("Clinic", back_populates="operating_hours", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<ClinicOperatingHours(clinic_id={self.clinic_id}, day={self.day_of_week}, open={self.is_open})>"


class Veterinarian(Base):
    """Veterinarian model with profile and specialty information."""
    
    __tablename__ = "veterinarians"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Foreign key to clinic
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True)
    
    # Professional information
    license_number = Column(String(100), nullable=False, unique=True, index=True)
    years_of_experience = Column(Integer, nullable=True)
    education = Column(JSON, nullable=True)  # Array of education details
    certifications = Column(JSON, nullable=True)  # Array of certifications
    
    # Professional bio
    bio = Column(Text, nullable=True)
    languages_spoken = Column(JSON, nullable=True)  # Array of languages
    
    # Consultation information
    consultation_fee = Column(Float, nullable=True)
    emergency_fee = Column(Float, nullable=True)
    
    # Availability
    is_available_for_emergency = Column(Boolean, default=False, nullable=False)
    is_accepting_new_patients = Column(Boolean, default=True, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="veterinarian_profile", lazy="selectin")
    clinic = relationship("Clinic", back_populates="veterinarians", lazy="selectin")
    specialties = relationship(
        "VeterinarianSpecialty",
        secondary=veterinarian_specialties,
        lazy="selectin"
    )
    appointments = relationship("Appointment", back_populates="veterinarian", lazy="selectin")
    availability = relationship("VeterinarianAvailability", back_populates="veterinarian", lazy="selectin", cascade="all, delete-orphan")
    reviews = relationship("VeterinarianReview", back_populates="veterinarian", lazy="selectin", cascade="all, delete-orphan")
    health_records = relationship("HealthRecord", back_populates="veterinarian", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<Veterinarian(id={self.id}, user_id={self.user_id}, license_number={self.license_number})>"
    
    @property
    def full_name(self) -> str:
        """Get veterinarian's full name from user relationship."""
        return self.user.full_name if self.user else "Unknown"
    
    @property
    def average_rating(self) -> Optional[float]:
        """Calculate average rating from reviews."""
        if not self.reviews:
            return None
        total_rating = sum(review.rating for review in self.reviews if review.rating)
        return total_rating / len(self.reviews) if self.reviews else None


class VeterinarianAvailability(Base):
    """Veterinarian availability schedule model."""
    
    __tablename__ = "veterinarian_availability"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to veterinarian
    veterinarian_id = Column(UUID(as_uuid=True), ForeignKey("veterinarians.id"), nullable=False, index=True)
    
    # Availability schedule
    day_of_week = Column(ENUM(DayOfWeek), nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    
    # Break times
    break_start_time = Column(Time, nullable=True)
    break_end_time = Column(Time, nullable=True)
    
    # Appointment duration (in minutes)
    default_appointment_duration = Column(Integer, default=30, nullable=False)
    
    # Special notes
    notes = Column(String(200), nullable=True)
    
    # Relationships
    veterinarian = relationship("Veterinarian", back_populates="availability", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<VeterinarianAvailability(vet_id={self.veterinarian_id}, day={self.day_of_week}, available={self.is_available})>"


class ClinicReview(Base):
    """Clinic review and rating model."""
    
    __tablename__ = "clinic_reviews"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Review content
    rating = Column(Integer, nullable=False)  # 1-5 stars
    title = Column(String(200), nullable=True)
    review_text = Column(Text, nullable=True)
    
    # Review metadata
    is_verified = Column(Boolean, default=False, nullable=False)
    is_anonymous = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    clinic = relationship("Clinic", back_populates="reviews", lazy="selectin")
    reviewer = relationship("User", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<ClinicReview(id={self.id}, clinic_id={self.clinic_id}, rating={self.rating})>"


class VeterinarianReview(Base):
    """Veterinarian review and rating model."""
    
    __tablename__ = "veterinarian_reviews"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    veterinarian_id = Column(UUID(as_uuid=True), ForeignKey("veterinarians.id"), nullable=False, index=True)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Review content
    rating = Column(Integer, nullable=False)  # 1-5 stars
    title = Column(String(200), nullable=True)
    review_text = Column(Text, nullable=True)
    
    # Review categories
    bedside_manner_rating = Column(Integer, nullable=True)  # 1-5 stars
    expertise_rating = Column(Integer, nullable=True)  # 1-5 stars
    communication_rating = Column(Integer, nullable=True)  # 1-5 stars
    
    # Review metadata
    is_verified = Column(Boolean, default=False, nullable=False)
    is_anonymous = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    veterinarian = relationship("Veterinarian", back_populates="reviews", lazy="selectin")
    reviewer = relationship("User", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<VeterinarianReview(id={self.id}, veterinarian_id={self.veterinarian_id}, rating={self.rating})>"