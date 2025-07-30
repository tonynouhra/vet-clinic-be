"""
Appointment models with veterinarian and clinic associations.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Float, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AppointmentStatus(str, Enum):
    """Appointment status enumeration."""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class AppointmentType(str, Enum):
    """Appointment type enumeration."""
    ROUTINE_CHECKUP = "routine_checkup"
    VACCINATION = "vaccination"
    SURGERY = "surgery"
    EMERGENCY = "emergency"
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    DENTAL = "dental"
    GROOMING = "grooming"
    DIAGNOSTIC = "diagnostic"
    TREATMENT = "treatment"
    OTHER = "other"


class AppointmentPriority(str, Enum):
    """Appointment priority enumeration."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    EMERGENCY = "emergency"


class Appointment(Base):
    """Appointment model for scheduling veterinary services."""
    
    __tablename__ = "appointments"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    pet_id = Column(UUID(as_uuid=True), ForeignKey("pets.id"), nullable=False, index=True)
    pet_owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    veterinarian_id = Column(UUID(as_uuid=True), ForeignKey("veterinarians.id"), nullable=False, index=True)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True)
    
    # Appointment details
    appointment_type = Column(ENUM(AppointmentType), nullable=False, index=True)
    status = Column(ENUM(AppointmentStatus), default=AppointmentStatus.SCHEDULED, nullable=False, index=True)
    priority = Column(ENUM(AppointmentPriority), default=AppointmentPriority.NORMAL, nullable=False, index=True)
    
    # Scheduling information
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes = Column(Integer, default=30, nullable=False)
    
    # Appointment content
    reason = Column(String(500), nullable=False)
    symptoms = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    special_instructions = Column(Text, nullable=True)
    
    # Service information
    services_requested = Column(JSON, nullable=True)  # Array of service names
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    
    # Status tracking
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(String(500), nullable=True)
    
    # Reminder tracking
    reminder_sent_24h = Column(Boolean, default=False, nullable=False)
    reminder_sent_2h = Column(Boolean, default=False, nullable=False)
    reminder_sent_24h_at = Column(DateTime(timezone=True), nullable=True)
    reminder_sent_2h_at = Column(DateTime(timezone=True), nullable=True)
    
    # Follow-up information
    follow_up_required = Column(Boolean, default=False, nullable=False)
    follow_up_date = Column(DateTime(timezone=True), nullable=True)
    follow_up_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    pet = relationship("Pet", back_populates="appointments", lazy="selectin")
    pet_owner = relationship("User", back_populates="appointments", lazy="selectin")
    veterinarian = relationship("Veterinarian", back_populates="appointments", lazy="selectin")
    clinic = relationship("Clinic", back_populates="appointments", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<Appointment(id={self.id}, pet_id={self.pet_id}, vet_id={self.veterinarian_id}, scheduled_at={self.scheduled_at})>"
    
    @property
    def is_upcoming(self) -> bool:
        """Check if appointment is upcoming."""
        return self.scheduled_at > datetime.utcnow() and self.status in [
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CONFIRMED
        ]
    
    @property
    def is_past(self) -> bool:
        """Check if appointment is in the past."""
        return self.scheduled_at < datetime.utcnow()
    
    @property
    def is_today(self) -> bool:
        """Check if appointment is today."""
        today = datetime.utcnow().date()
        return self.scheduled_at.date() == today
    
    @property
    def can_be_cancelled(self) -> bool:
        """Check if appointment can be cancelled."""
        return self.status in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]
    
    @property
    def can_be_rescheduled(self) -> bool:
        """Check if appointment can be rescheduled."""
        return self.status in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]
    
    def cancel(self, reason: Optional[str] = None) -> None:
        """Cancel the appointment."""
        if self.can_be_cancelled:
            self.status = AppointmentStatus.CANCELLED
            self.cancelled_at = datetime.utcnow()
            self.cancellation_reason = reason
    
    def confirm(self) -> None:
        """Confirm the appointment."""
        if self.status == AppointmentStatus.SCHEDULED:
            self.status = AppointmentStatus.CONFIRMED
            self.confirmed_at = datetime.utcnow()
    
    def check_in(self) -> None:
        """Check in for the appointment."""
        if self.status == AppointmentStatus.CONFIRMED:
            self.checked_in_at = datetime.utcnow()
    
    def start(self) -> None:
        """Start the appointment."""
        if self.status in [AppointmentStatus.CONFIRMED, AppointmentStatus.SCHEDULED]:
            self.status = AppointmentStatus.IN_PROGRESS
            self.started_at = datetime.utcnow()
    
    def complete(self, actual_cost: Optional[float] = None) -> None:
        """Complete the appointment."""
        if self.status == AppointmentStatus.IN_PROGRESS:
            self.status = AppointmentStatus.COMPLETED
            self.completed_at = datetime.utcnow()
            if actual_cost is not None:
                self.actual_cost = actual_cost


class AppointmentSlot(Base):
    """Available appointment slots for scheduling."""
    
    __tablename__ = "appointment_slots"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    veterinarian_id = Column(UUID(as_uuid=True), ForeignKey("veterinarians.id"), nullable=False, index=True)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, index=True)
    
    # Slot information
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes = Column(Integer, default=30, nullable=False)
    
    # Availability
    is_available = Column(Boolean, default=True, nullable=False, index=True)
    is_blocked = Column(Boolean, default=False, nullable=False)
    block_reason = Column(String(200), nullable=True)
    
    # Slot type
    slot_type = Column(String(50), default="regular", nullable=False)  # regular, emergency, walk-in
    max_bookings = Column(Integer, default=1, nullable=False)
    current_bookings = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    veterinarian = relationship("Veterinarian", lazy="selectin")
    clinic = relationship("Clinic", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<AppointmentSlot(id={self.id}, vet_id={self.veterinarian_id}, start_time={self.start_time}, available={self.is_available})>"
    
    @property
    def is_fully_booked(self) -> bool:
        """Check if slot is fully booked."""
        return self.current_bookings >= self.max_bookings
    
    @property
    def remaining_capacity(self) -> int:
        """Get remaining booking capacity."""
        return max(0, self.max_bookings - self.current_bookings)
    
    def book_slot(self) -> bool:
        """Book the slot if available."""
        if self.is_available and not self.is_fully_booked:
            self.current_bookings += 1
            return True
        return False
    
    def release_slot(self) -> bool:
        """Release a booking from the slot."""
        if self.current_bookings > 0:
            self.current_bookings -= 1
            return True
        return False