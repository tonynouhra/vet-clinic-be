"""
Version-agnostic Pet Service

This service handles data access and core business logic for pet-related
operations across all API versions. It supports dynamic parameters to
accommodate different API version requirements.
"""

from typing import List, Tuple, Optional, Dict, Any, Union
from datetime import date, datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.orm import selectinload

from app.models.pet import Pet, PetGender, PetSize, HealthRecord, HealthRecordType, Reminder
from app.core.exceptions import VetClinicException, NotFoundError, ValidationError


class PetService:
    """Version-agnostic service for pet data access and core business logic."""

    def __init__(self, db: AsyncSession):
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
        Supports dynamic parameters for different API versions.
        
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
        """
        try:
            # Build base query
            query = select(Pet)
            count_query = select(func.count(Pet.id))
            
            # Apply filters
            conditions = []
            
            if owner_id:
                conditions.append(Pet.owner_id == owner_id)
            
            if species:
                conditions.append(Pet.species.ilike(f"%{species}%"))
            
            if breed:
                conditions.append(Pet.breed.ilike(f"%{breed}%"))
            
            if gender:
                if isinstance(gender, str):
                    try:
                        gender = PetGender(gender)
                    except ValueError:
                        raise ValidationError(f"Invalid gender: {gender}")
                conditions.append(Pet.gender == gender)
            
            if size:
                if isinstance(size, str):
                    try:
                        size = PetSize(size)
                    except ValueError:
                        raise ValidationError(f"Invalid size: {size}")
                conditions.append(Pet.size == size)
            
            if is_active is not None:
                conditions.append(Pet.is_active == is_active)
            
            if search:
                search_term = f"%{search}%"
                conditions.append(
                    or_(
                        Pet.name.ilike(search_term),
                        Pet.breed.ilike(search_term),
                        Pet.species.ilike(search_term)
                    )
                )
            
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
            
            # Add relationships if requested (V2)
            if include_health_records:
                query = query.options(selectinload(Pet.health_records))
            
            if include_owner:
                query = query.options(selectinload(Pet.owner))
            
            # Get total count
            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Apply sorting (V2 feature)
            if sort_by:
                if sort_by == "name":
                    query = query.order_by(Pet.name)
                elif sort_by == "created_at":
                    query = query.order_by(Pet.created_at.desc())
                elif sort_by == "age":
                    query = query.order_by(Pet.birth_date.desc())
                else:
                    query = query.order_by(Pet.created_at.desc())
            else:
                query = query.order_by(Pet.created_at.desc())
            
            # Apply pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            # Execute query
            result = await self.db.execute(query)
            pets = result.scalars().all()
            
            return list(pets), total
            
        except Exception as e:
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to list pets: {str(e)}")

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
            NotFoundError: If pet not found
        """
        try:
            query = select(Pet).where(Pet.id == pet_id)
            
            # Add optional relationships based on version needs
            if include_health_records:
                query = query.options(selectinload(Pet.health_records))
            
            if include_owner:
                query = query.options(selectinload(Pet.owner))
            
            if include_appointments:
                query = query.options(selectinload(Pet.appointments))
            
            result = await self.db.execute(query)
            pet = result.scalar_one_or_none()
            
            if not pet:
                raise NotFoundError(f"Pet with id {pet_id} not found")
            
            return pet
            
        except Exception as e:
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to get pet by id: {str(e)}")

    async def create_pet(
        self,
        owner_id: uuid.UUID,
        name: str,
        species: str,
        breed: Optional[str] = None,
        mixed_breed: bool = False,
        gender: Union[PetGender, str] = PetGender.UNKNOWN,
        size: Optional[Union[PetSize, str]] = None,
        weight: Optional[float] = None,
        color: Optional[str] = None,
        birth_date: Optional[date] = None,
        age_years: Optional[int] = None,
        age_months: Optional[int] = None,
        is_age_estimated: bool = False,
        microchip_id: Optional[str] = None,
        registration_number: Optional[str] = None,
        medical_notes: Optional[str] = None,
        allergies: Optional[str] = None,
        current_medications: Optional[str] = None,
        special_needs: Optional[str] = None,
        temperament: Optional[str] = None,
        behavioral_notes: Optional[str] = None,
        profile_image_url: Optional[str] = None,
        additional_photos: Optional[List[str]] = None,  # V2 parameter
        **kwargs
    ) -> Pet:
        """
        Create a new pet.
        Supports dynamic parameters for different API versions.
        
        Args:
            owner_id: Owner UUID
            name: Pet name
            species: Pet species
            breed: Pet breed
            mixed_breed: Is mixed breed
            gender: Pet gender
            size: Pet size
            weight: Pet weight
            color: Pet color
            birth_date: Pet birth date
            age_years: Age in years
            age_months: Age in months
            is_age_estimated: Is age estimated
            microchip_id: Microchip ID
            registration_number: Registration number
            medical_notes: Medical notes
            allergies: Allergies
            current_medications: Current medications
            special_needs: Special needs
            temperament: Temperament
            behavioral_notes: Behavioral notes
            profile_image_url: Profile image URL
            additional_photos: Additional photos (V2)
            **kwargs: Additional parameters for future versions
            
        Returns:
            Created pet object
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Handle enum parameters
            if isinstance(gender, str):
                try:
                    gender = PetGender(gender)
                except ValueError:
                    raise ValidationError(f"Invalid gender: {gender}")
            
            if size and isinstance(size, str):
                try:
                    size = PetSize(size)
                except ValueError:
                    raise ValidationError(f"Invalid size: {size}")
            
            # Validate microchip uniqueness if provided
            if microchip_id:
                existing_pet = await self.get_pet_by_microchip(microchip_id)
                if existing_pet:
                    raise ValidationError("Microchip ID already registered")
            
            # Create pet data
            pet_data = {
                "owner_id": owner_id,
                "name": name.strip(),
                "species": species.strip().lower(),
                "breed": breed.strip() if breed else None,
                "mixed_breed": mixed_breed,
                "gender": gender,
                "size": size,
                "weight": weight,
                "color": color.strip() if color else None,
                "birth_date": birth_date,
                "age_years": age_years,
                "age_months": age_months,
                "is_age_estimated": is_age_estimated,
                "microchip_id": microchip_id.strip() if microchip_id else None,
                "registration_number": registration_number.strip() if registration_number else None,
                "medical_notes": medical_notes.strip() if medical_notes else None,
                "allergies": allergies.strip() if allergies else None,
                "current_medications": current_medications.strip() if current_medications else None,
                "special_needs": special_needs.strip() if special_needs else None,
                "temperament": temperament.strip() if temperament else None,
                "behavioral_notes": behavioral_notes.strip() if behavioral_notes else None,
                "profile_image_url": profile_image_url,
            }
            
            # Add V2 parameters
            if additional_photos:
                pet_data["additional_photos"] = additional_photos
            
            # Create new pet
            new_pet = Pet(**pet_data)
            
            self.db.add(new_pet)
            await self.db.commit()
            await self.db.refresh(new_pet)
            
            return new_pet
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to create pet: {str(e)}")

    async def update_pet(
        self,
        pet_id: uuid.UUID,
        name: Optional[str] = None,
        species: Optional[str] = None,
        breed: Optional[str] = None,
        mixed_breed: Optional[bool] = None,
        gender: Optional[Union[PetGender, str]] = None,
        size: Optional[Union[PetSize, str]] = None,
        weight: Optional[float] = None,
        color: Optional[str] = None,
        birth_date: Optional[date] = None,
        age_years: Optional[int] = None,
        age_months: Optional[int] = None,
        is_age_estimated: Optional[bool] = None,
        microchip_id: Optional[str] = None,
        registration_number: Optional[str] = None,
        medical_notes: Optional[str] = None,
        allergies: Optional[str] = None,
        current_medications: Optional[str] = None,
        special_needs: Optional[str] = None,
        temperament: Optional[str] = None,
        behavioral_notes: Optional[str] = None,
        profile_image_url: Optional[str] = None,
        additional_photos: Optional[List[str]] = None,  # V2 parameter
        is_active: Optional[bool] = None,
        **kwargs
    ) -> Pet:
        """
        Update pet information.
        Supports dynamic parameters for different API versions.
        
        Returns:
            Updated pet object
        """
        try:
            pet = await self.get_pet_by_id(pet_id)
            
            # Update fields if provided
            if name is not None:
                pet.name = name.strip()
            if species is not None:
                pet.species = species.strip().lower()
            if breed is not None:
                pet.breed = breed.strip() if breed else None
            if mixed_breed is not None:
                pet.mixed_breed = mixed_breed
            if gender is not None:
                if isinstance(gender, str):
                    try:
                        gender = PetGender(gender)
                    except ValueError:
                        raise ValidationError(f"Invalid gender: {gender}")
                pet.gender = gender
            if size is not None:
                if isinstance(size, str):
                    try:
                        size = PetSize(size)
                    except ValueError:
                        raise ValidationError(f"Invalid size: {size}")
                pet.size = size
            if weight is not None:
                pet.weight = weight
            if color is not None:
                pet.color = color.strip() if color else None
            if birth_date is not None:
                pet.birth_date = birth_date
            if age_years is not None:
                pet.age_years = age_years
            if age_months is not None:
                pet.age_months = age_months
            if is_age_estimated is not None:
                pet.is_age_estimated = is_age_estimated
            if microchip_id is not None:
                # Check uniqueness if changing
                if microchip_id != pet.microchip_id:
                    existing_pet = await self.get_pet_by_microchip(microchip_id)
                    if existing_pet:
                        raise ValidationError("Microchip ID already registered")
                pet.microchip_id = microchip_id.strip() if microchip_id else None
            if registration_number is not None:
                pet.registration_number = registration_number.strip() if registration_number else None
            if medical_notes is not None:
                pet.medical_notes = medical_notes.strip() if medical_notes else None
            if allergies is not None:
                pet.allergies = allergies.strip() if allergies else None
            if current_medications is not None:
                pet.current_medications = current_medications.strip() if current_medications else None
            if special_needs is not None:
                pet.special_needs = special_needs.strip() if special_needs else None
            if temperament is not None:
                pet.temperament = temperament.strip() if temperament else None
            if behavioral_notes is not None:
                pet.behavioral_notes = behavioral_notes.strip() if behavioral_notes else None
            if profile_image_url is not None:
                pet.profile_image_url = profile_image_url
            if additional_photos is not None:
                pet.additional_photos = additional_photos
            if is_active is not None:
                pet.is_active = is_active
            
            await self.db.commit()
            await self.db.refresh(pet)
            
            return pet
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to update pet: {str(e)}")

    async def delete_pet(self, pet_id: uuid.UUID) -> None:
        """
        Hard delete a pet and related data.
        
        Args:
            pet_id: Pet UUID
        """
        try:
            pet = await self.get_pet_by_id(pet_id)
            
            # Delete related records (handled by cascade)
            await self.db.delete(pet)
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to delete pet: {str(e)}")

    async def get_pet_by_microchip(self, microchip_id: str) -> Optional[Pet]:
        """
        Get pet by microchip ID.
        
        Args:
            microchip_id: Microchip ID
            
        Returns:
            Pet object or None if not found
        """
        try:
            query = select(Pet).where(Pet.microchip_id == microchip_id.strip())
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            raise VetClinicException(f"Failed to get pet by microchip: {str(e)}")

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
            query = select(Pet).where(Pet.owner_id == owner_id)
            
            if is_active is not None:
                query = query.where(Pet.is_active == is_active)
            
            if include_health_records:
                query = query.options(selectinload(Pet.health_records))
            
            query = query.order_by(Pet.created_at.desc())
            
            result = await self.db.execute(query)
            pets = result.scalars().all()
            
            return list(pets)
            
        except Exception as e:
            raise VetClinicException(f"Failed to get pets by owner: {str(e)}")

    async def mark_pet_deceased(
        self,
        pet_id: uuid.UUID,
        deceased_date: date
    ) -> Pet:
        """
        Mark a pet as deceased.
        
        Args:
            pet_id: Pet UUID
            deceased_date: Date of death
            
        Returns:
            Updated pet object
        """
        try:
            pet = await self.get_pet_by_id(pet_id)
            
            pet.is_deceased = True
            pet.deceased_date = deceased_date
            pet.is_active = False
            
            await self.db.commit()
            await self.db.refresh(pet)
            
            return pet
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to mark pet as deceased: {str(e)}")

    async def add_health_record(
        self,
        pet_id: uuid.UUID,
        record_type: Union[HealthRecordType, str],
        title: str,
        description: Optional[str] = None,
        record_date: date = None,
        **kwargs
    ) -> HealthRecord:
        """
        Add a health record to a pet.
        
        Args:
            pet_id: Pet UUID
            record_type: Health record type
            title: Record title
            description: Record description
            record_date: Record date
            **kwargs: Additional parameters for future versions
            
        Returns:
            Created health record
        """
        try:
            # Verify pet exists
            await self.get_pet_by_id(pet_id)
            
            if isinstance(record_type, str):
                try:
                    record_type = HealthRecordType(record_type)
                except ValueError:
                    raise ValidationError(f"Invalid record type: {record_type}")
            
            if record_date is None:
                record_date = date.today()
            
            record_data = {
                "pet_id": pet_id,
                "record_type": record_type,
                "title": title.strip(),
                "description": description.strip() if description else None,
                "record_date": record_date,
            }
            
            # Add additional fields from kwargs
            for field in ["diagnosis", "treatment", "medication_name", "dosage", "frequency", "duration", "cost", "notes"]:
                if field in kwargs and kwargs[field] is not None:
                    record_data[field] = kwargs[field]
            
            new_record = HealthRecord(**record_data)
            
            self.db.add(new_record)
            await self.db.commit()
            await self.db.refresh(new_record)
            
            return new_record
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to add health record: {str(e)}")

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
            query = select(HealthRecord).where(HealthRecord.pet_id == pet_id)
            
            if record_type:
                if isinstance(record_type, str):
                    record_type = HealthRecordType(record_type)
                query = query.where(HealthRecord.record_type == record_type)
            
            if start_date:
                query = query.where(HealthRecord.record_date >= start_date)
            
            if end_date:
                query = query.where(HealthRecord.record_date <= end_date)
            
            query = query.order_by(HealthRecord.record_date.desc())
            
            result = await self.db.execute(query)
            records = result.scalars().all()
            
            return list(records)
            
        except Exception as e:
            raise VetClinicException(f"Failed to get pet health records: {str(e)}")