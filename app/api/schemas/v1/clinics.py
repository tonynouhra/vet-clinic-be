"""
V1 Clinic and Veterinarian schemas for basic clinic management operations.

V1 focuses on essential clinic and veterinarian information and basic operations.
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime, time
from pydantic import Field, validator
import uuid

from app.api.schemas.base import BaseSchema, TimestampMixin, IDMixin, create_response_model
from app.api.schemas.validators import SchemaValidationMixin
from app.models.clinic import ClinicType, VeterinarianSpecialty, DayOfWeek


# Clinic Schemas

class ClinicResponseV1(BaseSchema, IDMixin, TimestampMixin):
    """V1 schema for clinic responses with basic information."""
    
    name: str = Field(..., description="Clinic name")
    clinic_type: ClinicType = Field(..., description="Type of clinic")
    description: Optional[str] = Field(None, description="Clinic description")
    phone_number: str = Field(..., description="Primary phone number")
    email: Optional[str] = Field(None, description="Contact email")
    website: Optional[str] = Field(None, description="Website URL")
    
    # Address information
    address_line1: str = Field(..., description="Address line 1")
    address_line2: Optional[str] = Field(None, description="Address line 2")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State")
    zip_code: str = Field(..., description="ZIP code")
    country: str = Field(..., description="Country")
    full_address: str = Field(..., description="Formatted full address")
    
    # Location coordinates
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    
    # Services and facilities
    services_offered: Optional[List[str]] = Field(None, description="Services offered")
    facilities: Optional[List[str]] = Field(None, description="Available facilities")
    
    # Emergency services
    is_emergency_clinic: bool = Field(..., description="Is emergency clinic")
    emergency_phone: Optional[str] = Field(None, description="Emergency phone number")
    is_24_hour: bool = Field(..., description="Is 24-hour clinic")
    
    # Status
    is_active: bool = Field(..., description="Is clinic active")
    is_accepting_new_patients: bool = Field(..., description="Is accepting new patients")
    
    # Rating information
    average_rating: Optional[float] = Field(None, description="Average rating from reviews")

    class Config:
        from_attributes = True


class ClinicListResponseV1(BaseSchema):
    """V1 schema for paginated clinic list responses."""
    
    clinics: List[ClinicResponseV1] = Field(..., description="List of clinics")
    total: int = Field(..., description="Total number of clinics")
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


# Veterinarian Schemas

class VeterinarianResponseV1(BaseSchema, IDMixin, TimestampMixin):
    """V1 schema for veterinarian responses with basic information."""
    
    user_id: uuid.UUID = Field(..., description="Associated user ID")
    clinic_id: uuid.UUID = Field(..., description="Associated clinic ID")
    license_number: str = Field(..., description="Professional license number")
    years_of_experience: Optional[int] = Field(None, description="Years of experience")
    bio: Optional[str] = Field(None, description="Professional biography")
    
    # Professional information
    education: Optional[List[Dict[str, Any]]] = Field(None, description="Education details")
    certifications: Optional[List[Dict[str, Any]]] = Field(None, description="Certifications")
    languages_spoken: Optional[List[str]] = Field(None, description="Languages spoken")
    
    # Consultation information
    consultation_fee: Optional[float] = Field(None, description="Consultation fee")
    emergency_fee: Optional[float] = Field(None, description="Emergency consultation fee")
    
    # Availability
    is_available_for_emergency: bool = Field(..., description="Available for emergency calls")
    is_accepting_new_patients: bool = Field(..., description="Accepting new patients")
    
    # Status
    is_active: bool = Field(..., description="Is veterinarian active")
    
    # User information (from relationship)
    full_name: str = Field(..., description="Veterinarian's full name")
    
    # Rating information
    average_rating: Optional[float] = Field(None, description="Average rating from reviews")

    class Config:
        from_attributes = True


class VeterinarianListResponseV1(BaseSchema):
    """V1 schema for paginated veterinarian list responses."""
    
    veterinarians: List[VeterinarianResponseV1] = Field(..., description="List of veterinarians")
    total: int = Field(..., description="Total number of veterinarians")
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


# Availability Schemas

class VeterinarianAvailabilityResponseV1(BaseSchema, IDMixin):
    """V1 schema for veterinarian availability responses."""
    
    veterinarian_id: uuid.UUID = Field(..., description="Veterinarian ID")
    day_of_week: DayOfWeek = Field(..., description="Day of the week")
    is_available: bool = Field(..., description="Is available on this day")
    start_time: Optional[time] = Field(None, description="Start time")
    end_time: Optional[time] = Field(None, description="End time")
    break_start_time: Optional[time] = Field(None, description="Break start time")
    break_end_time: Optional[time] = Field(None, description="Break end time")
    default_appointment_duration: int = Field(..., description="Default appointment duration in minutes")
    notes: Optional[str] = Field(None, description="Additional notes")

    class Config:
        from_attributes = True


class VeterinarianAvailabilityUpdateV1(BaseSchema, SchemaValidationMixin):
    """V1 schema for updating veterinarian availability."""
    
    day_of_week: DayOfWeek = Field(..., description="Day of the week")
    is_available: bool = Field(True, description="Is available on this day")
    start_time: Optional[time] = Field(None, description="Start time")
    end_time: Optional[time] = Field(None, description="End time")
    break_start_time: Optional[time] = Field(None, description="Break start time")
    break_end_time: Optional[time] = Field(None, description="Break end time")
    default_appointment_duration: int = Field(30, ge=15, le=240, description="Default appointment duration in minutes")
    notes: Optional[str] = Field(None, max_length=200, description="Additional notes")

    @validator('end_time')
    def validate_end_time(cls, v, values):
        start_time = values.get('start_time')
        is_available = values.get('is_available', True)
        
        if is_available and start_time and v:
            if v <= start_time:
                raise ValueError('End time must be after start time')
        return v

    @validator('break_end_time')
    def validate_break_end_time(cls, v, values):
        break_start_time = values.get('break_start_time')
        
        if break_start_time and v:
            if v <= break_start_time:
                raise ValueError('Break end time must be after break start time')
        return v


class VeterinarianAvailabilityBulkUpdateV1(BaseSchema):
    """V1 schema for bulk updating veterinarian availability."""
    
    availability: List[VeterinarianAvailabilityUpdateV1] = Field(..., description="List of availability updates")

    @validator('availability')
    def validate_availability_list(cls, v):
        if not v:
            raise ValueError('At least one availability entry is required')
        
        # Check for duplicate days
        days = [entry.day_of_week for entry in v]
        if len(days) != len(set(days)):
            raise ValueError('Duplicate days of week are not allowed')
        
        return v


# Review Schemas

class ClinicReviewCreateV1(BaseSchema, SchemaValidationMixin):
    """V1 schema for creating clinic reviews."""
    
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    title: Optional[str] = Field(None, max_length=200, description="Review title")
    review_text: Optional[str] = Field(None, max_length=2000, description="Review text")
    is_anonymous: bool = Field(False, description="Is anonymous review")

    @validator('title')
    def validate_title(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Review title cannot be empty')
        return v.strip() if v else None

    @validator('review_text')
    def validate_review_text(cls, v):
        if v is not None:
            return v.strip() if v.strip() else None
        return v


class VeterinarianReviewCreateV1(BaseSchema, SchemaValidationMixin):
    """V1 schema for creating veterinarian reviews."""
    
    rating: int = Field(..., ge=1, le=5, description="Overall rating from 1 to 5 stars")
    title: Optional[str] = Field(None, max_length=200, description="Review title")
    review_text: Optional[str] = Field(None, max_length=2000, description="Review text")
    bedside_manner_rating: Optional[int] = Field(None, ge=1, le=5, description="Bedside manner rating")
    expertise_rating: Optional[int] = Field(None, ge=1, le=5, description="Expertise rating")
    communication_rating: Optional[int] = Field(None, ge=1, le=5, description="Communication rating")
    is_anonymous: bool = Field(False, description="Is anonymous review")

    @validator('title')
    def validate_title(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Review title cannot be empty')
        return v.strip() if v else None

    @validator('review_text')
    def validate_review_text(cls, v):
        if v is not None:
            return v.strip() if v.strip() else None
        return v


class ClinicReviewResponseV1(BaseSchema, IDMixin, TimestampMixin):
    """V1 schema for clinic review responses."""
    
    clinic_id: uuid.UUID = Field(..., description="Clinic ID")
    reviewer_id: uuid.UUID = Field(..., description="Reviewer user ID")
    rating: int = Field(..., description="Rating from 1 to 5 stars")
    title: Optional[str] = Field(None, description="Review title")
    review_text: Optional[str] = Field(None, description="Review text")
    is_verified: bool = Field(..., description="Is review verified")
    is_anonymous: bool = Field(..., description="Is anonymous review")

    class Config:
        from_attributes = True


class VeterinarianReviewResponseV1(BaseSchema, IDMixin, TimestampMixin):
    """V1 schema for veterinarian review responses."""
    
    veterinarian_id: uuid.UUID = Field(..., description="Veterinarian ID")
    reviewer_id: uuid.UUID = Field(..., description="Reviewer user ID")
    rating: int = Field(..., description="Overall rating from 1 to 5 stars")
    title: Optional[str] = Field(None, description="Review title")
    review_text: Optional[str] = Field(None, description="Review text")
    bedside_manner_rating: Optional[int] = Field(None, description="Bedside manner rating")
    expertise_rating: Optional[int] = Field(None, description="Expertise rating")
    communication_rating: Optional[int] = Field(None, description="Communication rating")
    is_verified: bool = Field(..., description="Is review verified")
    is_anonymous: bool = Field(..., description="Is anonymous review")

    class Config:
        from_attributes = True


class ClinicReviewListResponseV1(BaseSchema):
    """V1 schema for paginated clinic review list responses."""
    
    reviews: List[ClinicReviewResponseV1] = Field(..., description="List of reviews")
    total: int = Field(..., description="Total number of reviews")
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


class VeterinarianReviewListResponseV1(BaseSchema):
    """V1 schema for paginated veterinarian review list responses."""
    
    reviews: List[VeterinarianReviewResponseV1] = Field(..., description="List of reviews")
    total: int = Field(..., description="Total number of reviews")
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


# Specialty Schema

class VeterinarianSpecialtyResponseV1(BaseSchema):
    """V1 schema for veterinarian specialty responses."""
    
    specialty: VeterinarianSpecialty = Field(..., description="Specialty type")
    certification_date: Optional[date] = Field(None, description="Certification date")
    certification_body: Optional[str] = Field(None, description="Certifying body")


# Response model factories for V1
ClinicGetResponseV1 = create_response_model(ClinicResponseV1, "v1")
ClinicListResponseModelV1 = create_response_model(ClinicListResponseV1, "v1")

VeterinarianGetResponseV1 = create_response_model(VeterinarianResponseV1, "v1")
VeterinarianListResponseModelV1 = create_response_model(VeterinarianListResponseV1, "v1")

VeterinarianAvailabilityGetResponseV1 = create_response_model(List[VeterinarianAvailabilityResponseV1], "v1")
VeterinarianAvailabilityUpdateResponseV1 = create_response_model(List[VeterinarianAvailabilityResponseV1], "v1")

ClinicReviewCreateResponseV1 = create_response_model(ClinicReviewResponseV1, "v1")
VeterinarianReviewCreateResponseV1 = create_response_model(VeterinarianReviewResponseV1, "v1")

ClinicReviewListResponseModelV1 = create_response_model(ClinicReviewListResponseV1, "v1")
VeterinarianReviewListResponseModelV1 = create_response_model(VeterinarianReviewListResponseV1, "v1")

VeterinarianSpecialtyListResponseV1 = create_response_model(List[VeterinarianSpecialtyResponseV1], "v1")