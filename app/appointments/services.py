"""
Version-agnostic Appointment Service

This service handles data access and core business logic for appointment-related
operations across all API versions. It supports dynamic parameters to
accommodate different API version requirements.
"""

from typing import List, Tuple, Optional, Dict, Any, Union
from datetime import datetime, date, timedelta
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.orm import selectinload

from app.models.appointment import (
    Appointment, 
    AppointmentSlot, 
    AppointmentStatus, 
    AppointmentType, 
    AppointmentPriority
)
from app.core.exceptions import VetClinicException, NotFoundError, ValidationError


class AppointmentService:
    """Version-agnostic service for appointment data access and core business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_appointments(
        self,
        page: int = 1,
        per_page: int = 10,
        pet_id: Optional[uuid.UUID] = None,
        pet_owner_id: Optional[uuid.UUID] = None,
        veterinarian_id: Optional[uuid.UUID] = None,
        clinic_id: Optional[uuid.UUID] = None,
        status: Optional[Union[AppointmentStatus, str]] = None,
        appointment_type: Optional[Union[AppointmentType, str]] = None,
        priority: Optional[Union[AppointmentPriority, str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        upcoming_only: bool = False,
        today_only: bool = False,
        include_pet: bool = False,  # V2 parameter
        include_owner: bool = False,  # V2 parameter
        include_veterinarian: bool = False,  # V2 parameter
        include_clinic: bool = False,  # V2 parameter
        sort_by: Optional[str] = None,  # V2 parameter
        **kwargs
    ) -> Tuple[List[Appointment], int]:
        """
        List appointments with pagination and filtering.
        Supports dynamic parameters for different API versions.
        
        Args:
            page: Page number (1-based)
            per_page: Items per page
            pet_id: Filter by pet ID
            pet_owner_id: Filter by pet owner ID
            veterinarian_id: Filter by veterinarian ID
            clinic_id: Filter by clinic ID
            status: Filter by appointment status
            appointment_type: Filter by appointment type
            priority: Filter by priority
            start_date: Filter by start date
            end_date: Filter by end date
            upcoming_only: Show only upcoming appointments
            today_only: Show only today's appointments
            include_pet: Include pet information (V2)
            include_owner: Include owner information (V2)
            include_veterinarian: Include veterinarian information (V2)
            include_clinic: Include clinic information (V2)
            sort_by: Sort by field (V2)
            **kwargs: Additional parameters for future versions
            
        Returns:
            Tuple of (appointments list, total count)
        """
        try:
            # Build base query
            query = select(Appointment)
            count_query = select(func.count(Appointment.id))
            
            # Apply filters
            conditions = []
            
            if pet_id:
                conditions.append(Appointment.pet_id == pet_id)
            
            if pet_owner_id:
                conditions.append(Appointment.pet_owner_id == pet_owner_id)
            
            if veterinarian_id:
                conditions.append(Appointment.veterinarian_id == veterinarian_id)
            
            if clinic_id:
                conditions.append(Appointment.clinic_id == clinic_id)
            
            if status:
                if isinstance(status, str):
                    try:
                        status = AppointmentStatus(status)
                    except ValueError:
                        raise ValidationError(f"Invalid appointment status: {status}")
                conditions.append(Appointment.status == status)
            
            if appointment_type:
                if isinstance(appointment_type, str):
                    try:
                        appointment_type = AppointmentType(appointment_type)
                    except ValueError:
                        raise ValidationError(f"Invalid appointment type: {appointment_type}")
                conditions.append(Appointment.appointment_type == appointment_type)
            
            if priority:
                if isinstance(priority, str):
                    try:
                        priority = AppointmentPriority(priority)
                    except ValueError:
                        raise ValidationError(f"Invalid priority: {priority}")
                conditions.append(Appointment.priority == priority)
            
            # Date filters
            if start_date:
                start_datetime = datetime.combine(start_date, datetime.min.time())
                conditions.append(Appointment.scheduled_at >= start_datetime)
            
            if end_date:
                end_datetime = datetime.combine(end_date, datetime.max.time())
                conditions.append(Appointment.scheduled_at <= end_datetime)
            
            if upcoming_only:
                now = datetime.utcnow()
                conditions.append(Appointment.scheduled_at > now)
                conditions.append(Appointment.status.in_([
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED
                ]))
            
            if today_only:
                today = datetime.utcnow().date()
                start_of_day = datetime.combine(today, datetime.min.time())
                end_of_day = datetime.combine(today, datetime.max.time())
                conditions.append(Appointment.scheduled_at.between(start_of_day, end_of_day))
            
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
            
            # Add relationships if requested (V2)
            if include_pet:
                query = query.options(selectinload(Appointment.pet))
            
            if include_owner:
                query = query.options(selectinload(Appointment.pet_owner))
            
            if include_veterinarian:
                query = query.options(selectinload(Appointment.veterinarian))
            
            if include_clinic:
                query = query.options(selectinload(Appointment.clinic))
            
            # Get total count
            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Apply sorting (V2 feature)
            if sort_by:
                if sort_by == "scheduled_at":
                    query = query.order_by(Appointment.scheduled_at)
                elif sort_by == "scheduled_at_desc":
                    query = query.order_by(Appointment.scheduled_at.desc())
                elif sort_by == "priority":
                    # Custom priority ordering
                    query = query.order_by(Appointment.priority.desc())
                elif sort_by == "status":
                    query = query.order_by(Appointment.status)
                elif sort_by == "created_at":
                    query = query.order_by(Appointment.created_at.desc())
                else:
                    query = query.order_by(Appointment.scheduled_at)
            else:
                query = query.order_by(Appointment.scheduled_at)
            
            # Apply pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            # Execute query
            result = await self.db.execute(query)
            appointments = result.scalars().all()
            
            return list(appointments), total
            
        except Exception as e:
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to list appointments: {str(e)}")

    async def get_appointment_by_id(
        self,
        appointment_id: uuid.UUID,
        include_pet: bool = False,
        include_owner: bool = False,
        include_veterinarian: bool = False,
        include_clinic: bool = False,
        **kwargs
    ) -> Appointment:
        """
        Get appointment by ID with optional related data.
        
        Args:
            appointment_id: Appointment UUID
            include_pet: Include pet information (V2)
            include_owner: Include owner information (V2)
            include_veterinarian: Include veterinarian information (V2)
            include_clinic: Include clinic information (V2)
            **kwargs: Additional parameters for future versions
            
        Returns:
            Appointment object
            
        Raises:
            NotFoundError: If appointment not found
        """
        try:
            query = select(Appointment).where(Appointment.id == appointment_id)
            
            # Add optional relationships based on version needs
            if include_pet:
                query = query.options(selectinload(Appointment.pet))
            
            if include_owner:
                query = query.options(selectinload(Appointment.pet_owner))
            
            if include_veterinarian:
                query = query.options(selectinload(Appointment.veterinarian))
            
            if include_clinic:
                query = query.options(selectinload(Appointment.clinic))
            
            result = await self.db.execute(query)
            appointment = result.scalar_one_or_none()
            
            if not appointment:
                raise NotFoundError(f"Appointment with id {appointment_id} not found")
            
            return appointment
            
        except Exception as e:
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to get appointment by id: {str(e)}")

    async def create_appointment(
        self,
        pet_id: uuid.UUID,
        pet_owner_id: uuid.UUID,
        veterinarian_id: uuid.UUID,
        clinic_id: uuid.UUID,
        appointment_type: Union[AppointmentType, str],
        scheduled_at: datetime,
        reason: str,
        duration_minutes: int = 30,
        priority: Union[AppointmentPriority, str] = AppointmentPriority.NORMAL,
        symptoms: Optional[str] = None,
        notes: Optional[str] = None,
        special_instructions: Optional[str] = None,
        services_requested: Optional[List[str]] = None,
        estimated_cost: Optional[float] = None,
        follow_up_required: bool = False,
        follow_up_date: Optional[datetime] = None,
        follow_up_notes: Optional[str] = None,
        **kwargs
    ) -> Appointment:
        """
        Create a new appointment.
        Supports dynamic parameters for different API versions.
        
        Args:
            pet_id: Pet UUID
            pet_owner_id: Pet owner UUID
            veterinarian_id: Veterinarian UUID
            clinic_id: Clinic UUID
            appointment_type: Type of appointment
            scheduled_at: Scheduled date and time
            reason: Reason for appointment
            duration_minutes: Duration in minutes
            priority: Appointment priority
            symptoms: Pet symptoms
            notes: Additional notes
            special_instructions: Special instructions
            services_requested: List of requested services
            estimated_cost: Estimated cost
            follow_up_required: Whether follow-up is required
            follow_up_date: Follow-up date
            follow_up_notes: Follow-up notes
            **kwargs: Additional parameters for future versions
            
        Returns:
            Created appointment object
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Handle enum parameters
            if isinstance(appointment_type, str):
                try:
                    appointment_type = AppointmentType(appointment_type)
                except ValueError:
                    raise ValidationError(f"Invalid appointment type: {appointment_type}")
            
            if isinstance(priority, str):
                try:
                    priority = AppointmentPriority(priority)
                except ValueError:
                    raise ValidationError(f"Invalid priority: {priority}")
            
            # Validate scheduled time is in the future
            if scheduled_at <= datetime.utcnow():
                raise ValidationError("Appointment must be scheduled in the future")
            
            # Create appointment data
            appointment_data = {
                "pet_id": pet_id,
                "pet_owner_id": pet_owner_id,
                "veterinarian_id": veterinarian_id,
                "clinic_id": clinic_id,
                "appointment_type": appointment_type,
                "scheduled_at": scheduled_at,
                "duration_minutes": duration_minutes,
                "priority": priority,
                "reason": reason.strip(),
                "symptoms": symptoms.strip() if symptoms else None,
                "notes": notes.strip() if notes else None,
                "special_instructions": special_instructions.strip() if special_instructions else None,
                "services_requested": services_requested,
                "estimated_cost": estimated_cost,
                "follow_up_required": follow_up_required,
                "follow_up_date": follow_up_date,
                "follow_up_notes": follow_up_notes.strip() if follow_up_notes else None,
                "status": AppointmentStatus.SCHEDULED
            }
            
            # Create new appointment
            new_appointment = Appointment(**appointment_data)
            
            self.db.add(new_appointment)
            await self.db.commit()
            await self.db.refresh(new_appointment)
            
            return new_appointment
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to create appointment: {str(e)}")

    async def update_appointment(
        self,
        appointment_id: uuid.UUID,
        scheduled_at: Optional[datetime] = None,
        appointment_type: Optional[Union[AppointmentType, str]] = None,
        priority: Optional[Union[AppointmentPriority, str]] = None,
        reason: Optional[str] = None,
        symptoms: Optional[str] = None,
        notes: Optional[str] = None,
        special_instructions: Optional[str] = None,
        services_requested: Optional[List[str]] = None,
        estimated_cost: Optional[float] = None,
        actual_cost: Optional[float] = None,
        follow_up_required: Optional[bool] = None,
        follow_up_date: Optional[datetime] = None,
        follow_up_notes: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        **kwargs
    ) -> Appointment:
        """
        Update appointment information.
        Supports dynamic parameters for different API versions.
        
        Returns:
            Updated appointment object
        """
        try:
            appointment = await self.get_appointment_by_id(appointment_id)
            
            # Update fields if provided
            if scheduled_at is not None:
                if scheduled_at <= datetime.utcnow():
                    raise ValidationError("Appointment must be scheduled in the future")
                appointment.scheduled_at = scheduled_at
            
            if appointment_type is not None:
                if isinstance(appointment_type, str):
                    try:
                        appointment_type = AppointmentType(appointment_type)
                    except ValueError:
                        raise ValidationError(f"Invalid appointment type: {appointment_type}")
                appointment.appointment_type = appointment_type
            
            if priority is not None:
                if isinstance(priority, str):
                    try:
                        priority = AppointmentPriority(priority)
                    except ValueError:
                        raise ValidationError(f"Invalid priority: {priority}")
                appointment.priority = priority
            
            if reason is not None:
                appointment.reason = reason.strip()
            if symptoms is not None:
                appointment.symptoms = symptoms.strip() if symptoms else None
            if notes is not None:
                appointment.notes = notes.strip() if notes else None
            if special_instructions is not None:
                appointment.special_instructions = special_instructions.strip() if special_instructions else None
            if services_requested is not None:
                appointment.services_requested = services_requested
            if estimated_cost is not None:
                appointment.estimated_cost = estimated_cost
            if actual_cost is not None:
                appointment.actual_cost = actual_cost
            if follow_up_required is not None:
                appointment.follow_up_required = follow_up_required
            if follow_up_date is not None:
                appointment.follow_up_date = follow_up_date
            if follow_up_notes is not None:
                appointment.follow_up_notes = follow_up_notes.strip() if follow_up_notes else None
            if duration_minutes is not None:
                appointment.duration_minutes = duration_minutes
            
            await self.db.commit()
            await self.db.refresh(appointment)
            
            return appointment
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to update appointment: {str(e)}")

    async def cancel_appointment(
        self,
        appointment_id: uuid.UUID,
        cancellation_reason: Optional[str] = None
    ) -> Appointment:
        """
        Cancel an appointment.
        
        Args:
            appointment_id: Appointment UUID
            cancellation_reason: Reason for cancellation
            
        Returns:
            Updated appointment object
        """
        try:
            appointment = await self.get_appointment_by_id(appointment_id)
            
            if not hasattr(appointment, "can_be_cancelled") or not appointment.can_be_cancelled:
                raise ValidationError(f"Appointment with status {appointment.status} cannot be cancelled")
            
            appointment.cancel(cancellation_reason)
            
            await self.db.commit()
            await self.db.refresh(appointment)
            
            return appointment
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to cancel appointment: {str(e)}")

    async def confirm_appointment(self, appointment_id: uuid.UUID) -> Appointment:
        """
        Confirm an appointment.
        
        Args:
            appointment_id: Appointment UUID
            
        Returns:
            Updated appointment object
        """
        try:
            appointment = await self.get_appointment_by_id(appointment_id)
            
            if appointment.status != AppointmentStatus.SCHEDULED:
                raise ValidationError(f"Only scheduled appointments can be confirmed")
            
            appointment.confirm()
            
            await self.db.commit()
            await self.db.refresh(appointment)
            
            return appointment
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to confirm appointment: {str(e)}")

    async def start_appointment(self, appointment_id: uuid.UUID) -> Appointment:
        """
        Start an appointment.
        
        Args:
            appointment_id: Appointment UUID
            
        Returns:
            Updated appointment object
        """
        try:
            appointment = await self.get_appointment_by_id(appointment_id)
            
            if appointment.status not in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]:
                raise ValidationError(f"Appointment with status {appointment.status} cannot be started")
            
            appointment.start()
            
            await self.db.commit()
            await self.db.refresh(appointment)
            
            return appointment
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to start appointment: {str(e)}")

    async def complete_appointment(
        self,
        appointment_id: uuid.UUID,
        actual_cost: Optional[float] = None
    ) -> Appointment:
        """
        Complete an appointment.
        
        Args:
            appointment_id: Appointment UUID
            actual_cost: Actual cost of the appointment
            
        Returns:
            Updated appointment object
        """
        try:
            appointment = await self.get_appointment_by_id(appointment_id)
            
            if appointment.status != AppointmentStatus.IN_PROGRESS:
                raise ValidationError(f"Only in-progress appointments can be completed")
            
            appointment.complete(actual_cost)
            
            await self.db.commit()
            await self.db.refresh(appointment)
            
            return appointment
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to complete appointment: {str(e)}")

    async def reschedule_appointment(
        self,
        appointment_id: uuid.UUID,
        new_scheduled_at: datetime
    ) -> Appointment:
        """
        Reschedule an appointment.
        
        Args:
            appointment_id: Appointment UUID
            new_scheduled_at: New scheduled date and time
            
        Returns:
            Updated appointment object
        """
        try:
            appointment = await self.get_appointment_by_id(appointment_id)
            
            if not appointment.can_be_rescheduled:
                raise ValidationError(f"Appointment with status {appointment.status} cannot be rescheduled")
            
            if new_scheduled_at <= datetime.utcnow():
                raise ValidationError("New appointment time must be in the future")
            
            # Update the scheduled time and status
            appointment.scheduled_at = new_scheduled_at
            appointment.status = AppointmentStatus.SCHEDULED  # Reset to scheduled
            appointment.confirmed_at = None  # Clear confirmation
            
            await self.db.commit()
            await self.db.refresh(appointment)
            
            return appointment
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to reschedule appointment: {str(e)}")

    async def delete_appointment(self, appointment_id: uuid.UUID) -> None:
        """
        Hard delete an appointment.
        
        Args:
            appointment_id: Appointment UUID
        """
        try:
            appointment = await self.get_appointment_by_id(appointment_id)
            
            await self.db.delete(appointment)
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to delete appointment: {str(e)}")

    async def get_appointments_by_pet(
        self,
        pet_id: uuid.UUID,
        include_past: bool = True,
        limit: Optional[int] = None,
        **kwargs
    ) -> List[Appointment]:
        """
        Get all appointments for a specific pet.
        
        Args:
            pet_id: Pet UUID
            include_past: Include past appointments
            limit: Limit number of results
            **kwargs: Additional parameters for future versions
            
        Returns:
            List of appointments
        """
        try:
            query = select(Appointment).where(Appointment.pet_id == pet_id)
            
            if not include_past:
                now = datetime.utcnow()
                query = query.where(Appointment.scheduled_at > now)
            
            query = query.order_by(Appointment.scheduled_at.desc())
            
            if limit:
                query = query.limit(limit)
            
            result = await self.db.execute(query)
            appointments = result.scalars().all()
            
            return list(appointments)
            
        except Exception as e:
            raise VetClinicException(f"Failed to get appointments by pet: {str(e)}")

    async def get_appointments_by_veterinarian(
        self,
        veterinarian_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        **kwargs
    ) -> List[Appointment]:
        """
        Get all appointments for a specific veterinarian.
        
        Args:
            veterinarian_id: Veterinarian UUID
            start_date: Filter by start date
            end_date: Filter by end date
            **kwargs: Additional parameters for future versions
            
        Returns:
            List of appointments
        """
        try:
            query = select(Appointment).where(Appointment.veterinarian_id == veterinarian_id)
            
            if start_date:
                start_datetime = datetime.combine(start_date, datetime.min.time())
                query = query.where(Appointment.scheduled_at >= start_datetime)
            
            if end_date:
                end_datetime = datetime.combine(end_date, datetime.max.time())
                query = query.where(Appointment.scheduled_at <= end_datetime)
            
            query = query.order_by(Appointment.scheduled_at)
            
            result = await self.db.execute(query)
            appointments = result.scalars().all()
            
            return list(appointments)
            
        except Exception as e:
            raise VetClinicException(f"Failed to get appointments by veterinarian: {str(e)}")

    async def get_available_slots(
        self,
        veterinarian_id: uuid.UUID,
        clinic_id: uuid.UUID,
        start_date: date,
        end_date: Optional[date] = None,
        **kwargs
    ) -> List[AppointmentSlot]:
        """
        Get available appointment slots.
        
        Args:
            veterinarian_id: Veterinarian UUID
            clinic_id: Clinic UUID
            start_date: Start date for slot search
            end_date: End date for slot search
            **kwargs: Additional parameters for future versions
            
        Returns:
            List of available appointment slots
        """
        try:
            if end_date is None:
                end_date = start_date + timedelta(days=7)  # Default to one week
            
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            query = select(AppointmentSlot).where(
                and_(
                    AppointmentSlot.veterinarian_id == veterinarian_id,
                    AppointmentSlot.clinic_id == clinic_id,
                    AppointmentSlot.start_time >= start_datetime,
                    AppointmentSlot.start_time <= end_datetime,
                    AppointmentSlot.is_available == True,
                    AppointmentSlot.is_blocked == False
                )
            ).order_by(AppointmentSlot.start_time)
            
            result = await self.db.execute(query)
            slots = result.scalars().all()
            
            # Filter out fully booked slots
            available_slots = [slot for slot in slots if not slot.is_fully_booked]
            
            return available_slots
            
        except Exception as e:
            raise VetClinicException(f"Failed to get available slots: {str(e)}")