"""
V1 Pet schemas for basic pet management operations.

V1 focuses on essential pet information and basic CRUD operations.
"""

from typing import Optional, List
from datetime import date
from pydantic import Field, validator
import uuid

from app.api.schemas.base import BaseSchema, TimestampMixin, IDMixin, create_response_model
from app.api.schemas.validators import SchemaValidationMixin
from app.models.pet import PetGender, PetSize


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


# Response model factories for V1
PetCreateResponseV1 = create_response_model(PetResponseV1, "v1")
PetUpdateResponseV1 = create_response_model(PetResponseV1, "v1")
PetGetResponseV1 = create_response_model(PetResponseV1, "v1")
PetListResponseModelV1 = create_response_model(PetListResponseV1, "v1")
PetDeleteResponseV1 = create_response_model(dict, "v1")  # Simple success message
PetDeceasedResponseV1 = create_response_model(PetResponseV1, "v1")