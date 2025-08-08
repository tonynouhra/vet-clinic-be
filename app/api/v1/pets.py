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
from sqlalchemy.orm import relationship

from app.core.database import get_db
from app.api.deps import get_current_user, require_any_role, require_role
from app.models.user import User, UserRole
from app.models.pet import PetGender, PetSize, HealthRecordType
from app.pets.controller import PetController
from app.api.schemas.v1.pets import (
    PetCreateV1,
    PetUpdateV1,
    PetResponseV1,
    PetListResponseV1,
    DeceasedPetRequestV1,
    HealthRecordCreateV1,
    HealthRecordResponseV1,
    ReminderCreateV1,
    ReminderResponseV1,
    PetCreateResponseV1,
    PetUpdateResponseV1,
    PetGetResponseV1,
    PetListResponseModelV1,
    PetDeleteResponseV1,
    PetDeceasedResponseV1,
    PetHealthRecordResponseV1,
    PetReminderResponseV1
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
    current_user: User = Depends(require_any_role([UserRole.CLINIC_MANAGER, UserRole.VETERINARIAN]))
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
    current_user: User = Depends(require_role([UserRole.CLINIC_MANAGER, UserRole.VETERINARIAN]))
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
    current_user: User = Depends(require_role([UserRole.CLINIC_MANAGER, UserRole.ADMIN]))
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
    current_user: User = Depends(require_role([UserRole.CLINIC_MANAGER, UserRole.VETERINARIAN]))
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

@router.post("/{pet_id}/health-records", response_model=PetHealthRecordResponseV1, status_code=status.HTTP_201_CREATED)
async def add_health_record(
    pet_id: uuid.UUID,
    record_data: HealthRecordCreateV1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.CLINIC_MANAGER, UserRole.VETERINARIAN]))
):
    """
    Add a health record to a pet.
    V1 endpoint for basic health record management.
    """
    try:
        controller = PetController(db)
        
        health_record = await controller.add_health_record(
            pet_id=pet_id,
            record_data=record_data,
            created_by=current_user.id
        )
        
        return PetHealthRecordResponseV1(
            success=True,
            data=HealthRecordResponseV1.model_validate(health_record),
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add health record: {str(e)}"
        )


@router.get("/{pet_id}/health-records", response_model=List[HealthRecordResponseV1])
async def get_pet_health_records(
    pet_id: uuid.UUID,
    record_type: Optional[HealthRecordType] = Query(None, description="Filter by record type"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get health records for a pet with filtering.
    V1 endpoint for health record retrieval.
    """
    try:
        controller = PetController(db)
        
        health_records = await controller.get_pet_health_records(
            pet_id=pet_id,
            record_type=record_type,
            start_date=start_date,
            end_date=end_date
        )
        
        return [HealthRecordResponseV1.model_validate(record) for record in health_records]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get health records: {str(e)}"
        )


@router.get("/{pet_id}/vaccinations", response_model=List[HealthRecordResponseV1])
async def get_pet_vaccinations(
    pet_id: uuid.UUID,
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get vaccination records for a pet.
    V1 endpoint for vaccination tracking.
    """
    try:
        controller = PetController(db)
        
        vaccinations = await controller.get_pet_health_records(
            pet_id=pet_id,
            record_type=HealthRecordType.VACCINATION,
            start_date=start_date,
            end_date=end_date
        )
        
        return [HealthRecordResponseV1.model_validate(record) for record in vaccinations]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get vaccinations: {str(e)}"
        )


@router.get("/{pet_id}/medications", response_model=List[HealthRecordResponseV1])
async def get_pet_medications(
    pet_id: uuid.UUID,
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get medication records for a pet.
    V1 endpoint for medication tracking.
    """
    try:
        controller = PetController(db)
        
        medications = await controller.get_pet_health_records(
            pet_id=pet_id,
            record_type=HealthRecordType.MEDICATION,
            start_date=start_date,
            end_date=end_date
        )
        
        return [HealthRecordResponseV1.model_validate(record) for record in medications]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get medications: {str(e)}"
        )


@router.post("/{pet_id}/reminders", response_model=PetReminderResponseV1, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    pet_id: uuid.UUID,
    reminder_data: ReminderCreateV1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.CLINIC_MANAGER, UserRole.VETERINARIAN]))
):
    """
    Create a reminder for a pet.
    V1 endpoint for reminder management.
    """
    try:
        controller = PetController(db)
        
        reminder = await controller.create_reminder(
            pet_id=pet_id,
            reminder_data=reminder_data,
            created_by=current_user.id
        )
        
        return PetReminderResponseV1(
            success=True,
            data=ReminderResponseV1.model_validate(reminder),
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create reminder: {str(e)}"
        )


@router.get("/{pet_id}/reminders", response_model=List[ReminderResponseV1])
async def get_pet_reminders(
    pet_id: uuid.UUID,
    reminder_type: Optional[str] = Query(None, description="Filter by reminder type"),
    is_completed: Optional[bool] = Query(None, description="Filter by completion status"),
    due_before: Optional[date] = Query(None, description="Filter by due date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get reminders for a pet.
    V1 endpoint for reminder retrieval.
    """
    try:
        controller = PetController(db)
        
        reminders = await controller.get_pet_reminders(
            pet_id=pet_id,
            reminder_type=reminder_type,
            is_completed=is_completed,
            due_before=due_before
        )
        
        return [ReminderResponseV1.model_validate(reminder) for reminder in reminders]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reminders: {str(e)}"
        )


@router.patch("/reminders/{reminder_id}/complete", response_model=PetReminderResponseV1)
async def complete_reminder(
    reminder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.CLINIC_MANAGER, UserRole.VETERINARIAN]))
):
    """
    Mark a reminder as completed.
    V1 endpoint for reminder completion.
    """
    try:
        controller = PetController(db)
        
        reminder = await controller.complete_reminder(
            reminder_id=reminder_id,
            completed_by=current_user.id
        )
        
        return PetReminderResponseV1(
            success=True,
            data=ReminderResponseV1.model_validate(reminder),
            version="v1"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete reminder: {str(e)}"
        )