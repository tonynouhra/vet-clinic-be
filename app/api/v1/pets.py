"""
V1 Pet API endpoints using version-agnostic controllers.

Provides basic pet management functionality:
- CRUD operations for pets
- Basic pet information retrieval
- Pet search and filtering
- Microchip lookup
- Pet deceased marking
"""

from typing import List, Optional
from datetime import date
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.app_helpers.auth_helpers import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.pet import PetGender, PetSize
from app.pets.controller import PetController
from app.api.schemas.v1.pets import (
    PetCreateV1,
    PetUpdateV1,
    PetResponseV1,
    PetListResponseV1,
    DeceasedPetRequestV1,
    PetCreateResponseV1,
    PetUpdateResponseV1,
    PetGetResponseV1,
    PetListResponseModelV1,
    PetDeleteResponseV1,
    PetDeceasedResponseV1
)

router = APIRouter()


@router.get("/", response_model=PetListResponseModelV1)
async def list_pets(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    owner_id: Optional[uuid.UUID] = Query(None, description="Filter by owner ID"),
    species: Optional[str] = Query(None, description="Filter by species"),
    breed: Optional[str] = Query(None, description="Filter by breed"),
    gender: Optional[PetGender] = Query(None, description="Filter by gender"),
    size: Optional[PetSize] = Query(None, description="Filter by size"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search pets by name or breed"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List pets with pagination and filtering.
    V1 endpoint provides basic pet listing functionality.
    """
    try:
        controller = PetController(db)
        
        # V1 specific parameters (basic functionality)
        pets, total = await controller.list_pets(
            page=page,
            per_page=per_page,
            owner_id=owner_id,
            species=species,
            breed=breed,
            gender=gender,
            size=size,
            is_active=is_active,
            search=search,
            # V1 defaults - no enhanced features
            include_health_records=False,
            include_owner=False,
            sort_by=None
        )
        
        # Calculate pagination metadata
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        
        # Create V1 response
        pet_list_response = PetListResponseV1(
            pets=[PetResponseV1.model_validate(pet) for pet in pets],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
        return PetListResponseModelV1(
            success=True,
            data=pet_list_response,
            version="v1"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list pets: {str(e)}"
        )


@router.post("/", response_model=PetCreateResponseV1, status_code=status.HTTP_201_CREATED)
async def create_pet(
    pet_data: PetCreateV1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.CLINIC_ADMIN, UserRole.VETERINARIAN, UserRole.VET_TECH]))
):
    """
    Create a new pet.
    V1 endpoint for basic pet creation.
    """
    try:
        controller = PetController(db)
        
        # Create pet using V1 schema
        pet = await controller.create_pet(
            pet_data=pet_data,
            created_by=current_user.id
        )
        
        return PetCreateResponseV1(
            success=True,
            data=PetResponseV1.model_validate(pet),
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create pet: {str(e)}"
        )


@router.get("/{pet_id}", response_model=PetGetResponseV1)
async def get_pet(
    pet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get pet by ID.
    V1 endpoint provides basic pet information.
    """
    try:
        controller = PetController(db)
        
        # V1 specific parameters (basic functionality)
        pet = await controller.get_pet_by_id(
            pet_id=pet_id,
            # V1 defaults - no enhanced features
            include_health_records=False,
            include_owner=False,
            include_appointments=False
        )
        
        return PetGetResponseV1(
            success=True,
            data=PetResponseV1.model_validate(pet),
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pet: {str(e)}"
        )


@router.put("/{pet_id}", response_model=PetUpdateResponseV1)
async def update_pet(
    pet_id: uuid.UUID,
    pet_data: PetUpdateV1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.CLINIC_ADMIN, UserRole.VETERINARIAN, UserRole.VET_TECH]))
):
    """
    Update pet information.
    V1 endpoint for basic pet updates.
    """
    try:
        controller = PetController(db)
        
        # Update pet using V1 schema
        pet = await controller.update_pet(
            pet_id=pet_id,
            pet_data=pet_data,
            updated_by=current_user.id
        )
        
        return PetUpdateResponseV1(
            success=True,
            data=PetResponseV1.model_validate(pet),
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update pet: {str(e)}"
        )


@router.delete("/{pet_id}", response_model=PetDeleteResponseV1)
async def delete_pet(
    pet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.CLINIC_ADMIN, UserRole.SYSTEM_ADMIN]))
):
    """
    Delete a pet.
    V1 endpoint for pet deletion (admin only).
    """
    try:
        controller = PetController(db)
        
        result = await controller.delete_pet(
            pet_id=pet_id,
            deleted_by=current_user.id
        )
        
        return PetDeleteResponseV1(
            success=True,
            data=result,
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete pet: {str(e)}"
        )


@router.get("/microchip/{microchip_id}", response_model=PetGetResponseV1)
async def get_pet_by_microchip(
    microchip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get pet by microchip ID.
    V1 endpoint for microchip lookup.
    """
    try:
        controller = PetController(db)
        
        pet = await controller.get_pet_by_microchip(microchip_id=microchip_id)
        
        return PetGetResponseV1(
            success=True,
            data=PetResponseV1.model_validate(pet),
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pet by microchip: {str(e)}"
        )


@router.get("/owner/{owner_id}", response_model=PetListResponseModelV1)
async def get_pets_by_owner(
    owner_id: uuid.UUID,
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all pets owned by a specific user.
    V1 endpoint for owner-based pet retrieval.
    """
    try:
        controller = PetController(db)
        
        # V1 specific parameters (basic functionality)
        pets = await controller.get_pets_by_owner(
            owner_id=owner_id,
            is_active=is_active,
            # V1 defaults - no enhanced features
            include_health_records=False
        )
        
        # Create V1 response
        pet_list_response = PetListResponseV1(
            pets=[PetResponseV1.model_validate(pet) for pet in pets],
            total=len(pets),
            page=1,
            per_page=len(pets),
            total_pages=1
        )
        
        return PetListResponseModelV1(
            success=True,
            data=pet_list_response,
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pets by owner: {str(e)}"
        )


@router.patch("/{pet_id}/deceased", response_model=PetDeceasedResponseV1)
async def mark_pet_deceased(
    pet_id: uuid.UUID,
    deceased_data: DeceasedPetRequestV1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.CLINIC_ADMIN, UserRole.VETERINARIAN]))
):
    """
    Mark a pet as deceased.
    V1 endpoint for marking pets as deceased.
    """
    try:
        controller = PetController(db)
        
        pet = await controller.mark_pet_deceased(
            pet_id=pet_id,
            deceased_date=deceased_data.deceased_date,
            marked_by=current_user.id
        )
        
        return PetDeceasedResponseV1(
            success=True,
            data=PetResponseV1.model_validate(pet),
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark pet as deceased: {str(e)}"
        )