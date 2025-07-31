"""
Version-agnostic Appointment Controller

This controller handles HTTP request processing and business logic orchestration
for appointment-related operations across all API versions. It accepts Union types for
different API version schemas and returns raw data that can be formatted by any version.
"""

from typing import List, Optional, Union, Dict, Any, Tuple
from datetime import datetime, date
import uuid
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.exceptions import VetClinicException, NotFoundError, ValidationError
from app.models.appointment import Appointment, AppointmentStatus, AppointmentType, AppointmentPriority
from .services import AppointmentService
from ..app_helpers import validate_pagination_params


class AppointmentController:
    """Version-agnostic controller for appointment-related operations."""

    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.service = AppointmentService(db)
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
        Handles business rules and validation before delegating to service.
        """
        try:
            # Validate pagination parameters
            page, page_size = validate_pagination_params(page=page, size=per_page)
            
            # Delegate to service
            appointments, total = await self.service.list_appointments(
                page=page,
                per_page=per_page,
                pet_id=pet_id,
                pet_owner_id=pet_owner_id,
                veterinarian_id=veterinarian_id,
                clinic_id=clinic_id,
                status=status,
                appointment_type=appointment_type,
                priority=priority,
                start_date=start_date,
                end_date=end_date,
                upcoming_only=upcoming_only,
                today_only=today_only,
                include_pet=include_pet,
                include_owner=include_owner,
                include_veterinarian=include_veterinarian,
                include_clinic=include_clinic,
                sort_by=sort_by,
                **kwargs
            )
            
            return appointments, total
            
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

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
        """
        try:
            appointment = await self.service.get_appointment_by_id(
                appointment_id=appointment_id,
                include_pet=include_pet,
                include_owner=include_owner,
                include_veterinarian=include_veterinarian,
                include_clinic=include_clinic,
                **kwargs
            )
            return appointment
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def create_appointment(
        self,
        appointment_data: Union[BaseModel, Dict[str, Any]],
        created_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Appointment:
        """
        Create a new appointment.
        Accepts Union[AppointmentCreateV1, AppointmentCreateV2] for create operations.
        """
        try:
            # Extract data from schema or dict
            if isinstance(appointment_data, BaseModel):
                data = appointment_data.model_dump(exclude_unset=True)
            else:
                data = appointment_data
            
            # Business rule validation
            await self._validate_appointment_creation(data, created_by)
            
            # Extract common fields
            pet_id = data.get("pet_id")
            pet_owner_id = data.get("pet_owner_id")
            veterinarian_id = data.get("veterinarian_id")
            clinic_id = data.get("clinic_id")
            appointment_type = data.get("appointment_type")
            scheduled_at = data.get("scheduled_at")
            reason = data.get("reason")
            duration_minutes = data.get("duration_minutes", 30)
            priority = data.get("priority", AppointmentPriority.NORMAL)
            symptoms = data.get("symptoms")
            notes = data.get("notes")
            special_instructions = data.get("special_instructions")
            services_requested = data.get("services_requested")
            estimated_cost = data.get("estimated_cost")
            follow_up_required = data.get("follow_up_required", False)
            follow_up_date = data.get("follow_up_date")
            follow_up_notes = data.get("follow_up_notes")
            
            # Create appointment
            appointment = await self.service.create_appointment(
                pet_id=pet_id,
                pet_owner_id=pet_owner_id,
                veterinarian_id=veterinarian_id,
                clinic_id=clinic_id,
                appointment_type=appointment_type,
                scheduled_at=scheduled_at,
                reason=reason,
                duration_minutes=duration_minutes,
                priority=priority,
                symptoms=symptoms,
                notes=notes,
                special_instructions=special_instructions,
                services_requested=services_requested,
                estimated_cost=estimated_cost,
                follow_up_required=follow_up_required,
                follow_up_date=follow_up_date,
                follow_up_notes=follow_up_notes,
                **kwargs
            )
            
            return appointment
            
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def update_appointment(
        self,
        appointment_id: uuid.UUID,
        appointment_data: Union[BaseModel, Dict[str, Any]],
        updated_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Appointment:
        """
        Update appointment information.
        Accepts Union[AppointmentUpdateV1, AppointmentUpdateV2] for update operations.
        """
        try:
            # Extract data from schema or dict
            if isinstance(appointment_data, BaseModel):
                data = appointment_data.model_dump(exclude_unset=True)
            else:
                data = appointment_data
            
            # Business rule validation
            await self._validate_appointment_update(appointment_id, data, updated_by)
            
            # Update appointment
            appointment = await self.service.update_appointment(appointment_id=appointment_id, **data, **kwargs)
            
            return appointment
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def cancel_appointment(
        self,
        appointment_id: uuid.UUID,
        cancellation_reason: Optional[str] = None,
        cancelled_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Appointment:
        """Cancel an appointment."""
        try:
            # Business rule validation
            await self._validate_appointment_cancellation(appointment_id, cancelled_by)
            
            appointment = await self.service.cancel_appointment(appointment_id, cancellation_reason)
            return appointment
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def confirm_appointment(
        self,
        appointment_id: uuid.UUID,
        confirmed_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Appointment:
        """Confirm an appointment."""
        try:
            # Business rule validation
            await self._validate_appointment_confirmation(appointment_id, confirmed_by)
            
            appointment = await self.service.confirm_appointment(appointment_id)
            return appointment
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def start_appointment(
        self,
        appointment_id: uuid.UUID,
        started_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Appointment:
        """Start an appointment."""
        try:
            appointment = await self.service.start_appointment(appointment_id)
            return appointment
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def complete_appointment(
        self,
        appointment_id: uuid.UUID,
        actual_cost: Optional[float] = None,
        completed_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Appointment:
        """Complete an appointment."""
        try:
            appointment = await self.service.complete_appointment(appointment_id, actual_cost)
            return appointment
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def reschedule_appointment(
        self,
        appointment_id: uuid.UUID,
        new_scheduled_at: datetime,
        rescheduled_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Appointment:
        """Reschedule an appointment."""
        try:
            # Business rule validation
            await self._validate_appointment_reschedule(appointment_id, new_scheduled_at, rescheduled_by)
            
            appointment = await self.service.reschedule_appointment(appointment_id, new_scheduled_at)
            return appointment
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    async def delete_appointment(
        self,
        appointment_id: uuid.UUID,
        deleted_by: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Delete an appointment."""
        try:
            # Business rule validation
            await self._validate_appointment_deletion(appointment_id, deleted_by)
            
            await self.service.delete_appointment(appointment_id)
            
            return {"success": True, "message": "Appointment deleted successfully"}
            
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except VetClinicException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

    # Private helper methods for business rule validation

    async def _validate_appointment_creation(
        self,
        data: Dict[str, Any],
        created_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for appointment creation."""
        # Validate required fields
        required_fields = ["pet_id", "pet_owner_id", "veterinarian_id", "clinic_id", "appointment_type", "scheduled_at", "reason"]
        for field in required_fields:
            if not data.get(field):
                raise ValidationError(f"{field} is required")
        
        # Validate appointment type
        appointment_type = data.get("appointment_type")
        if isinstance(appointment_type, str):
            try:
                AppointmentType(appointment_type)
            except ValueError:
                raise ValidationError(f"Invalid appointment type: {appointment_type}")
        
        # Validate scheduled time is in the future
        scheduled_at = data.get("scheduled_at")
        if isinstance(scheduled_at, datetime) and scheduled_at <= datetime.utcnow():
            raise ValidationError("Appointment must be scheduled in the future")

    async def _validate_appointment_update(
        self,
        appointment_id: uuid.UUID,
        data: Dict[str, Any],
        updated_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for appointment updates."""
        # Validate scheduled time if provided
        scheduled_at = data.get("scheduled_at")
        if scheduled_at and isinstance(scheduled_at, datetime) and scheduled_at <= datetime.utcnow():
            raise ValidationError("Appointment must be scheduled in the future")

    async def _validate_appointment_cancellation(
        self,
        appointment_id: uuid.UUID,
        cancelled_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for appointment cancellation."""
        # Check if appointment exists and can be cancelled
        appointment = await self.service.get_appointment_by_id(appointment_id)
        if not appointment.can_be_cancelled:
            raise ValidationError(f"Appointment with status {appointment.status} cannot be cancelled")

    async def _validate_appointment_confirmation(
        self,
        appointment_id: uuid.UUID,
        confirmed_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for appointment confirmation."""
        # Check if appointment exists and can be confirmed
        appointment = await self.service.get_appointment_by_id(appointment_id)
        if appointment.status != AppointmentStatus.SCHEDULED:
            raise ValidationError("Only scheduled appointments can be confirmed")

    async def _validate_appointment_reschedule(
        self,
        appointment_id: uuid.UUID,
        new_scheduled_at: datetime,
        rescheduled_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for appointment rescheduling."""
        # Check if appointment exists and can be rescheduled
        appointment = await self.service.get_appointment_by_id(appointment_id)
        if not appointment.can_be_rescheduled:
            raise ValidationError(f"Appointment with status {appointment.status} cannot be rescheduled")
        
        # Validate new scheduled time is in the future
        if new_scheduled_at <= datetime.utcnow():
            raise ValidationError("New appointment time must be in the future")

    async def _validate_appointment_deletion(
        self,
        appointment_id: uuid.UUID,
        deleted_by: Optional[uuid.UUID]
    ) -> None:
        """Validate business rules for appointment deletion."""
        # Check if appointment exists
        await self.service.get_appointment_by_id(appointment_id)
        
        # Additional business rules can be added here
        pass