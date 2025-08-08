"""
Version-agnostic Clinic Controller

This controller handles HTTP request processing and business logic orchestration
for clinic and veterinarian related operations across all API versions. It accepts 
Union types for different API version schemas and returns raw data that can be 
formatted by any version.
"""

from typing import List, Optional, Union, Dict, Any, Tuple
from datetime import date, time
import uuid
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.exceptions import VetClinicException, NotFoundError, ValidationError
from app.models.clinic import (
    Clinic, Veterinarian, VeterinarianAvailability, ClinicOperatingHours,
    ClinicReview, VeterinarianReview, ClinicType, VeterinarianSpecialty,
    DayOfWeek
)
from .services import ClinicService


class ClinicController:
    """Version-agnostic controller for clinic and veterinarian related operations."""

    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.service = ClinicService(db)
        self.db = db

    # Clinic Management Methods

    async def list_clinics(
        self,
        page: int = 1,
        per_page: int = 10,
        clinic_type: Optional[Union[ClinicType, str]] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        is_emergency: Optional[bool] = None,
        is_24_hour: Optional[bool] = None,
        is_accepting_patients: Optional[bool] = None,
        search: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_miles: Optional[float] = None,
        include_veterinarians: bool = False,
        include_reviews: bool = False,
        sort_by: Optional[str] = None,
        **kwargs
    ) -> Tuple[List[Clinic], int]:
        """
        List clinics with pagination and filtering.
        Handles business rules and validation before delegating to service.
        """
        try:
            # Validate pagination parameters
            if page < 1:
                raise ValidationError("Page must be greater than 0")
            if per_page < 1 or per_page > 100:
                raise ValidationError("Items per page must be between 1 and 100")
            
            # Validate location parameters
            if latitude is not None or longitude is not None or radius_miles is not None:
                if latitude is None or longitude is None:
                    raise ValidationError("Both latitude and longitude are required for location search")
                if radius_miles is None:
                    radius_miles = 25  # Default radius
                if radius_miles <= 0 or radius_miles > 500:
                    raise ValidationError("Radius must be between 0 and 500 miles")
                if latitude < -90 or latitude > 90:
                    raise ValidationError("Latitude must be between -90 and 90")
                if longitude < -180 or longitude > 180:
                    raise ValidationError("Longitude must be between -180 and 180")
            
            # Delegate to service
            clinics, total = await self.service.list_clinics(
                page=page,
                per_page=per_page,
                clinic_type=clinic_type,
                city=city,
                state=state,
                is_emergency=is_emergency,
                is_24_hour=is_24_hour,
                is_accepting_patients=is_accepting_patients,
                search=search,
                latitude=latitude,
                longitude=longitude,
                radius_miles=radius_miles,
                include_veterinarians=include_veterinarians,
                include_reviews=include_reviews,
                sort_by=sort_by,
                **kwargs
            )
            
            return clinics, total
            
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def get_clinic_by_id(
        self,
        clinic_id: uuid.UUID,
        include_veterinarians: bool = False,
        include_reviews: bool = False,
        include_operating_hours: bool = False,
        **kwargs
    ) -> Clinic:
        """
        Get clinic by ID with optional related data.
        """
        try:
            clinic = await self.service.get_clinic_by_id(
                clinic_id=clinic_id,
                include_veterinarians=include_veterinarians,
                include_reviews=include_reviews,
                include_operating_hours=include_operating_hours,
                **kwargs
            )
            return clinic
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    # Veterinarian Management Methods

    async def list_veterinarians(
        self,
        page: int = 1,
        per_page: int = 10,
        clinic_id: Optional[uuid.UUID] = None,
        specialty: Optional[Union[VeterinarianSpecialty, str]] = None,
        is_available_for_emergency: Optional[bool] = None,
        is_accepting_patients: Optional[bool] = None,
        search: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        min_experience_years: Optional[int] = None,
        include_clinic: bool = False,
        include_reviews: bool = False,
        include_availability: bool = False,
        sort_by: Optional[str] = None,
        **kwargs
    ) -> Tuple[List[Veterinarian], int]:
        """
        List veterinarians with pagination and filtering.
        Handles business rules and validation before delegating to service.
        """
        try:
            # Validate pagination parameters
            if page < 1:
                raise ValidationError("Page must be greater than 0")
            if per_page < 1 or per_page > 100:
                raise ValidationError("Items per page must be between 1 and 100")
            
            # Validate experience years
            if min_experience_years is not None and min_experience_years < 0:
                raise ValidationError("Minimum experience years cannot be negative")
            
            # Delegate to service
            veterinarians, total = await self.service.list_veterinarians(
                page=page,
                per_page=per_page,
                clinic_id=clinic_id,
                specialty=specialty,
                is_available_for_emergency=is_available_for_emergency,
                is_accepting_patients=is_accepting_patients,
                search=search,
                city=city,
                state=state,
                min_experience_years=min_experience_years,
                include_clinic=include_clinic,
                include_reviews=include_reviews,
                include_availability=include_availability,
                sort_by=sort_by,
                **kwargs
            )
            
            return veterinarians, total
            
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def get_veterinarian_by_id(
        self,
        veterinarian_id: uuid.UUID,
        include_clinic: bool = False,
        include_reviews: bool = False,
        include_availability: bool = False,
        include_specialties: bool = False,
        **kwargs
    ) -> Veterinarian:
        """
        Get veterinarian by ID with optional related data.
        """
        try:
            veterinarian = await self.service.get_veterinarian_by_id(
                veterinarian_id=veterinarian_id,
                include_clinic=include_clinic,
                include_reviews=include_reviews,
                include_availability=include_availability,
                include_specialties=include_specialties,
                **kwargs
            )
            return veterinarian
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def get_veterinarian_by_user_id(
        self,
        user_id: uuid.UUID,
        **kwargs
    ) -> Optional[Veterinarian]:
        """
        Get veterinarian by user ID.
        """
        try:
            veterinarian = await self.service.get_veterinarian_by_user_id(
                user_id=user_id,
                **kwargs
            )
            return veterinarian
            
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    # Availability Management Methods

    async def get_veterinarian_availability(
        self,
        veterinarian_id: uuid.UUID,
        day_of_week: Optional[Union[DayOfWeek, str]] = None,
        **kwargs
    ) -> List[VeterinarianAvailability]:
        """
        Get veterinarian availability schedule.
        """
        try:
            availability = await self.service.get_veterinarian_availability(
                veterinarian_id=veterinarian_id,
                day_of_week=day_of_week,
                **kwargs
            )
            return availability
            
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def update_veterinarian_availability(
        self,
        veterinarian_id: uuid.UUID,
        availability_data: Union[BaseModel, List[Dict[str, Any]]],
        updated_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> List[VeterinarianAvailability]:
        """
        Update veterinarian availability schedule.
        """
        try:
            # Extract data from schema or dict
            if isinstance(availability_data, BaseModel):
                data = availability_data.model_dump(exclude_unset=True)
                if "availability" in data:
                    data = data["availability"]
            else:
                data = availability_data
            
            # Business rule validation
            await self._validate_availability_update(veterinarian_id, data, updated_by)
            
            # Update availability
            availability = await self.service.update_veterinarian_availability(
                veterinarian_id=veterinarian_id,
                availability_data=data,
                **kwargs
            )
            
            return availability
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    # Review Management Methods

    async def create_clinic_review(
        self,
        clinic_id: uuid.UUID,
        review_data: Union[BaseModel, Dict[str, Any]],
        reviewer_id: uuid.UUID,
        **kwargs
    ) -> ClinicReview:
        """
        Create a clinic review.
        """
        try:
            # Extract data from schema or dict
            if isinstance(review_data, BaseModel):
                data = review_data.model_dump(exclude_unset=True)
            else:
                data = review_data
            
            # Business rule validation
            await self._validate_clinic_review_creation(clinic_id, data, reviewer_id)
            
            # Create review
            review = await self.service.create_clinic_review(
                clinic_id=clinic_id,
                reviewer_id=reviewer_id,
                rating=data.get("rating"),
                title=data.get("title"),
                review_text=data.get("review_text"),
                is_anonymous=data.get("is_anonymous", False),
                **kwargs
            )
            
            return review
            
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def create_veterinarian_review(
        self,
        veterinarian_id: uuid.UUID,
        review_data: Union[BaseModel, Dict[str, Any]],
        reviewer_id: uuid.UUID,
        **kwargs
    ) -> VeterinarianReview:
        """
        Create a veterinarian review.
        """
        try:
            # Extract data from schema or dict
            if isinstance(review_data, BaseModel):
                data = review_data.model_dump(exclude_unset=True)
            else:
                data = review_data
            
            # Business rule validation
            await self._validate_veterinarian_review_creation(veterinarian_id, data, reviewer_id)
            
            # Create review
            review = await self.service.create_veterinarian_review(
                veterinarian_id=veterinarian_id,
                reviewer_id=reviewer_id,
                rating=data.get("rating"),
                title=data.get("title"),
                review_text=data.get("review_text"),
                bedside_manner_rating=data.get("bedside_manner_rating"),
                expertise_rating=data.get("expertise_rating"),
                communication_rating=data.get("communication_rating"),
                is_anonymous=data.get("is_anonymous", False),
                **kwargs
            )
            
            return review
            
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def get_clinic_reviews(
        self,
        clinic_id: uuid.UUID,
        page: int = 1,
        per_page: int = 10,
        **kwargs
    ) -> Tuple[List[ClinicReview], int]:
        """
        Get reviews for a clinic.
        """
        try:
            # Validate pagination parameters
            if page < 1:
                raise ValidationError("Page must be greater than 0")
            if per_page < 1 or per_page > 100:
                raise ValidationError("Items per page must be between 1 and 100")
            
            reviews, total = await self.service.get_clinic_reviews(
                clinic_id=clinic_id,
                page=page,
                per_page=per_page,
                **kwargs
            )
            
            return reviews, total
            
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def get_veterinarian_reviews(
        self,
        veterinarian_id: uuid.UUID,
        page: int = 1,
        per_page: int = 10,
        **kwargs
    ) -> Tuple[List[VeterinarianReview], int]:
        """
        Get reviews for a veterinarian.
        """
        try:
            # Validate pagination parameters
            if page < 1:
                raise ValidationError("Page must be greater than 0")
            if per_page < 1 or per_page > 100:
                raise ValidationError("Items per page must be between 1 and 100")
            
            reviews, total = await self.service.get_veterinarian_reviews(
                veterinarian_id=veterinarian_id,
                page=page,
                per_page=per_page,
                **kwargs
            )
            
            return reviews, total
            
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    # Search and Filtering Methods

    async def search_veterinarians_by_location(
        self,
        latitude: float,
        longitude: float,
        radius_miles: float = 25,
        specialty: Optional[Union[VeterinarianSpecialty, str]] = None,
        is_available_for_emergency: Optional[bool] = None,
        page: int = 1,
        per_page: int = 10,
        **kwargs
    ) -> Tuple[List[Veterinarian], int]:
        """
        Search veterinarians by location with distance calculation.
        """
        try:
            # Validate location parameters
            if latitude < -90 or latitude > 90:
                raise ValidationError("Latitude must be between -90 and 90")
            if longitude < -180 or longitude > 180:
                raise ValidationError("Longitude must be between -180 and 180")
            if radius_miles <= 0 or radius_miles > 500:
                raise ValidationError("Radius must be between 0 and 500 miles")
            
            # Validate pagination parameters
            if page < 1:
                raise ValidationError("Page must be greater than 0")
            if per_page < 1 or per_page > 100:
                raise ValidationError("Items per page must be between 1 and 100")
            
            veterinarians, total = await self.service.search_veterinarians_by_location(
                latitude=latitude,
                longitude=longitude,
                radius_miles=radius_miles,
                specialty=specialty,
                is_available_for_emergency=is_available_for_emergency,
                page=page,
                per_page=per_page,
                **kwargs
            )
            
            return veterinarians, total
            
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def get_veterinarian_specialties(
        self,
        veterinarian_id: uuid.UUID,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Get specialties for a veterinarian.
        """
        try:
            specialties = await self.service.get_veterinarian_specialties(
                veterinarian_id=veterinarian_id,
                **kwargs
            )
            return specialties
            
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    # Private helper methods for business rule validation

    async def _validate_availability_update(
        self,
        veterinarian_id: uuid.UUID,
        availability_data: List[Dict[str, Any]],
        updated_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for availability updates."""
        if not availability_data:
            raise ValidationError("Availability data is required")
        
        # Validate each availability entry
        for entry in availability_data:
            day_of_week = entry.get("day_of_week")
            if not day_of_week:
                raise ValidationError("Day of week is required for each availability entry")
            
            # Validate day of week
            if isinstance(day_of_week, str):
                try:
                    DayOfWeek(day_of_week)
                except ValueError:
                    raise ValidationError(f"Invalid day of week: {day_of_week}")
            
            # Validate times if available
            is_available = entry.get("is_available", True)
            if is_available:
                start_time = entry.get("start_time")
                end_time = entry.get("end_time")
                
                if start_time and end_time:
                    if isinstance(start_time, str):
                        try:
                            start_time = time.fromisoformat(start_time)
                        except ValueError:
                            raise ValidationError(f"Invalid start time format: {start_time}")
                    
                    if isinstance(end_time, str):
                        try:
                            end_time = time.fromisoformat(end_time)
                        except ValueError:
                            raise ValidationError(f"Invalid end time format: {end_time}")
                    
                    if start_time >= end_time:
                        raise ValidationError("Start time must be before end time")
                
                # Validate break times if provided
                break_start = entry.get("break_start_time")
                break_end = entry.get("break_end_time")
                
                if break_start and break_end:
                    if isinstance(break_start, str):
                        try:
                            break_start = time.fromisoformat(break_start)
                        except ValueError:
                            raise ValidationError(f"Invalid break start time format: {break_start}")
                    
                    if isinstance(break_end, str):
                        try:
                            break_end = time.fromisoformat(break_end)
                        except ValueError:
                            raise ValidationError(f"Invalid break end time format: {break_end}")
                    
                    if break_start >= break_end:
                        raise ValidationError("Break start time must be before break end time")
                    
                    # Validate break times are within working hours
                    if start_time and end_time:
                        if break_start < start_time or break_end > end_time:
                            raise ValidationError("Break times must be within working hours")
            
            # Validate appointment duration
            duration = entry.get("default_appointment_duration", 30)
            if duration < 15 or duration > 240:
                raise ValidationError("Appointment duration must be between 15 and 240 minutes")

    async def _validate_clinic_review_creation(
        self,
        clinic_id: uuid.UUID,
        data: Dict[str, Any],
        reviewer_id: uuid.UUID
    ) -> None:
        """Validate business rules for clinic review creation."""
        # Validate required fields
        rating = data.get("rating")
        if rating is None:
            raise ValidationError("Rating is required")
        
        if rating < 1 or rating > 5:
            raise ValidationError("Rating must be between 1 and 5")
        
        # Validate title if provided
        title = data.get("title")
        if title is not None and not title.strip():
            raise ValidationError("Review title cannot be empty")
        
        # Validate review text if provided
        review_text = data.get("review_text")
        if review_text is not None and len(review_text.strip()) > 2000:
            raise ValidationError("Review text cannot exceed 2000 characters")

    async def _validate_veterinarian_review_creation(
        self,
        veterinarian_id: uuid.UUID,
        data: Dict[str, Any],
        reviewer_id: uuid.UUID
    ) -> None:
        """Validate business rules for veterinarian review creation."""
        # Validate required fields
        rating = data.get("rating")
        if rating is None:
            raise ValidationError("Rating is required")
        
        if rating < 1 or rating > 5:
            raise ValidationError("Rating must be between 1 and 5")
        
        # Validate optional ratings
        optional_ratings = ["bedside_manner_rating", "expertise_rating", "communication_rating"]
        for rating_field in optional_ratings:
            rating_value = data.get(rating_field)
            if rating_value is not None and (rating_value < 1 or rating_value > 5):
                raise ValidationError(f"{rating_field} must be between 1 and 5")
        
        # Validate title if provided
        title = data.get("title")
        if title is not None and not title.strip():
            raise ValidationError("Review title cannot be empty")
        
        # Validate review text if provided
        review_text = data.get("review_text")
        if review_text is not None and len(review_text.strip()) > 2000:
            raise ValidationError("Review text cannot exceed 2000 characters")