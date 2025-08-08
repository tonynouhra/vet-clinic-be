"""
V1 Pet schemas for basic pet management operations.

V1 focuses on essential pet information and basic CRUD operations.
"""

from typing import Optional, List
from datetime import date, datetime
from pydantic import Field, validator
import uuid

from app.api.schemas.base import BaseSchema, TimestampMixin, IDMixin, create_response_model
from app.api.schemas.validators import SchemaValidationMixin
from app.models.pet import PetGender, PetSize, HealthRecordType


class PetCreateV1(BaseSchema, SchemaValidationMixin):
    """V1 schema for creating pets with basic information."""
    
    owner_id: uuid.UUID = Field(..., description="Owner's user ID")
    name: str = Field(..., min_length=1, max_length=100, description="Pet name")
    species: str = Field(..., min_length=1, max_length=50, description="Pet species (dog, cat, etc.)")
    breed: Optional[str] = Field(None, max_length=100, description="Pet breed")
    mixed_breed: bool = Field(False, description="Is mixed breed")
    gender: PetGender = Field(PetGender.UNKNOWN, description="Pet gender")
    size: Optional[PetSize] = Field(None, description="Pet size category")
    weight: Optional[float] = Field(None, gt=0, description="Pet weight in pounds")
    color: Optional[str] = Field(None, max_length=100, description="Pet color")
    birth_date: Optional[date] = Field(None, description="Pet birth date")
    age_years: Optional[int] = Field(None, ge=0, le=50, description="Age in years")
    age_months: Optional[int] = Field(None, ge=0, le=11, description="Age in months")
    is_age_estimated: bool = Field(False, description="Is age estimated")
    microchip_id: Optional[str] = Field(None, max_length=50, description="Microchip ID")
    registration_number: Optional[str] = Field(None, max_length=100, description="Registration number")
    medical_notes: Optional[str] = Field(None, description="Medical notes")
    allergies: Optional[str] = Field(None, description="Known allergies")
    current_medications: Optional[str] = Field(None, description="Current medications")
    special_needs: Optional[str] = Field(None, description="Special needs")
    profile_image_url: Optional[str] = Field(None, max_length=500, description="Profile image URL")

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Pet name cannot be empty')
        return v.strip()

    @validator('species')
    def validate_species(cls, v):
        if not v or not v.strip():
            raise ValueError('Pet species cannot be empty')
        return v.strip().lower()

    @validator('breed')
    def validate_breed(cls, v):
        if v is not None:
            return v.strip() if v.strip() else None
        return v

    @validator('color')
    def validate_color(cls, v):
        if v is not None:
            return v.strip() if v.strip() else None
        return v

    @validator('microchip_id')
    def validate_microchip_id(cls, v):
        if v is not None:
            v = v.strip()
            if v and len(v) < 8:
                raise ValueError('Microchip ID must be at least 8 characters')
            return v if v else None
        return v

    @validator('birth_date')
    def validate_birth_date(cls, v):
        if v is not None and v > date.today():
            raise ValueError('Birth date cannot be in the future')
        return v


class PetUpdateV1(BaseSchema, SchemaValidationMixin):
    """V1 schema for updating pets with basic information."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Pet name")
    species: Optional[str] = Field(None, min_length=1, max_length=50, description="Pet species")
    breed: Optional[str] = Field(None, max_length=100, description="Pet breed")
    mixed_breed: Optional[bool] = Field(None, description="Is mixed breed")
    gender: Optional[PetGender] = Field(None, description="Pet gender")
    size: Optional[PetSize] = Field(None, description="Pet size category")
    weight: Optional[float] = Field(None, gt=0, description="Pet weight in pounds")
    color: Optional[str] = Field(None, max_length=100, description="Pet color")
    birth_date: Optional[date] = Field(None, description="Pet birth date")
    age_years: Optional[int] = Field(None, ge=0, le=50, description="Age in years")
    age_months: Optional[int] = Field(None, ge=0, le=11, description="Age in months")
    is_age_estimated: Optional[bool] = Field(None, description="Is age estimated")
    microchip_id: Optional[str] = Field(None, max_length=50, description="Microchip ID")
    registration_number: Optional[str] = Field(None, max_length=100, description="Registration number")
    medical_notes: Optional[str] = Field(None, description="Medical notes")
    allergies: Optional[str] = Field(None, description="Known allergies")
    current_medications: Optional[str] = Field(None, description="Current medications")
    special_needs: Optional[str] = Field(None, description="Special needs")
    profile_image_url: Optional[str] = Field(None, max_length=500, description="Profile image URL")
    is_active: Optional[bool] = Field(None, description="Is pet active")

    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not v or not v.strip():
                raise ValueError('Pet name cannot be empty')
            return v.strip()
        return v

    @validator('species')
    def validate_species(cls, v):
        if v is not None:
            if not v or not v.strip():
                raise ValueError('Pet species cannot be empty')
            return v.strip().lower()
        return v

    @validator('breed')
    def validate_breed(cls, v):
        if v is not None:
            return v.strip() if v.strip() else None
        return v

    @validator('color')
    def validate_color(cls, v):
        if v is not None:
            return v.strip() if v.strip() else None
        return v

    @validator('microchip_id')
    def validate_microchip_id(cls, v):
        if v is not None:
            v = v.strip()
            if v and len(v) < 8:
                raise ValueError('Microchip ID must be at least 8 characters')
            return v if v else None
        return v

    @validator('birth_date')
    def validate_birth_date(cls, v):
        if v is not None and v > date.today():
            raise ValueError('Birth date cannot be in the future')
        return v


class PetResponseV1(BaseSchema, IDMixin, TimestampMixin):
    """V1 schema for pet responses with basic information."""
    
    owner_id: uuid.UUID = Field(..., description="Owner's user ID")
    name: str = Field(..., description="Pet name")
    species: str = Field(..., description="Pet species")
    breed: Optional[str] = Field(None, description="Pet breed")
    mixed_breed: bool = Field(..., description="Is mixed breed")
    gender: PetGender = Field(..., description="Pet gender")
    size: Optional[PetSize] = Field(None, description="Pet size category")
    weight: Optional[float] = Field(None, description="Pet weight in pounds")
    color: Optional[str] = Field(None, description="Pet color")
    birth_date: Optional[date] = Field(None, description="Pet birth date")
    age_years: Optional[int] = Field(None, description="Age in years")
    age_months: Optional[int] = Field(None, description="Age in months")
    is_age_estimated: bool = Field(..., description="Is age estimated")
    age_display: str = Field(..., description="Formatted age display")
    microchip_id: Optional[str] = Field(None, description="Microchip ID")
    registration_number: Optional[str] = Field(None, description="Registration number")
    medical_notes: Optional[str] = Field(None, description="Medical notes")
    allergies: Optional[str] = Field(None, description="Known allergies")
    current_medications: Optional[str] = Field(None, description="Current medications")
    special_needs: Optional[str] = Field(None, description="Special needs")
    temperament: Optional[str] = Field(None, description="Pet temperament")
    behavioral_notes: Optional[str] = Field(None, description="Behavioral notes")
    profile_image_url: Optional[str] = Field(None, description="Profile image URL")
    is_active: bool = Field(..., description="Is pet active")
    is_deceased: bool = Field(..., description="Is pet deceased")
    deceased_date: Optional[date] = Field(None, description="Date of death")

    class Config:
        from_attributes = True


class PetListResponseV1(BaseSchema):
    """V1 schema for paginated pet list responses."""
    
    pets: List[PetResponseV1] = Field(..., description="List of pets")
    total: int = Field(..., description="Total number of pets")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")

    @validator('total_pages', pre=True, always=True)
    def calculate_total_pages(cls, v, values):
        total = values.get('total', 0)
        per_page = values.get('per_page', 10)
        if per_page <= 0:
            return 0
        return (total + per_page - 1) // per_page


class DeceasedPetRequestV1(BaseSchema):
    """V1 schema for marking pet as deceased."""
    
    deceased_date: date = Field(..., description="Date of death")

    @validator('deceased_date')
    def validate_deceased_date(cls, v):
        if v > date.today():
            raise ValueError('Deceased date cannot be in the future')
        return v


class HealthRecordCreateV1(BaseSchema, SchemaValidationMixin):
    """V1 schema for creating health records."""
    
    record_type: HealthRecordType = Field(..., description="Record type")
    title: str = Field(..., min_length=1, max_length=200, description="Record title")
    description: Optional[str] = Field(None, description="Record description")
    record_date: date = Field(..., description="Record date")
    next_due_date: Optional[date] = Field(None, description="Next due date for recurring items")
    diagnosis: Optional[str] = Field(None, description="Diagnosis")
    treatment: Optional[str] = Field(None, description="Treatment provided")
    medication_name: Optional[str] = Field(None, max_length=200, description="Medication name")
    dosage: Optional[str] = Field(None, max_length=100, description="Medication dosage")
    frequency: Optional[str] = Field(None, max_length=100, description="Medication frequency")
    duration: Optional[str] = Field(None, max_length=100, description="Treatment duration")
    cost: Optional[float] = Field(None, ge=0, description="Cost of treatment")
    notes: Optional[str] = Field(None, description="Additional notes")

    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Health record title cannot be empty')
        return v.strip()

    @validator('record_date')
    def validate_record_date(cls, v):
        if v > date.today():
            raise ValueError('Record date cannot be in the future')
        return v

    @validator('next_due_date')
    def validate_next_due_date(cls, v, values):
        if v is not None:
            record_date = values.get('record_date')
            if record_date and v <= record_date:
                raise ValueError('Next due date must be after record date')
        return v


class HealthRecordResponseV1(BaseSchema, IDMixin, TimestampMixin):
    """V1 schema for health record responses."""
    
    pet_id: uuid.UUID = Field(..., description="Pet ID")
    veterinarian_id: Optional[uuid.UUID] = Field(None, description="Veterinarian ID")
    record_type: HealthRecordType = Field(..., description="Record type")
    title: str = Field(..., description="Record title")
    description: Optional[str] = Field(None, description="Record description")
    record_date: date = Field(..., description="Record date")
    next_due_date: Optional[date] = Field(None, description="Next due date")
    diagnosis: Optional[str] = Field(None, description="Diagnosis")
    treatment: Optional[str] = Field(None, description="Treatment provided")
    medication_name: Optional[str] = Field(None, description="Medication name")
    dosage: Optional[str] = Field(None, description="Medication dosage")
    frequency: Optional[str] = Field(None, description="Medication frequency")
    duration: Optional[str] = Field(None, description="Treatment duration")
    cost: Optional[float] = Field(None, description="Cost of treatment")
    notes: Optional[str] = Field(None, description="Additional notes")
    is_active: bool = Field(..., description="Is record active")

    class Config:
        from_attributes = True


# Response model factories for V1
PetCreateResponseV1 = create_response_model(PetResponseV1, "v1")
PetUpdateResponseV1 = create_response_model(PetResponseV1, "v1")
PetGetResponseV1 = create_response_model(PetResponseV1, "v1")
PetListResponseModelV1 = create_response_model(PetListResponseV1, "v1")
PetDeleteResponseV1 = create_response_model(dict, "v1")  # Simple success message
PetDeceasedResponseV1 = create_response_model(PetResponseV1, "v1")
class ReminderCreateV1(BaseSchema, SchemaValidationMixin):
    """V1 schema for creating reminders."""
    
    title: str = Field(..., min_length=1, max_length=200, description="Reminder title")
    description: Optional[str] = Field(None, description="Reminder description")
    reminder_type: str = Field(..., description="Type of reminder (vaccination, medication, checkup, etc.)")
    due_date: date = Field(..., description="Due date")
    reminder_date: date = Field(..., description="When to send reminder")
    health_record_id: Optional[uuid.UUID] = Field(None, description="Associated health record ID")
    is_recurring: bool = Field(False, description="Is recurring reminder")
    recurrence_interval_days: Optional[int] = Field(None, ge=1, description="Recurrence interval in days")

    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Reminder title cannot be empty')
        return v.strip()

    @validator('reminder_date')
    def validate_reminder_date(cls, v, values):
        due_date = values.get('due_date')
        if due_date and v > due_date:
            raise ValueError('Reminder date cannot be after due date')
        return v

    @validator('recurrence_interval_days')
    def validate_recurrence_interval(cls, v, values):
        is_recurring = values.get('is_recurring', False)
        if is_recurring and not v:
            raise ValueError('Recurrence interval is required for recurring reminders')
        if not is_recurring and v:
            raise ValueError('Recurrence interval should not be set for non-recurring reminders')
        return v


class ReminderResponseV1(BaseSchema, IDMixin, TimestampMixin):
    """V1 schema for reminder responses."""
    
    pet_id: uuid.UUID = Field(..., description="Pet ID")
    health_record_id: Optional[uuid.UUID] = Field(None, description="Associated health record ID")
    title: str = Field(..., description="Reminder title")
    description: Optional[str] = Field(None, description="Reminder description")
    reminder_type: str = Field(..., description="Type of reminder")
    due_date: date = Field(..., description="Due date")
    reminder_date: date = Field(..., description="When to send reminder")
    is_recurring: bool = Field(..., description="Is recurring reminder")
    recurrence_interval_days: Optional[int] = Field(None, description="Recurrence interval in days")
    is_completed: bool = Field(..., description="Is reminder completed")
    is_sent: bool = Field(..., description="Is reminder sent")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    sent_at: Optional[datetime] = Field(None, description="Sent timestamp")

    class Config:
        from_attributes = True


PetHealthRecordResponseV1 = create_response_model(HealthRecordResponseV1, "v1")
PetReminderResponseV1 = create_response_model(ReminderResponseV1, "v1")