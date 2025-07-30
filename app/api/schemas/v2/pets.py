"""
V2 Pet schemas for enhanced pet management operations.

V2 includes all V1 features plus:
- Enhanced health record integration
- Additional photos support
- Advanced filtering and sorting
- Batch operations
- Pet statistics
- Appointment history integration
- Owner information inclusion
"""

from typing import Optional, List, Dict, Any
from datetime import date
from pydantic import Field, validator
import uuid

from app.api.schemas.base import BaseSchema, TimestampMixin, IDMixin, create_response_model
from app.api.schemas.validators import SchemaValidationMixin
from app.models.pet import PetGender, PetSize, HealthRecordType


class PetCreateV2(BaseSchema, SchemaValidationMixin):
    """V2 schema for creating pets with enhanced information."""
    
    # Basic pet information (inherited from V1)
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
    temperament: Optional[str] = Field(None, max_length=200, description="Pet temperament")
    behavioral_notes: Optional[str] = Field(None, description="Behavioral notes")
    profile_image_url: Optional[str] = Field(None, max_length=500, description="Profile image URL")
    
    # V2 Enhanced features
    additional_photos: Optional[List[str]] = Field(None, max_items=10, description="Additional photo URLs")
    initial_health_record: Optional[Dict[str, Any]] = Field(None, description="Initial health record data")
    emergency_contact: Optional[Dict[str, str]] = Field(None, description="Emergency contact information")
    insurance_info: Optional[Dict[str, str]] = Field(None, description="Pet insurance information")
    preferred_vet_id: Optional[uuid.UUID] = Field(None, description="Preferred veterinarian ID")

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

    @validator('additional_photos')
    def validate_additional_photos(cls, v):
        if v is not None:
            # Validate URLs
            for url in v:
                if not url or not url.strip():
                    raise ValueError('Photo URLs cannot be empty')
            return [url.strip() for url in v if url.strip()]
        return v

    @validator('emergency_contact')
    def validate_emergency_contact(cls, v):
        if v is not None:
            required_fields = ['name', 'phone']
            for field in required_fields:
                if field not in v or not v[field].strip():
                    raise ValueError(f'Emergency contact {field} is required')
        return v


class PetUpdateV2(BaseSchema, SchemaValidationMixin):
    """V2 schema for updating pets with enhanced information."""
    
    # Basic pet information (inherited from V1)
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
    temperament: Optional[str] = Field(None, max_length=200, description="Pet temperament")
    behavioral_notes: Optional[str] = Field(None, description="Behavioral notes")
    profile_image_url: Optional[str] = Field(None, max_length=500, description="Profile image URL")
    is_active: Optional[bool] = Field(None, description="Is pet active")
    
    # V2 Enhanced features
    additional_photos: Optional[List[str]] = Field(None, max_items=10, description="Additional photo URLs")
    emergency_contact: Optional[Dict[str, str]] = Field(None, description="Emergency contact information")
    insurance_info: Optional[Dict[str, str]] = Field(None, description="Pet insurance information")
    preferred_vet_id: Optional[uuid.UUID] = Field(None, description="Preferred veterinarian ID")

    # Same validators as create schema
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

    @validator('additional_photos')
    def validate_additional_photos(cls, v):
        if v is not None:
            for url in v:
                if not url or not url.strip():
                    raise ValueError('Photo URLs cannot be empty')
            return [url.strip() for url in v if url.strip()]
        return v

    @validator('emergency_contact')
    def validate_emergency_contact(cls, v):
        if v is not None and v:  # Only validate if not empty
            required_fields = ['name', 'phone']
            for field in required_fields:
                if field not in v or not v[field].strip():
                    raise ValueError(f'Emergency contact {field} is required')
        return v


class HealthRecordResponseV2(BaseSchema, IDMixin, TimestampMixin):
    """V2 health record response schema."""
    
    pet_id: uuid.UUID = Field(..., description="Pet ID")
    veterinarian_id: Optional[uuid.UUID] = Field(None, description="Veterinarian ID")
    record_type: HealthRecordType = Field(..., description="Record type")
    title: str = Field(..., description="Record title")
    description: Optional[str] = Field(None, description="Record description")
    record_date: date = Field(..., description="Record date")
    next_due_date: Optional[date] = Field(None, description="Next due date")
    diagnosis: Optional[str] = Field(None, description="Diagnosis")
    treatment: Optional[str] = Field(None, description="Treatment")
    medication_name: Optional[str] = Field(None, description="Medication name")
    dosage: Optional[str] = Field(None, description="Dosage")
    frequency: Optional[str] = Field(None, description="Frequency")
    duration: Optional[str] = Field(None, description="Duration")
    cost: Optional[float] = Field(None, description="Cost")
    notes: Optional[str] = Field(None, description="Additional notes")

    class Config:
        from_attributes = True


class OwnerInfoV2(BaseSchema):
    """V2 owner information schema."""
    
    id: uuid.UUID = Field(..., description="Owner ID")
    email: str = Field(..., description="Owner email")
    first_name: str = Field(..., description="Owner first name")
    last_name: str = Field(..., description="Owner last name")
    phone_number: Optional[str] = Field(None, description="Owner phone number")

    class Config:
        from_attributes = True


class PetResponseV2(BaseSchema, IDMixin, TimestampMixin):
    """V2 schema for pet responses with enhanced information."""
    
    # Basic pet information (inherited from V1)
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
    
    # V2 Enhanced features
    additional_photos: Optional[List[str]] = Field(None, description="Additional photo URLs")
    emergency_contact: Optional[Dict[str, str]] = Field(None, description="Emergency contact information")
    insurance_info: Optional[Dict[str, str]] = Field(None, description="Pet insurance information")
    preferred_vet_id: Optional[uuid.UUID] = Field(None, description="Preferred veterinarian ID")
    
    # V2 Relationship data (optional)
    owner: Optional[OwnerInfoV2] = Field(None, description="Owner information")
    health_records: Optional[List[HealthRecordResponseV2]] = Field(None, description="Health records")
    total_appointments: Optional[int] = Field(None, description="Total appointments count")
    last_appointment_date: Optional[date] = Field(None, description="Last appointment date")
    next_appointment_date: Optional[date] = Field(None, description="Next appointment date")

    class Config:
        from_attributes = True


class PetListResponseV2(BaseSchema):
    """V2 schema for paginated pet list responses with enhanced information."""
    
    pets: List[PetResponseV2] = Field(..., description="List of pets")
    total: int = Field(..., description="Total number of pets")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    # V2 enhanced metadata
    statistics: Optional[Dict[str, Any]] = Field(None, description="List statistics")
    filters_applied: Optional[Dict[str, Any]] = Field(None, description="Applied filters summary")

    @validator('total_pages', pre=True, always=True)
    def calculate_total_pages(cls, v, values):
        total = values.get('total', 0)
        per_page = values.get('per_page', 10)
        if per_page <= 0:
            return 0
        return (total + per_page - 1) // per_page


class PetStatisticsV2(BaseSchema):
    """V2 pet statistics schema."""
    
    total_health_records: int = Field(..., description="Total health records")
    total_appointments: int = Field(..., description="Total appointments")
    last_checkup_date: Optional[date] = Field(None, description="Last checkup date")
    next_due_vaccination: Optional[date] = Field(None, description="Next vaccination due")
    days_since_registration: int = Field(..., description="Days since pet registration")
    weight_history_count: int = Field(0, description="Number of weight records")
    active_medications_count: int = Field(0, description="Number of active medications")


class HealthRecordCreateV2(BaseSchema):
    """V2 schema for creating health records."""
    
    record_type: HealthRecordType = Field(..., description="Record type")
    title: str = Field(..., min_length=1, max_length=200, description="Record title")
    description: Optional[str] = Field(None, description="Record description")
    record_date: date = Field(..., description="Record date")
    next_due_date: Optional[date] = Field(None, description="Next due date")
    diagnosis: Optional[str] = Field(None, description="Diagnosis")
    treatment: Optional[str] = Field(None, description="Treatment")
    medication_name: Optional[str] = Field(None, max_length=200, description="Medication name")
    dosage: Optional[str] = Field(None, max_length=100, description="Dosage")
    frequency: Optional[str] = Field(None, max_length=100, description="Frequency")
    duration: Optional[str] = Field(None, max_length=100, description="Duration")
    cost: Optional[float] = Field(None, ge=0, description="Cost")
    notes: Optional[str] = Field(None, description="Additional notes")

    @validator('record_date')
    def validate_record_date(cls, v):
        if v > date.today():
            raise ValueError('Record date cannot be in the future')
        return v

    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Health record title cannot be empty')
        return v.strip()


class DeceasedPetRequestV2(BaseSchema):
    """V2 schema for marking pet as deceased with enhanced information."""
    
    deceased_date: date = Field(..., description="Date of death")
    cause_of_death: Optional[str] = Field(None, description="Cause of death")
    notes: Optional[str] = Field(None, description="Additional notes")
    notify_owner: bool = Field(True, description="Send notification to owner")

    @validator('deceased_date')
    def validate_deceased_date(cls, v):
        if v > date.today():
            raise ValueError('Deceased date cannot be in the future')
        return v


class BatchPetOperationV2(BaseSchema):
    """V2 schema for batch pet operations."""
    
    pet_ids: List[uuid.UUID] = Field(..., min_items=1, max_items=50, description="Pet IDs")
    operation: str = Field(..., description="Operation type (activate, deactivate, bulk_update)")
    operation_data: Optional[Dict[str, Any]] = Field(None, description="Operation-specific data")
    
    @validator('operation')
    def validate_operation(cls, v):
        allowed_operations = ['activate', 'deactivate', 'bulk_update', 'export']
        if v not in allowed_operations:
            raise ValueError(f'Operation must be one of: {", ".join(allowed_operations)}')
        return v


# Response model factories for V2
PetCreateResponseV2 = create_response_model(PetResponseV2, "v2")
PetUpdateResponseV2 = create_response_model(PetResponseV2, "v2")
PetGetResponseV2 = create_response_model(PetResponseV2, "v2")
PetListResponseModelV2 = create_response_model(PetListResponseV2, "v2")
PetDeleteResponseV2 = create_response_model(dict, "v2")  # Simple success message
PetDeceasedResponseV2 = create_response_model(PetResponseV2, "v2")
PetStatisticsResponseV2 = create_response_model(PetStatisticsV2, "v2")
PetHealthRecordResponseV2 = create_response_model(HealthRecordResponseV2, "v2")
PetBatchOperationResponseV2 = create_response_model(dict, "v2")  # Batch operation results