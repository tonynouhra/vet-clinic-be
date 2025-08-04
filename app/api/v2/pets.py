"""
V2 Pet API endpoints using version-agnostic controllers.

Provides enhanced pet management functionality:
- All V1 features plus:
- Enhanced pet information with health records
- Owner information inclusion
- Pet statistics
- Health record management
- Advanced filtering and sorting
- Batch operations
- Enhanced deceased pet handling
"""

from typing import List, Optional
from datetime import date
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.pet import PetGender, PetSize, HealthRecordType
from app.pets.controller import PetController
from app.api.schemas.v2.pets import (
    PetCreateV2,
    PetUpdateV2,
    PetResponseV2,
    PetListResponseV2,
    PetStatisticsV2,
    HealthRecordCreateV2,
    HealthRecordResponseV2,
    DeceasedPetRequestV2,
    BatchPetOperationV2,
    PetCreateResponseV2,
    PetUpdateResponseV2,
    PetGetResponseV2,
    PetListResponseModelV2,
    PetDeleteResponseV2,
    PetDeceasedResponseV2,
    PetStatisticsResponseV2,
    PetHealthRecordResponseV2,
    PetBatchOperationResponseV2
)

router = APIRouter()


@router.get("/", response_model=PetListResponseModelV2)
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
    # V2 Enhanced parameters
    include_health_records: bool = Query(False, description="Include health records"),
    include_owner: bool = Query(False, description="Include owner information"),
    sort_by: Optional[str] = Query(None, description="Sort by field (name, created_at, age)"),
    include_statistics: bool = Query(False, description="Include list statistics"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List pets with enhanced filtering and information.
    V2 endpoint provides advanced pet listing with health records and owner info.
    """
    try:
        controller = PetController(db)
        
        # V2 enhanced parameters
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
            # V2 specific features
            include_health_records=include_health_records,
            include_owner=include_owner,
            sort_by=sort_by
        )
        
        # Calculate pagination metadata
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        
        # Prepare statistics if requested
        statistics = None
        if include_statistics:
            statistics = {
                "total_active": sum(1 for pet in pets if pet.is_active),
                "total_deceased": sum(1 for pet in pets if pet.is_deceased),
                "species_breakdown": {},
                "average_age_years": 0  # Would calculate from actual data
            }
            
            # Species breakdown
            for pet in pets:
                species = pet.species
                statistics["species_breakdown"][species] = statistics["species_breakdown"].get(species, 0) + 1
        
        # Prepare filters applied summary
        filters_applied = {
            "owner_id": owner_id,
            "species": species,
            "breed": breed,
            "gender": gender,
            "size": size,
            "is_active": is_active,
            "search": search,
            "sort_by": sort_by,
            "include_health_records": include_health_records,
            "include_owner": include_owner
        }
        # Remove None values
        filters_applied = {k: v for k, v in filters_applied.items() if v is not None}
        
        # Create V2 response
        pet_list_response = PetListResponseV2(
            pets=[PetResponseV2.model_validate(pet) for pet in pets],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            statistics=statistics,
            filters_applied=filters_applied
        )
        
        return PetListResponseModelV2(
            success=True,
            data=pet_list_response,
            version="v2"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list pets: {str(e)}"
        )


@router.post("/", response_model=PetCreateResponseV2, status_code=status.HTTP_201_CREATED)
async def create_pet(
    pet_data: PetCreateV2,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.CLINIC_MANAGER, UserRole.VETERINARIAN]))
):
    """
    Create a new pet with enhanced information.
    V2 endpoint supports additional photos, emergency contacts, and initial health records.
    """
    try:
        controller = PetController(db)
        
        # Create pet using V2 schema
        pet = await controller.create_pet(
            pet_data=pet_data,
            created_by=current_user.id
        )
        
        return PetCreateResponseV2(
            success=True,
            data=PetResponseV2.model_validate(pet),
            version="v2"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create pet: {str(e)}"
        )


@router.get("/{pet_id}", response_model=PetGetResponseV2)
async def get_pet(
    pet_id: uuid.UUID,
    include_health_records: bool = Query(False, description="Include health records"),
    include_owner: bool = Query(False, description="Include owner information"),
    include_appointments: bool = Query(False, description="Include appointment information"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get pet by ID with enhanced information.
    V2 endpoint provides comprehensive pet information including health records and appointments.
    """
    try:
        controller = PetController(db)
        
        # V2 enhanced parameters
        pet = await controller.get_pet_by_id(
            pet_id=pet_id,
            include_health_records=include_health_records,
            include_owner=include_owner,
            include_appointments=include_appointments
        )
        
        return PetGetResponseV2(
            success=True,
            data=PetResponseV2.model_validate(pet),
            version="v2"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pet: {str(e)}"
        )


@router.put("/{pet_id}", response_model=PetUpdateResponseV2)
async def update_pet(
    pet_id: uuid.UUID,
    pet_data: PetUpdateV2,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.CLINIC_MANAGER, UserRole.VETERINARIAN]))
):
    """
    Update pet information with enhanced fields.
    V2 endpoint supports updating additional photos, emergency contacts, and insurance info.
    """
    try:
        controller = PetController(db)
        
        # Update pet using V2 schema
        pet = await controller.update_pet(
            pet_id=pet_id,
            pet_data=pet_data,
            updated_by=current_user.id
        )
        
        return PetUpdateResponseV2(
            success=True,
            data=PetResponseV2.model_validate(pet),
            version="v2"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update pet: {str(e)}"
        )


@router.delete("/{pet_id}", response_model=PetDeleteResponseV2)
async def delete_pet(
    pet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.CLINIC_MANAGER, UserRole.ADMIN]))
):
    """
    Delete a pet.
    V2 endpoint for pet deletion (admin only).
    """
    try:
        controller = PetController(db)
        
        result = await controller.delete_pet(
            pet_id=pet_id,
            deleted_by=current_user.id
        )
        
        return PetDeleteResponseV2(
            success=True,
            data=result,
            version="v2"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete pet: {str(e)}"
        )


@router.get("/microchip/{microchip_id}", response_model=PetGetResponseV2)
async def get_pet_by_microchip(
    microchip_id: str,
    include_health_records: bool = Query(False, description="Include health records"),
    include_owner: bool = Query(False, description="Include owner information"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get pet by microchip ID with enhanced information.
    V2 endpoint for microchip lookup with optional related data.
    """
    try:
        controller = PetController(db)
        
        pet = await controller.get_pet_by_microchip(microchip_id=microchip_id)
        
        # If enhanced information requested, fetch it
        if include_health_records or include_owner:
            pet = await controller.get_pet_by_id(
                pet_id=pet.id,
                include_health_records=include_health_records,
                include_owner=include_owner
            )
        
        return PetGetResponseV2(
            success=True,
            data=PetResponseV2.model_validate(pet),
            version="v2"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pet by microchip: {str(e)}"
        )


@router.get("/owner/{owner_id}", response_model=PetListResponseModelV2)
async def get_pets_by_owner(
    owner_id: uuid.UUID,
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    include_health_records: bool = Query(False, description="Include health records"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all pets owned by a specific user with enhanced information.
    V2 endpoint for owner-based pet retrieval with health records.
    """
    try:
        controller = PetController(db)
        
        # V2 enhanced parameters
        pets = await controller.get_pets_by_owner(
            owner_id=owner_id,
            is_active=is_active,
            include_health_records=include_health_records
        )
        
        # Create V2 response
        pet_list_response = PetListResponseV2(
            pets=[PetResponseV2.model_validate(pet) for pet in pets],
            total=len(pets),
            page=1,
            per_page=len(pets),
            total_pages=1,
            statistics={
                "total_active": sum(1 for pet in pets if pet.is_active),
                "total_deceased": sum(1 for pet in pets if pet.is_deceased)
            }
        )
        
        return PetListResponseModelV2(
            success=True,
            data=pet_list_response,
            version="v2"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pets by owner: {str(e)}"
        )


@router.patch("/{pet_id}/deceased", response_model=PetDeceasedResponseV2)
async def mark_pet_deceased(
    pet_id: uuid.UUID,
    deceased_data: DeceasedPetRequestV2,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.CLINIC_MANAGER, UserRole.VETERINARIAN]))
):
    """
    Mark a pet as deceased with enhanced information.
    V2 endpoint supports cause of death, notes, and owner notification.
    """
    try:
        controller = PetController(db)
        
        pet = await controller.mark_pet_deceased(
            pet_id=pet_id,
            deceased_date=deceased_data.deceased_date,
            marked_by=current_user.id,
            # V2 enhancements would be handled by additional service methods
            cause_of_death=getattr(deceased_data, 'cause_of_death', None),
            notes=getattr(deceased_data, 'notes', None),
            notify_owner=getattr(deceased_data, 'notify_owner', True)
        )
        
        return PetDeceasedResponseV2(
            success=True,
            data=PetResponseV2.model_validate(pet),
            version="v2"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark pet as deceased: {str(e)}"
        )


@router.get("/{pet_id}/stats", response_model=PetStatisticsResponseV2)
async def get_pet_statistics(
    pet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get pet statistics and health summary.
    V2 specific endpoint for comprehensive pet statistics.
    """
    try:
        controller = PetController(db)
        
        # Get pet with all related data
        pet = await controller.get_pet_by_id(
            pet_id=pet_id,
            include_health_records=True,
            include_appointments=True
        )
        
        # Calculate statistics
        from datetime import datetime
        current_date = datetime.now().date()
        registration_date = pet.created_at.date()
        days_since_registration = (current_date - registration_date).days
        
        # Count health records by type
        total_health_records = len(pet.health_records) if pet.health_records else 0
        
        # Find last checkup
        last_checkup_date = None
        if pet.health_records:
            checkups = [hr for hr in pet.health_records if hr.record_type == HealthRecordType.CHECKUP]
            if checkups:
                last_checkup_date = max(hr.record_date for hr in checkups)
        
        # Find next vaccination due
        next_due_vaccination = None
        if pet.health_records:
            vaccinations = [hr for hr in pet.health_records 
                          if hr.record_type == HealthRecordType.VACCINATION and hr.next_due_date]
            if vaccinations:
                future_dates = [hr.next_due_date for hr in vaccinations if hr.next_due_date >= current_date]
                if future_dates:
                    next_due_vaccination = min(future_dates)
        
        # Count appointments
        total_appointments = len(pet.appointments) if pet.appointments else 0
        
        # Count active medications (simplified)
        active_medications_count = 1 if pet.current_medications else 0
        
        statistics = PetStatisticsV2(
            total_health_records=total_health_records,
            total_appointments=total_appointments,
            last_checkup_date=last_checkup_date,
            next_due_vaccination=next_due_vaccination,
            days_since_registration=days_since_registration,
            weight_history_count=0,  # Would need separate weight tracking
            active_medications_count=active_medications_count
        )
        
        return PetStatisticsResponseV2(
            success=True,
            data=statistics,
            version="v2"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pet statistics: {str(e)}"
        )


@router.post("/{pet_id}/health-records", response_model=PetHealthRecordResponseV2, status_code=status.HTTP_201_CREATED)
async def add_health_record(
    pet_id: uuid.UUID,
    record_data: HealthRecordCreateV2,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.CLINIC_MANAGER, UserRole.VETERINARIAN]))
):
    """
    Add a health record to a pet.
    V2 specific endpoint for comprehensive health record management.
    """
    try:
        controller = PetController(db)
        
        health_record = await controller.add_health_record(
            pet_id=pet_id,
            record_data=record_data,
            created_by=current_user.id
        )
        
        return PetHealthRecordResponseV2(
            success=True,
            data=HealthRecordResponseV2.model_validate(health_record),
            version="v2"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add health record: {str(e)}"
        )


@router.get("/{pet_id}/health-records", response_model=List[HealthRecordResponseV2])
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
    V2 specific endpoint for health record retrieval.
    """
    try:
        controller = PetController(db)
        
        health_records = await controller.get_pet_health_records(
            pet_id=pet_id,
            record_type=record_type,
            start_date=start_date,
            end_date=end_date
        )
        
        return [HealthRecordResponseV2.model_validate(record) for record in health_records]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get health records: {str(e)}"
        )


@router.post("/batch", response_model=PetBatchOperationResponseV2)
async def batch_pet_operation(
    batch_data: BatchPetOperationV2,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.CLINIC_MANAGER, UserRole.ADMIN]))
):
    """
    Perform batch operations on multiple pets.
    V2 specific endpoint for bulk pet management.
    """
    try:
        controller = PetController(db)
        
        successful = 0
        failed = 0
        errors = []
        
        for i, pet_id in enumerate(batch_data.pet_ids):
            try:
                if batch_data.operation == "activate":
                    await controller.update_pet(
                        pet_id=pet_id,
                        pet_data={"is_active": True},
                        updated_by=current_user.id
                    )
                elif batch_data.operation == "deactivate":
                    await controller.update_pet(
                        pet_id=pet_id,
                        pet_data={"is_active": False},
                        updated_by=current_user.id
                    )
                elif batch_data.operation == "bulk_update":
                    if batch_data.operation_data:
                        await controller.update_pet(
                            pet_id=pet_id,
                            pet_data=batch_data.operation_data,
                            updated_by=current_user.id
                        )
                
                successful += 1
                
            except Exception as e:
                failed += 1
                errors.append({
                    "index": i,
                    "pet_id": str(pet_id),
                    "error": str(e)
                })
        
        result = {
            "operation": batch_data.operation,
            "total_requested": len(batch_data.pet_ids),
            "successful": successful,
            "failed": failed,
            "errors": errors,
            "message": f"Batch {batch_data.operation} completed: {successful} successful, {failed} failed"
        }
        
        return PetBatchOperationResponseV2(
            success=failed == 0,  # Only successful if no failures
            data=result,
            version="v2"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform batch operation: {str(e)}"
        )