"""
V1 Clinic and Veterinarian API endpoints using version-agnostic controllers.

Provides basic clinic and veterinarian management functionality:
- Clinic listing and search
- Veterinarian listing and search
- Availability management
- Review system
- Location-based search
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, require_any_role, require_role
from app.models.user import User, UserRole
from app.models.clinic import ClinicType, VeterinarianSpecialty, DayOfWeek
from app.clinics.controller import ClinicController
from app.api.schemas.v1.clinics import (
    ClinicResponseV1,
    ClinicListResponseV1,
    ClinicGetResponseV1,
    ClinicListResponseModelV1,
    VeterinarianResponseV1,
    VeterinarianListResponseV1,
    VeterinarianGetResponseV1,
    VeterinarianListResponseModelV1,
    VeterinarianAvailabilityResponseV1,
    VeterinarianAvailabilityUpdateV1,
    VeterinarianAvailabilityBulkUpdateV1,
    VeterinarianAvailabilityGetResponseV1,
    VeterinarianAvailabilityUpdateResponseV1,
    ClinicReviewCreateV1,
    VeterinarianReviewCreateV1,
    ClinicReviewResponseV1,
    VeterinarianReviewResponseV1,
    ClinicReviewListResponseV1,
    VeterinarianReviewListResponseV1,
    ClinicReviewCreateResponseV1,
    VeterinarianReviewCreateResponseV1,
    ClinicReviewListResponseModelV1,
    VeterinarianReviewListResponseModelV1,
    VeterinarianSpecialtyResponseV1,
    VeterinarianSpecialtyListResponseV1
)

router = APIRouter()


# Clinic Endpoints

@router.get("/clinics", response_model=ClinicListResponseModelV1)
async def list_clinics(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    clinic_type: Optional[ClinicType] = Query(None, description="Filter by clinic type"),
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    is_emergency: Optional[bool] = Query(None, description="Filter by emergency clinic status"),
    is_24_hour: Optional[bool] = Query(None, description="Filter by 24-hour availability"),
    is_accepting_patients: Optional[bool] = Query(None, description="Filter by accepting new patients"),
    search: Optional[str] = Query(None, description="Search clinics by name, description, or address"),
    latitude: Optional[float] = Query(None, ge=-90, le=90, description="Latitude for location-based search"),
    longitude: Optional[float] = Query(None, ge=-180, le=180, description="Longitude for location-based search"),
    radius_miles: Optional[float] = Query(None, gt=0, le=500, description="Search radius in miles"),
    sort_by: Optional[str] = Query(None, description="Sort by field (name, city, distance)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List clinics with pagination and filtering.
    V1 endpoint provides basic clinic listing functionality.
    """
    try:
        controller = ClinicController(db)
        
        # V1 specific parameters (basic functionality)
        clinics, total = await controller.list_clinics(
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
            # V1 defaults - no enhanced features
            include_veterinarians=False,
            include_reviews=False,
            sort_by=sort_by
        )
        
        # Calculate pagination metadata
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        
        # Create V1 response
        clinic_list_response = ClinicListResponseV1(
            clinics=[ClinicResponseV1.model_validate(clinic) for clinic in clinics],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
        return ClinicListResponseModelV1(
            success=True,
            data=clinic_list_response,
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list clinics: {str(e)}"
        )


@router.get("/clinics/{clinic_id}", response_model=ClinicGetResponseV1)
async def get_clinic(
    clinic_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get clinic by ID.
    V1 endpoint provides basic clinic information.
    """
    try:
        controller = ClinicController(db)
        
        # V1 specific parameters (basic functionality)
        clinic = await controller.get_clinic_by_id(
            clinic_id=clinic_id,
            # V1 defaults - no enhanced features
            include_veterinarians=False,
            include_reviews=False,
            include_operating_hours=False
        )
        
        return ClinicGetResponseV1(
            success=True,
            data=ClinicResponseV1.model_validate(clinic),
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get clinic: {str(e)}"
        )


# Veterinarian Endpoints

@router.get("/veterinarians", response_model=VeterinarianListResponseModelV1)
async def list_veterinarians(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    clinic_id: Optional[uuid.UUID] = Query(None, description="Filter by clinic ID"),
    specialty: Optional[VeterinarianSpecialty] = Query(None, description="Filter by specialty"),
    is_available_for_emergency: Optional[bool] = Query(None, description="Filter by emergency availability"),
    is_accepting_patients: Optional[bool] = Query(None, description="Filter by accepting new patients"),
    search: Optional[str] = Query(None, description="Search veterinarians by name or bio"),
    city: Optional[str] = Query(None, description="Filter by clinic city"),
    state: Optional[str] = Query(None, description="Filter by clinic state"),
    min_experience_years: Optional[int] = Query(None, ge=0, description="Minimum years of experience"),
    sort_by: Optional[str] = Query(None, description="Sort by field (name, experience, rating)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List veterinarians with pagination and filtering.
    V1 endpoint provides basic veterinarian listing functionality.
    """
    try:
        controller = ClinicController(db)
        
        # V1 specific parameters (basic functionality)
        veterinarians, total = await controller.list_veterinarians(
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
            # V1 defaults - no enhanced features
            include_clinic=False,
            include_reviews=False,
            include_availability=False,
            sort_by=sort_by
        )
        
        # Calculate pagination metadata
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        
        # Create V1 response
        veterinarian_list_response = VeterinarianListResponseV1(
            veterinarians=[VeterinarianResponseV1.model_validate(vet) for vet in veterinarians],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
        return VeterinarianListResponseModelV1(
            success=True,
            data=veterinarian_list_response,
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list veterinarians: {str(e)}"
        )


@router.get("/veterinarians/{veterinarian_id}", response_model=VeterinarianGetResponseV1)
async def get_veterinarian(
    veterinarian_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get veterinarian by ID.
    V1 endpoint provides basic veterinarian information.
    """
    try:
        controller = ClinicController(db)
        
        # V1 specific parameters (basic functionality)
        veterinarian = await controller.get_veterinarian_by_id(
            veterinarian_id=veterinarian_id,
            # V1 defaults - no enhanced features
            include_clinic=False,
            include_reviews=False,
            include_availability=False,
            include_specialties=False
        )
        
        return VeterinarianGetResponseV1(
            success=True,
            data=VeterinarianResponseV1.model_validate(veterinarian),
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get veterinarian: {str(e)}"
        )


@router.get("/veterinarians/search/location", response_model=VeterinarianListResponseModelV1)
async def search_veterinarians_by_location(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude coordinate"),
    radius_miles: float = Query(25, gt=0, le=500, description="Search radius in miles"),
    specialty: Optional[VeterinarianSpecialty] = Query(None, description="Filter by specialty"),
    is_available_for_emergency: Optional[bool] = Query(None, description="Filter by emergency availability"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search veterinarians by location with distance calculation.
    V1 endpoint for location-based veterinarian search.
    """
    try:
        controller = ClinicController(db)
        
        veterinarians, total = await controller.search_veterinarians_by_location(
            latitude=latitude,
            longitude=longitude,
            radius_miles=radius_miles,
            specialty=specialty,
            is_available_for_emergency=is_available_for_emergency,
            page=page,
            per_page=per_page
        )
        
        # Calculate pagination metadata
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        
        # Create V1 response
        veterinarian_list_response = VeterinarianListResponseV1(
            veterinarians=[VeterinarianResponseV1.model_validate(vet) for vet in veterinarians],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
        return VeterinarianListResponseModelV1(
            success=True,
            data=veterinarian_list_response,
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search veterinarians by location: {str(e)}"
        )


# Availability Endpoints

@router.get("/veterinarians/{veterinarian_id}/availability", response_model=VeterinarianAvailabilityGetResponseV1)
async def get_veterinarian_availability(
    veterinarian_id: uuid.UUID,
    day_of_week: Optional[DayOfWeek] = Query(None, description="Filter by day of week"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get veterinarian availability schedule.
    V1 endpoint for availability retrieval.
    """
    try:
        controller = ClinicController(db)
        
        availability = await controller.get_veterinarian_availability(
            veterinarian_id=veterinarian_id,
            day_of_week=day_of_week
        )
        
        return VeterinarianAvailabilityGetResponseV1(
            success=True,
            data=[VeterinarianAvailabilityResponseV1.model_validate(avail) for avail in availability],
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get veterinarian availability: {str(e)}"
        )


@router.put("/veterinarians/{veterinarian_id}/availability", response_model=VeterinarianAvailabilityUpdateResponseV1)
async def update_veterinarian_availability(
    veterinarian_id: uuid.UUID,
    availability_data: VeterinarianAvailabilityBulkUpdateV1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VETERINARIAN, UserRole.CLINIC_MANAGER, UserRole.ADMIN]))
):
    """
    Update veterinarian availability schedule.
    V1 endpoint for availability management.
    """
    try:
        controller = ClinicController(db)
        
        # Check if current user is the veterinarian or has management permissions
        if current_user.role == UserRole.VETERINARIAN:
            vet_profile = await controller.get_veterinarian_by_user_id(current_user.id)
            if not vet_profile or vet_profile.id != veterinarian_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only update your own availability"
                )
        
        availability = await controller.update_veterinarian_availability(
            veterinarian_id=veterinarian_id,
            availability_data=availability_data,
            updated_by=current_user.id
        )
        
        return VeterinarianAvailabilityUpdateResponseV1(
            success=True,
            data=[VeterinarianAvailabilityResponseV1.model_validate(avail) for avail in availability],
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update veterinarian availability: {str(e)}"
        )


# Review Endpoints

@router.post("/clinics/{clinic_id}/reviews", response_model=ClinicReviewCreateResponseV1, status_code=status.HTTP_201_CREATED)
async def create_clinic_review(
    clinic_id: uuid.UUID,
    review_data: ClinicReviewCreateV1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a clinic review.
    V1 endpoint for clinic review creation.
    """
    try:
        controller = ClinicController(db)
        
        review = await controller.create_clinic_review(
            clinic_id=clinic_id,
            review_data=review_data,
            reviewer_id=current_user.id
        )
        
        return ClinicReviewCreateResponseV1(
            success=True,
            data=ClinicReviewResponseV1.model_validate(review),
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create clinic review: {str(e)}"
        )


@router.post("/veterinarians/{veterinarian_id}/reviews", response_model=VeterinarianReviewCreateResponseV1, status_code=status.HTTP_201_CREATED)
async def create_veterinarian_review(
    veterinarian_id: uuid.UUID,
    review_data: VeterinarianReviewCreateV1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a veterinarian review.
    V1 endpoint for veterinarian review creation.
    """
    try:
        controller = ClinicController(db)
        
        review = await controller.create_veterinarian_review(
            veterinarian_id=veterinarian_id,
            review_data=review_data,
            reviewer_id=current_user.id
        )
        
        return VeterinarianReviewCreateResponseV1(
            success=True,
            data=VeterinarianReviewResponseV1.model_validate(review),
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create veterinarian review: {str(e)}"
        )


@router.get("/clinics/{clinic_id}/reviews", response_model=ClinicReviewListResponseModelV1)
async def get_clinic_reviews(
    clinic_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get reviews for a clinic.
    V1 endpoint for clinic review retrieval.
    """
    try:
        controller = ClinicController(db)
        
        reviews, total = await controller.get_clinic_reviews(
            clinic_id=clinic_id,
            page=page,
            per_page=per_page
        )
        
        # Calculate pagination metadata
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        
        # Create V1 response
        review_list_response = ClinicReviewListResponseV1(
            reviews=[ClinicReviewResponseV1.model_validate(review) for review in reviews],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
        return ClinicReviewListResponseModelV1(
            success=True,
            data=review_list_response,
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get clinic reviews: {str(e)}"
        )


@router.get("/veterinarians/{veterinarian_id}/reviews", response_model=VeterinarianReviewListResponseModelV1)
async def get_veterinarian_reviews(
    veterinarian_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get reviews for a veterinarian.
    V1 endpoint for veterinarian review retrieval.
    """
    try:
        controller = ClinicController(db)
        
        reviews, total = await controller.get_veterinarian_reviews(
            veterinarian_id=veterinarian_id,
            page=page,
            per_page=per_page
        )
        
        # Calculate pagination metadata
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        
        # Create V1 response
        review_list_response = VeterinarianReviewListResponseV1(
            reviews=[VeterinarianReviewResponseV1.model_validate(review) for review in reviews],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
        return VeterinarianReviewListResponseModelV1(
            success=True,
            data=review_list_response,
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get veterinarian reviews: {str(e)}"
        )


# Specialty Endpoints

@router.get("/veterinarians/{veterinarian_id}/specialties", response_model=VeterinarianSpecialtyListResponseV1)
async def get_veterinarian_specialties(
    veterinarian_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get specialties for a veterinarian.
    V1 endpoint for specialty retrieval.
    """
    try:
        controller = ClinicController(db)
        
        specialties = await controller.get_veterinarian_specialties(
            veterinarian_id=veterinarian_id
        )
        
        return VeterinarianSpecialtyListResponseV1(
            success=True,
            data=[VeterinarianSpecialtyResponseV1.model_validate(spec) for spec in specialties],
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get veterinarian specialties: {str(e)}"
        )