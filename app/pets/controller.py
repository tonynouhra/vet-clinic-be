"""
Version-agnostic Pet Controller

This controller handles HTTP request processing and business logic orchestration
for pet-related operations across all API versions. It accepts Union types for
different API version schemas and returns raw data that can be formatted by any version.
"""

from typing import List, Optional, Union, Dict, Any, Tuple
from datetime import date
import uuid
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.exceptions import VetClinicException, NotFoundError, ValidationError
from app.models.pet import Pet, PetGender, PetSize, HealthRecord, HealthRecordType
from .services import PetService


class PetController:
    """Version-agnostic controller for pet-related operations."""

    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.service = PetService(db)
        self.db = db

    async def list_pets(
        self,
        page: int = 1,
        per_page: int = 10,
        owner_id: Optional[uuid.UUID] = None,
        species: Optional[str] = None,
        breed: Optional[str] = None,
        gender: Optional[Union[PetGender, str]] = None,
        size: Optional[Union[PetSize, str]] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        include_health_records: bool = False,  # V2 parameter
        include_owner: bool = False,  # V2 parameter
        sort_by: Optional[str] = None,  # V2 parameter
        **kwargs
    ) -> Tuple[List[Pet], int]:
        """
        List pets with pagination and filtering.
        Handles business rules and validation before delegating to service.
        
        Args:
            page: Page number (1-based)
            per_page: Items per page
            owner_id: Filter by owner ID
            species: Filter by species
            breed: Filter by breed
            gender: Filter by gender
            size: Filter by size
            is_active: Filter by active status
            search: Search term for name or breed
            include_health_records: Include health records (V2)
            include_owner: Include owner information (V2)
            sort_by: Sort by field (V2)
            **kwargs: Additional parameters for future versions
            
        Returns:
            Tuple of (pets list, total count)
            
        Raises:
            HTTPException: For validation errors or business rule violations
        """
        try:
            # Validate pagination parameters
            if page < 1:
                raise ValidationError("Page must be greater than 0")
            if per_page < 1 or per_page > 100:
                raise ValidationError("Items per page must be between 1 and 100")
            
            # Delegate to service
            pets, total = await self.service.list_pets(
                page=page,
                per_page=per_page,
                owner_id=owner_id,
                species=species,
                breed=breed,
                gender=gender,
                size=size,
                is_active=is_active,
                search=search,
                include_health_records=include_health_records,
                include_owner=include_owner,
                sort_by=sort_by,
                **kwargs
            )
            
            return pets, total
            
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def get_pet_by_id(
        self,
        pet_id: uuid.UUID,
        include_health_records: bool = False,
        include_owner: bool = False,
        include_appointments: bool = False,
        **kwargs
    ) -> Pet:
        """
        Get pet by ID with optional related data.
        
        Args:
            pet_id: Pet UUID
            include_health_records: Include health records (V2)
            include_owner: Include owner information (V2)
            include_appointments: Include appointments (V2)
            **kwargs: Additional parameters for future versions
            
        Returns:
            Pet object
            
        Raises:
            HTTPException: If pet not found or validation errors
        """
        try:
            pet = await self.service.get_pet_by_id(
                pet_id=pet_id,
                include_health_records=include_health_records,
                include_owner=include_owner,
                include_appointments=include_appointments,
                **kwargs
            )
            return pet
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def create_pet(
        self,
        pet_data: Union[BaseModel, Dict[str, Any]],
        created_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Pet:
        """
        Create a new pet.
        Accepts Union[PetCreateV1, PetCreateV2] for create operations.
        
        Args:
            pet_data: Pet creation data (V1 or V2 schema)
            created_by: ID of user creating this pet
            **kwargs: Additional parameters for future versions
            
        Returns:
            Created pet object
            
        Raises:
            HTTPException: For validation errors or business rule violations
        """
        try:
            # Extract data from schema or dict
            if isinstance(pet_data, BaseModel):
                data = pet_data.model_dump(exclude_unset=True)
            else:
                data = pet_data
            
            # Business rule validation
            await self._validate_pet_creation(data, created_by)
            
            # Extract common fields
            owner_id = data.get("owner_id")
            name = data.get("name")
            species = data.get("species")
            breed = data.get("breed")
            mixed_breed = data.get("mixed_breed", False)
            gender = data.get("gender", PetGender.UNKNOWN)
            size = data.get("size")
            weight = data.get("weight")
            color = data.get("color")
            birth_date = data.get("birth_date")
            age_years = data.get("age_years")
            age_months = data.get("age_months")
            is_age_estimated = data.get("is_age_estimated", False)
            microchip_id = data.get("microchip_id")
            registration_number = data.get("registration_number")
            medical_notes = data.get("medical_notes")
            allergies = data.get("allergies")
            current_medications = data.get("current_medications")
            special_needs = data.get("special_needs")
            temperament = data.get("temperament")
            behavioral_notes = data.get("behavioral_notes")
            profile_image_url = data.get("profile_image_url")
            
            # Extract V2 fields if present
            additional_photos = data.get("additional_photos")
            
            # Create pet
            pet = await self.service.create_pet(
                owner_id=owner_id,
                name=name,
                species=species,
                breed=breed,
                mixed_breed=mixed_breed,
                gender=gender,
                size=size,
                weight=weight,
                color=color,
                birth_date=birth_date,
                age_years=age_years,
                age_months=age_months,
                is_age_estimated=is_age_estimated,
                microchip_id=microchip_id,
                registration_number=registration_number,
                medical_notes=medical_notes,
                allergies=allergies,
                current_medications=current_medications,
                special_needs=special_needs,
                temperament=temperament,
                behavioral_notes=behavioral_notes,
                profile_image_url=profile_image_url,
                additional_photos=additional_photos,
                **kwargs
            )
            
            return pet
            
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def update_pet(
        self,
        pet_id: uuid.UUID,
        pet_data: Union[BaseModel, Dict[str, Any]],
        updated_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Pet:
        """
        Update pet information.
        Accepts Union[PetUpdateV1, PetUpdateV2] for update operations.
        
        Args:
            pet_id: Pet UUID
            pet_data: Pet update data (V1 or V2 schema)
            updated_by: ID of user making the update
            **kwargs: Additional parameters for future versions
            
        Returns:
            Updated pet object
            
        Raises:
            HTTPException: For validation errors or business rule violations
        """
        try:
            # Extract data from schema or dict
            if isinstance(pet_data, BaseModel):
                data = pet_data.model_dump(exclude_unset=True)
            else:
                data = pet_data
            
            # Business rule validation
            await self._validate_pet_update(pet_id, data, updated_by)
            
            # Update pet
            pet = await self.service.update_pet(pet_id=pet_id, **data, **kwargs)
            
            return pet
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def delete_pet(
        self,
        pet_id: uuid.UUID,
        deleted_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Delete a pet.
        
        Args:
            pet_id: Pet UUID
            deleted_by: ID of user performing the deletion
            **kwargs: Additional parameters for future versions
            
        Returns:
            Success confirmation
            
        Raises:
            HTTPException: For validation errors or business rule violations
        """
        try:
            # Business rule validation
            await self._validate_pet_deletion(pet_id, deleted_by)
            
            # Delete pet
            await self.service.delete_pet(pet_id)
            
            return {"success": True, "message": "Pet deleted successfully"}
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def get_pet_by_microchip(
        self,
        microchip_id: str,
        **kwargs
    ) -> Pet:
        """
        Get pet by microchip ID.
        
        Args:
            microchip_id: Microchip ID
            **kwargs: Additional parameters for future versions
            
        Returns:
            Pet object
            
        Raises:
            HTTPException: If pet not found
        """
        try:
            pet = await self.service.get_pet_by_microchip(microchip_id)
            if not pet:
                raise NotFoundError(f"Pet with microchip {microchip_id} not found")
            return pet
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def get_pets_by_owner(
        self,
        owner_id: uuid.UUID,
        is_active: Optional[bool] = True,
        include_health_records: bool = False,
        **kwargs
    ) -> List[Pet]:
        """
        Get all pets owned by a specific user.
        
        Args:
            owner_id: Owner UUID
            is_active: Filter by active status
            include_health_records: Include health records
            **kwargs: Additional parameters for future versions
            
        Returns:
            List of pets
        """
        try:
            pets = await self.service.get_pets_by_owner(
                owner_id=owner_id,
                is_active=is_active,
                include_health_records=include_health_records,
                **kwargs
            )
            return pets
            
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def mark_pet_deceased(
        self,
        pet_id: uuid.UUID,
        deceased_date: date,
        marked_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Pet:
        """
        Mark a pet as deceased.
        
        Args:
            pet_id: Pet UUID
            deceased_date: Date of death
            marked_by: ID of user marking the pet as deceased
            **kwargs: Additional parameters for future versions
            
        Returns:
            Updated pet object
        """
        try:
            # Business rule validation
            await self._validate_pet_deceased_marking(pet_id, deceased_date, marked_by)
            
            pet = await self.service.mark_pet_deceased(pet_id, deceased_date)
            return pet
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def add_health_record(
        self,
        pet_id: uuid.UUID,
        record_data: Union[BaseModel, Dict[str, Any]],
        created_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> HealthRecord:
        """
        Add a health record to a pet.
        
        Args:
            pet_id: Pet UUID
            record_data: Health record data
            created_by: ID of user creating the record
            **kwargs: Additional parameters for future versions
            
        Returns:
            Created health record
        """
        try:
            # Extract data from schema or dict
            if isinstance(record_data, BaseModel):
                data = record_data.model_dump(exclude_unset=True)
            else:
                data = record_data
            
            # Business rule validation
            await self._validate_health_record_creation(pet_id, data, created_by)
            
            # Extract required fields
            record_type = data.get("record_type")
            title = data.get("title")
            description = data.get("description")
            record_date = data.get("record_date")
            
            # Create health record
            record = await self.service.add_health_record(
                pet_id=pet_id,
                record_type=record_type,
                title=title,
                description=description,
                record_date=record_date,
                **{k: v for k, v in data.items() if k not in ["record_type", "title", "description", "record_date"]}
            )
            
            return record
            
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def get_pet_health_records(
        self,
        pet_id: uuid.UUID,
        record_type: Optional[Union[HealthRecordType, str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        **kwargs
    ) -> List[HealthRecord]:
        """
        Get health records for a pet.
        
        Args:
            pet_id: Pet UUID
            record_type: Filter by record type
            start_date: Filter by start date
            end_date: Filter by end date
            **kwargs: Additional parameters for future versions
            
        Returns:
            List of health records
        """
        try:
            records = await self.service.get_pet_health_records(
                pet_id=pet_id,
                record_type=record_type,
                start_date=start_date,
                end_date=end_date,
                **kwargs
            )
            return records
            
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    # Private helper methods for business rule validation

    async def _validate_pet_creation(
        self,
        data: Dict[str, Any],
        created_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for pet creation."""
        # Validate required fields
        required_fields = ["owner_id", "name", "species"]
        for field in required_fields:
            if not data.get(field):
                raise ValidationError(f"{field} is required")
        
        # Validate name is not empty
        name = data.get("name", "").strip()
        if not name:
            raise ValidationError("Pet name cannot be empty")
        
        # Validate species is not empty
        species = data.get("species", "").strip()
        if not species:
            raise ValidationError("Pet species cannot be empty")
        
        # Validate gender if provided
        gender = data.get("gender")
        if gender and isinstance(gender, str):
            try:
                PetGender(gender)
            except ValueError:
                raise ValidationError(f"Invalid gender: {gender}")
        
        # Validate size if provided
        size = data.get("size")
        if size and isinstance(size, str):
            try:
                PetSize(size)
            except ValueError:
                raise ValidationError(f"Invalid size: {size}")
        
        # Validate weight if provided
        weight = data.get("weight")
        if weight is not None and weight < 0:
            raise ValidationError("Weight cannot be negative")
        
        # Validate age if provided
        age_years = data.get("age_years")
        age_months = data.get("age_months")
        if age_years is not None and age_years < 0:
            raise ValidationError("Age in years cannot be negative")
        if age_months is not None and age_months < 0:
            raise ValidationError("Age in months cannot be negative")

    async def _validate_pet_update(
        self,
        pet_id: uuid.UUID,
        data: Dict[str, Any],
        updated_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for pet updates."""
        # Validate name if provided
        name = data.get("name")
        if name is not None and not name.strip():
            raise ValidationError("Pet name cannot be empty")
        
        # Validate species if provided
        species = data.get("species")
        if species is not None and not species.strip():
            raise ValidationError("Pet species cannot be empty")
        
        # Validate gender if provided
        gender = data.get("gender")
        if gender and isinstance(gender, str):
            try:
                PetGender(gender)
            except ValueError:
                raise ValidationError(f"Invalid gender: {gender}")
        
        # Validate size if provided
        size = data.get("size")
        if size and isinstance(size, str):
            try:
                PetSize(size)
            except ValueError:
                raise ValidationError(f"Invalid size: {size}")
        
        # Validate weight if provided
        weight = data.get("weight")
        if weight is not None and weight < 0:
            raise ValidationError("Weight cannot be negative")

    async def _validate_pet_deletion(
        self,
        pet_id: uuid.UUID,
        deleted_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for pet deletion."""
        # Check if pet exists
        await self.service.get_pet_by_id(pet_id)
        
        # Additional business rules can be added here
        # For example: prevent deletion of pets with active appointments
        pass

    async def _validate_pet_deceased_marking(
        self,
        pet_id: uuid.UUID,
        deceased_date: date,
        marked_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for marking pet as deceased."""
        # Check if pet exists
        pet = await self.service.get_pet_by_id(pet_id)
        
        # Validate deceased date is not in the future
        from datetime import date as current_date
        if deceased_date > current_date.today():
            raise ValidationError("Deceased date cannot be in the future")
        
        # Validate pet is not already deceased
        if pet.is_deceased:
            raise ValidationError("Pet is already marked as deceased")

    async def _validate_health_record_creation(
        self,
        pet_id: uuid.UUID,
        data: Dict[str, Any],
        created_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for health record creation."""
        # Validate required fields
        required_fields = ["record_type", "title"]
        for field in required_fields:
            if not data.get(field):
                raise ValidationError(f"{field} is required")
        
        # Validate record type
        record_type = data.get("record_type")
        if isinstance(record_type, str):
            try:
                HealthRecordType(record_type)
            except ValueError:
                raise ValidationError(f"Invalid record type: {record_type}")
        
        # Validate title is not empty
        title = data.get("title", "").strip()
        if not title:
            raise ValidationError("Health record title cannot be empty")
        
        # Validate record date if provided
        record_date = data.get("record_date")
        if record_date:
            from datetime import date as current_date
            if record_date > current_date.today():
                raise ValidationError("Record date cannot be in the future")