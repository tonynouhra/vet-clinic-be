"""
Version-agnostic Clinic Service

This service handles data access and core business logic for clinic and veterinarian
related operations across all API versions. It supports dynamic parameters to
accommodate different API version requirements.
"""

from typing import List, Tuple, Optional, Dict, Any, Union
from datetime import date, datetime, time
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, delete, text
from sqlalchemy.orm import selectinload, joinedload

from app.models.clinic import (
    Clinic, Veterinarian, VeterinarianAvailability, ClinicOperatingHours,
    ClinicReview, VeterinarianReview, ClinicType, VeterinarianSpecialty,
    DayOfWeek, veterinarian_specialties
)
from app.models.user import User
from app.core.exceptions import VetClinicException, NotFoundError, ValidationError


class ClinicService:
    """Version-agnostic service for clinic and veterinarian data access and core business logic."""

    def __init__(self, db: AsyncSession):
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
        Supports dynamic parameters for different API versions.
        """
        try:
            # Build base query
            query = select(Clinic)
            count_query = select(func.count(Clinic.id))
            
            # Apply filters
            conditions = []
            
            if clinic_type:
                if isinstance(clinic_type, str):
                    try:
                        clinic_type = ClinicType(clinic_type)
                    except ValueError:
                        raise ValidationError(f"Invalid clinic type: {clinic_type}")
                conditions.append(Clinic.clinic_type == clinic_type)
            
            if city:
                conditions.append(Clinic.city.ilike(f"%{city}%"))
            
            if state:
                conditions.append(Clinic.state.ilike(f"%{state}%"))
            
            if is_emergency is not None:
                conditions.append(Clinic.is_emergency_clinic == is_emergency)
            
            if is_24_hour is not None:
                conditions.append(Clinic.is_24_hour == is_24_hour)
            
            if is_accepting_patients is not None:
                conditions.append(Clinic.is_accepting_new_patients == is_accepting_patients)
            
            if search:
                search_term = f"%{search}%"
                conditions.append(
                    or_(
                        Clinic.name.ilike(search_term),
                        Clinic.description.ilike(search_term),
                        Clinic.city.ilike(search_term),
                        Clinic.address_line1.ilike(search_term)
                    )
                )
            
            # Location-based filtering
            if latitude is not None and longitude is not None and radius_miles is not None:
                # Use Haversine formula for distance calculation
                distance_query = text("""
                    (3959 * acos(
                        cos(radians(:lat)) * cos(radians(latitude)) * 
                        cos(radians(longitude) - radians(:lng)) + 
                        sin(radians(:lat)) * sin(radians(latitude))
                    )) <= :radius
                """)
                conditions.append(distance_query.bindparams(
                    lat=latitude, lng=longitude, radius=radius_miles
                ))
            
            # Always filter for active clinics
            conditions.append(Clinic.is_active == True)
            
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
            
            # Add relationships if requested
            if include_veterinarians:
                query = query.options(selectinload(Clinic.veterinarians))
            
            if include_reviews:
                query = query.options(selectinload(Clinic.reviews))
            
            # Get total count
            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Apply sorting
            if sort_by:
                if sort_by == "name":
                    query = query.order_by(Clinic.name)
                elif sort_by == "city":
                    query = query.order_by(Clinic.city, Clinic.name)
                elif sort_by == "rating":
                    # This would require a subquery for average rating
                    query = query.order_by(Clinic.created_at.desc())
                elif sort_by == "distance" and latitude and longitude:
                    # Order by distance when location is provided
                    distance_order = text("""
                        (3959 * acos(
                            cos(radians(:lat)) * cos(radians(latitude)) * 
                            cos(radians(longitude) - radians(:lng)) + 
                            sin(radians(:lat)) * sin(radians(latitude))
                        ))
                    """).bindparams(lat=latitude, lng=longitude)
                    query = query.order_by(distance_order)
                else:
                    query = query.order_by(Clinic.created_at.desc())
            else:
                query = query.order_by(Clinic.name)
            
            # Apply pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            # Execute query
            result = await self.db.execute(query)
            clinics = result.scalars().all()
            
            return list(clinics), total
            
        except Exception as e:
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to list clinics: {str(e)}")

    async def get_clinic_by_id(
        self,
        clinic_id: uuid.UUID,
        include_veterinarians: bool = False,
        include_reviews: bool = False,
        include_operating_hours: bool = False,
        **kwargs
    ) -> Clinic:
        """Get clinic by ID with optional related data."""
        try:
            query = select(Clinic).where(Clinic.id == clinic_id)
            
            # Add optional relationships
            if include_veterinarians:
                query = query.options(selectinload(Clinic.veterinarians))
            
            if include_reviews:
                query = query.options(selectinload(Clinic.reviews))
            
            if include_operating_hours:
                query = query.options(selectinload(Clinic.operating_hours))
            
            result = await self.db.execute(query)
            clinic = result.scalar_one_or_none()
            
            if not clinic:
                raise NotFoundError(f"Clinic with id {clinic_id} not found")
            
            return clinic
            
        except Exception as e:
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to get clinic by id: {str(e)}")

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
        Supports dynamic parameters for different API versions.
        """
        try:
            # Build base query with user join for search functionality
            query = select(Veterinarian).join(User, Veterinarian.user_id == User.id)
            count_query = select(func.count(Veterinarian.id)).join(User, Veterinarian.user_id == User.id)
            
            # Apply filters
            conditions = []
            
            if clinic_id:
                conditions.append(Veterinarian.clinic_id == clinic_id)
            
            if specialty:
                if isinstance(specialty, str):
                    try:
                        specialty = VeterinarianSpecialty(specialty)
                    except ValueError:
                        raise ValidationError(f"Invalid specialty: {specialty}")
                # Join with veterinarian_specialties table
                specialty_subquery = select(veterinarian_specialties.c.veterinarian_id).where(
                    veterinarian_specialties.c.specialty == specialty
                )
                conditions.append(Veterinarian.id.in_(specialty_subquery))
            
            if is_available_for_emergency is not None:
                conditions.append(Veterinarian.is_available_for_emergency == is_available_for_emergency)
            
            if is_accepting_patients is not None:
                conditions.append(Veterinarian.is_accepting_new_patients == is_accepting_patients)
            
            if min_experience_years is not None:
                conditions.append(Veterinarian.years_of_experience >= min_experience_years)
            
            if search:
                search_term = f"%{search}%"
                conditions.append(
                    or_(
                        User.first_name.ilike(search_term),
                        User.last_name.ilike(search_term),
                        Veterinarian.bio.ilike(search_term),
                        Veterinarian.license_number.ilike(search_term)
                    )
                )
            
            # Location-based filtering through clinic
            if city or state:
                query = query.join(Clinic, Veterinarian.clinic_id == Clinic.id)
                count_query = count_query.join(Clinic, Veterinarian.clinic_id == Clinic.id)
                
                if city:
                    conditions.append(Clinic.city.ilike(f"%{city}%"))
                if state:
                    conditions.append(Clinic.state.ilike(f"%{state}%"))
            
            # Always filter for active veterinarians
            conditions.append(Veterinarian.is_active == True)
            conditions.append(User.is_active == True)
            
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
            
            # Add relationships if requested
            if include_clinic:
                query = query.options(selectinload(Veterinarian.clinic))
            
            if include_reviews:
                query = query.options(selectinload(Veterinarian.reviews))
            
            if include_availability:
                query = query.options(selectinload(Veterinarian.availability))
            
            # Always include user information
            query = query.options(selectinload(Veterinarian.user))
            
            # Get total count
            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Apply sorting
            if sort_by:
                if sort_by == "name":
                    query = query.order_by(User.first_name, User.last_name)
                elif sort_by == "experience":
                    query = query.order_by(Veterinarian.years_of_experience.desc())
                elif sort_by == "rating":
                    # This would require a subquery for average rating
                    query = query.order_by(Veterinarian.created_at.desc())
                else:
                    query = query.order_by(User.first_name, User.last_name)
            else:
                query = query.order_by(User.first_name, User.last_name)
            
            # Apply pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            # Execute query
            result = await self.db.execute(query)
            veterinarians = result.scalars().all()
            
            return list(veterinarians), total
            
        except Exception as e:
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to list veterinarians: {str(e)}")

    async def get_veterinarian_by_id(
        self,
        veterinarian_id: uuid.UUID,
        include_clinic: bool = False,
        include_reviews: bool = False,
        include_availability: bool = False,
        include_specialties: bool = False,
        **kwargs
    ) -> Veterinarian:
        """Get veterinarian by ID with optional related data."""
        try:
            query = select(Veterinarian).where(Veterinarian.id == veterinarian_id)
            
            # Always include user information
            query = query.options(selectinload(Veterinarian.user))
            
            # Add optional relationships
            if include_clinic:
                query = query.options(selectinload(Veterinarian.clinic))
            
            if include_reviews:
                query = query.options(selectinload(Veterinarian.reviews))
            
            if include_availability:
                query = query.options(selectinload(Veterinarian.availability))
            
            result = await self.db.execute(query)
            veterinarian = result.scalar_one_or_none()
            
            if not veterinarian:
                raise NotFoundError(f"Veterinarian with id {veterinarian_id} not found")
            
            # Get specialties if requested
            if include_specialties:
                specialties_query = select(veterinarian_specialties).where(
                    veterinarian_specialties.c.veterinarian_id == veterinarian_id
                )
                specialties_result = await self.db.execute(specialties_query)
                veterinarian._specialties = [
                    {
                        "specialty": row.specialty,
                        "certification_date": row.certification_date,
                        "certification_body": row.certification_body
                    }
                    for row in specialties_result
                ]
            
            return veterinarian
            
        except Exception as e:
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to get veterinarian by id: {str(e)}")

    async def get_veterinarian_by_user_id(
        self,
        user_id: uuid.UUID,
        **kwargs
    ) -> Optional[Veterinarian]:
        """Get veterinarian by user ID."""
        try:
            query = select(Veterinarian).where(Veterinarian.user_id == user_id)
            query = query.options(selectinload(Veterinarian.user))
            query = query.options(selectinload(Veterinarian.clinic))
            
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            raise VetClinicException(f"Failed to get veterinarian by user id: {str(e)}")

    # Availability Management Methods

    async def get_veterinarian_availability(
        self,
        veterinarian_id: uuid.UUID,
        day_of_week: Optional[Union[DayOfWeek, str]] = None,
        **kwargs
    ) -> List[VeterinarianAvailability]:
        """Get veterinarian availability schedule."""
        try:
            query = select(VeterinarianAvailability).where(
                VeterinarianAvailability.veterinarian_id == veterinarian_id
            )
            
            if day_of_week:
                if isinstance(day_of_week, str):
                    try:
                        day_of_week = DayOfWeek(day_of_week)
                    except ValueError:
                        raise ValidationError(f"Invalid day of week: {day_of_week}")
                query = query.where(VeterinarianAvailability.day_of_week == day_of_week)
            
            query = query.order_by(VeterinarianAvailability.day_of_week)
            
            result = await self.db.execute(query)
            availability = result.scalars().all()
            
            return list(availability)
            
        except Exception as e:
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to get veterinarian availability: {str(e)}")

    async def update_veterinarian_availability(
        self,
        veterinarian_id: uuid.UUID,
        availability_data: List[Dict[str, Any]],
        **kwargs
    ) -> List[VeterinarianAvailability]:
        """Update veterinarian availability schedule."""
        try:
            # Verify veterinarian exists
            await self.get_veterinarian_by_id(veterinarian_id)
            
            # Delete existing availability
            delete_query = delete(VeterinarianAvailability).where(
                VeterinarianAvailability.veterinarian_id == veterinarian_id
            )
            await self.db.execute(delete_query)
            
            # Create new availability records
            new_availability = []
            for data in availability_data:
                day_of_week = data.get("day_of_week")
                if isinstance(day_of_week, str):
                    day_of_week = DayOfWeek(day_of_week)
                
                availability = VeterinarianAvailability(
                    veterinarian_id=veterinarian_id,
                    day_of_week=day_of_week,
                    is_available=data.get("is_available", True),
                    start_time=data.get("start_time"),
                    end_time=data.get("end_time"),
                    break_start_time=data.get("break_start_time"),
                    break_end_time=data.get("break_end_time"),
                    default_appointment_duration=data.get("default_appointment_duration", 30),
                    notes=data.get("notes")
                )
                self.db.add(availability)
                new_availability.append(availability)
            
            await self.db.commit()
            
            # Refresh all objects
            for availability in new_availability:
                await self.db.refresh(availability)
            
            return new_availability
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to update veterinarian availability: {str(e)}")

    # Review Management Methods

    async def create_clinic_review(
        self,
        clinic_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        rating: int,
        title: Optional[str] = None,
        review_text: Optional[str] = None,
        is_anonymous: bool = False,
        **kwargs
    ) -> ClinicReview:
        """Create a clinic review."""
        try:
            # Verify clinic exists
            await self.get_clinic_by_id(clinic_id)
            
            # Validate rating
            if rating < 1 or rating > 5:
                raise ValidationError("Rating must be between 1 and 5")
            
            review = ClinicReview(
                clinic_id=clinic_id,
                reviewer_id=reviewer_id,
                rating=rating,
                title=title.strip() if title else None,
                review_text=review_text.strip() if review_text else None,
                is_anonymous=is_anonymous,
                is_verified=False  # Would be set by admin/verification process
            )
            
            self.db.add(review)
            await self.db.commit()
            await self.db.refresh(review)
            
            return review
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to create clinic review: {str(e)}")

    async def create_veterinarian_review(
        self,
        veterinarian_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        rating: int,
        title: Optional[str] = None,
        review_text: Optional[str] = None,
        bedside_manner_rating: Optional[int] = None,
        expertise_rating: Optional[int] = None,
        communication_rating: Optional[int] = None,
        is_anonymous: bool = False,
        **kwargs
    ) -> VeterinarianReview:
        """Create a veterinarian review."""
        try:
            # Verify veterinarian exists
            await self.get_veterinarian_by_id(veterinarian_id)
            
            # Validate ratings
            ratings_to_validate = [
                ("rating", rating),
                ("bedside_manner_rating", bedside_manner_rating),
                ("expertise_rating", expertise_rating),
                ("communication_rating", communication_rating)
            ]
            
            for rating_name, rating_value in ratings_to_validate:
                if rating_value is not None and (rating_value < 1 or rating_value > 5):
                    raise ValidationError(f"{rating_name} must be between 1 and 5")
            
            review = VeterinarianReview(
                veterinarian_id=veterinarian_id,
                reviewer_id=reviewer_id,
                rating=rating,
                title=title.strip() if title else None,
                review_text=review_text.strip() if review_text else None,
                bedside_manner_rating=bedside_manner_rating,
                expertise_rating=expertise_rating,
                communication_rating=communication_rating,
                is_anonymous=is_anonymous,
                is_verified=False  # Would be set by admin/verification process
            )
            
            self.db.add(review)
            await self.db.commit()
            await self.db.refresh(review)
            
            return review
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to create veterinarian review: {str(e)}")

    async def get_clinic_reviews(
        self,
        clinic_id: uuid.UUID,
        page: int = 1,
        per_page: int = 10,
        **kwargs
    ) -> Tuple[List[ClinicReview], int]:
        """Get reviews for a clinic."""
        try:
            query = select(ClinicReview).where(ClinicReview.clinic_id == clinic_id)
            count_query = select(func.count(ClinicReview.id)).where(ClinicReview.clinic_id == clinic_id)
            
            # Get total count
            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Apply pagination and ordering
            query = query.order_by(ClinicReview.created_at.desc())
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            # Include reviewer information
            query = query.options(selectinload(ClinicReview.reviewer))
            
            result = await self.db.execute(query)
            reviews = result.scalars().all()
            
            return list(reviews), total
            
        except Exception as e:
            raise VetClinicException(f"Failed to get clinic reviews: {str(e)}")

    async def get_veterinarian_reviews(
        self,
        veterinarian_id: uuid.UUID,
        page: int = 1,
        per_page: int = 10,
        **kwargs
    ) -> Tuple[List[VeterinarianReview], int]:
        """Get reviews for a veterinarian."""
        try:
            query = select(VeterinarianReview).where(VeterinarianReview.veterinarian_id == veterinarian_id)
            count_query = select(func.count(VeterinarianReview.id)).where(VeterinarianReview.veterinarian_id == veterinarian_id)
            
            # Get total count
            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Apply pagination and ordering
            query = query.order_by(VeterinarianReview.created_at.desc())
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            # Include reviewer information
            query = query.options(selectinload(VeterinarianReview.reviewer))
            
            result = await self.db.execute(query)
            reviews = result.scalars().all()
            
            return list(reviews), total
            
        except Exception as e:
            raise VetClinicException(f"Failed to get veterinarian reviews: {str(e)}")

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
        """Search veterinarians by location with distance calculation."""
        try:
            # Build query with distance calculation
            distance_formula = text("""
                (3959 * acos(
                    cos(radians(:lat)) * cos(radians(clinics.latitude)) * 
                    cos(radians(clinics.longitude) - radians(:lng)) + 
                    sin(radians(:lat)) * sin(radians(clinics.latitude))
                )) as distance
            """).bindparams(lat=latitude, lng=longitude)
            
            query = select(Veterinarian, distance_formula).join(
                Clinic, Veterinarian.clinic_id == Clinic.id
            ).join(User, Veterinarian.user_id == User.id)
            
            count_query = select(func.count(Veterinarian.id)).join(
                Clinic, Veterinarian.clinic_id == Clinic.id
            ).join(User, Veterinarian.user_id == User.id)
            
            # Apply distance filter
            distance_condition = text("""
                (3959 * acos(
                    cos(radians(:lat)) * cos(radians(clinics.latitude)) * 
                    cos(radians(clinics.longitude) - radians(:lng)) + 
                    sin(radians(:lat)) * sin(radians(clinics.latitude))
                )) <= :radius
            """).bindparams(lat=latitude, lng=longitude, radius=radius_miles)
            
            conditions = [distance_condition]
            
            # Apply additional filters
            if specialty:
                if isinstance(specialty, str):
                    specialty = VeterinarianSpecialty(specialty)
                specialty_subquery = select(veterinarian_specialties.c.veterinarian_id).where(
                    veterinarian_specialties.c.specialty == specialty
                )
                conditions.append(Veterinarian.id.in_(specialty_subquery))
            
            if is_available_for_emergency is not None:
                conditions.append(Veterinarian.is_available_for_emergency == is_available_for_emergency)
            
            # Always filter for active records
            conditions.extend([
                Veterinarian.is_active == True,
                User.is_active == True,
                Clinic.is_active == True
            ])
            
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
            
            # Get total count
            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Order by distance
            query = query.order_by(text("distance"))
            
            # Apply pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            # Include related data
            query = query.options(
                selectinload(Veterinarian.user),
                selectinload(Veterinarian.clinic)
            )
            
            result = await self.db.execute(query)
            veterinarians_with_distance = result.all()
            
            # Extract just the veterinarians (distance is available as second element)
            veterinarians = [row[0] for row in veterinarians_with_distance]
            
            return veterinarians, total
            
        except Exception as e:
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to search veterinarians by location: {str(e)}")

    async def get_veterinarian_specialties(
        self,
        veterinarian_id: uuid.UUID,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Get specialties for a veterinarian."""
        try:
            query = select(veterinarian_specialties).where(
                veterinarian_specialties.c.veterinarian_id == veterinarian_id
            )
            
            result = await self.db.execute(query)
            specialties = [
                {
                    "specialty": row.specialty,
                    "certification_date": row.certification_date,
                    "certification_body": row.certification_body
                }
                for row in result
            ]
            
            return specialties
            
        except Exception as e:
            raise VetClinicException(f"Failed to get veterinarian specialties: {str(e)}")