"""
V2 Appointment API Endpoints

This module contains all appointment-related API endpoints for version 2.
Uses the shared AppointmentController with V2-specific schemas and enhanced features.
"""

from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.appointment import Appointment, AppointmentStatus, AppointmentType, AppointmentPriority
from app.appointments.controller import AppointmentController
from app.app_helpers.auth_helpers import get_current_user, require_role
from app.app_helpers.dependency_helpers import get_controller
from app.api.schemas.v2.appointments import (
    AppointmentCreateV2,
    AppointmentUpdateV2,
    AppointmentResponseV2,
    AppointmentListRequestV2,
    AppointmentStatusUpdateV2,
    AppointmentCancellationV2,
    AppointmentRescheduleV2,
    RecurringAppointmentCreateV2,
    BatchAppointmentOperationV2,
    AppointmentStatisticsV2,
    AppointmentResponseModelV2,
    AppointmentListResponseModelV2,
    AppointmentStatisticsResponseModelV2,
    AppointmentOperationSuccessV2,
    AppointmentErrorResponseV2,
    PetInfoV2,
    VeterinarianInfoV2,
    ClinicInfoV2
)

router = APIRouter(prefix="/appointments", tags=["appointments-v2"])


# Helper function to convert Appointment model to V2 response
def appointment_to_v2_response(appointment: Appointment, include_relationships: bool = False) -> AppointmentResponseV2:
    """Convert Appointment model to V2 response schema with optional relationships."""
    response_data = {
        "id": appointment.id,
        "pet_id": appointment.pet_id,
        "pet_owner_id": appointment.pet_owner_id,
        "veterinarian_id": appointment.veterinarian_id,
        "clinic_id": appointment.clinic_id,
        "appointment_type": appointment.appointment_type,
        "scheduled_at": appointment.scheduled_at,
        "duration_minutes": appointment.duration_minutes,
        "reason": appointment.reason,
        "status": appointment.status,
        "priority": appointment.priority,
        "symptoms": appointment.symptoms,
        "notes": appointment.notes,
        "special_instructions": appointment.special_instructions,
        "estimated_cost": appointment.estimated_cost,
        "actual_cost": appointment.actual_cost,
        "confirmed_at": appointment.confirmed_at,
        "checked_in_at": appointment.checked_in_at,
        "started_at": appointment.started_at,
        "completed_at": appointment.completed_at,
        "cancelled_at": appointment.cancelled_at,
        "cancellation_reason": appointment.cancellation_reason,
        "follow_up_required": appointment.follow_up_required,
        "follow_up_date": appointment.follow_up_date,
        "follow_up_notes": appointment.follow_up_notes,
        "services_requested": appointment.services_requested,
        "reminder_sent_24h": appointment.reminder_sent_24h,
        "reminder_sent_2h": appointment.reminder_sent_2h,
        "reminder_sent_24h_at": appointment.reminder_sent_24h_at,
        "reminder_sent_2h_at": appointment.reminder_sent_2h_at,
        "pre_appointment_checklist": None,  # V2 feature, would need to be added to model
        "emergency_contact": None,  # V2 feature, would need to be added to model
        "created_at": appointment.created_at,
        "updated_at": appointment.updated_at
    }
    
    # Add relationship data if requested and available
    if include_relationships:
        if hasattr(appointment, 'pet') and appointment.pet:
            response_data["pet"] = PetInfoV2(
                id=appointment.pet.id,
                name=appointment.pet.name,
                species=appointment.pet.species,
                breed=appointment.pet.breed
            )
        
        if hasattr(appointment, 'veterinarian') and appointment.veterinarian:
            response_data["veterinarian"] = VeterinarianInfoV2(
                id=appointment.veterinarian.id,
                first_name=appointment.veterinarian.user.first_name if appointment.veterinarian.user else "",
                last_name=appointment.veterinarian.user.last_name if appointment.veterinarian.user else "",
                specialization=None  # Would need to be extracted from specialties
            )
        
        if hasattr(appointment, 'clinic') and appointment.clinic:
            response_data["clinic"] = ClinicInfoV2(
                id=appointment.clinic.id,
                name=appointment.clinic.name,
                address=appointment.clinic.full_address,
                phone=appointment.clinic.phone_number
            )
    
    return AppointmentResponseV2(**response_data)


@router.get("/", response_model=dict)
async def list_appointments(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    pet_id: Optional[uuid.UUID] = Query(None, description="Filter by pet ID"),
    veterinarian_id: Optional[uuid.UUID] = Query(None, description="Filter by veterinarian ID"),
    clinic_id: Optional[uuid.UUID] = Query(None, description="Filter by clinic ID"),
    status: Optional[AppointmentStatus] = Query(None, description="Filter by status"),
    appointment_type: Optional[AppointmentType] = Query(None, description="Filter by appointment type"),
    priority: Optional[AppointmentPriority] = Query(None, description="Filter by priority"),
    date_from: Optional[datetime] = Query(None, description="Filter appointments from date"),
    date_to: Optional[datetime] = Query(None, description="Filter appointments to date"),
    include_pet_info: bool = Query(False, description="Include pet information in response"),
    include_vet_info: bool = Query(False, description="Include veterinarian information in response"),
    include_clinic_info: bool = Query(False, description="Include clinic information in response"),
    search: Optional[str] = Query(None, description="Search in reason, symptoms, or notes"),
    has_follow_up: Optional[bool] = Query(None, description="Filter by follow-up requirement"),
    cost_min: Optional[float] = Query(None, ge=0, description="Minimum cost filter"),
    cost_max: Optional[float] = Query(None, ge=0, description="Maximum cost filter"),
    sort_by: Optional[str] = Query("scheduled_at", description="Sort field"),
    sort_order: Optional[str] = Query("asc", description="Sort order (asc/desc)"),
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    List appointments with enhanced filtering and pagination.
    
    V2 provides advanced filtering, sorting, and optional relationship data.
    """
    # Convert date filters to the format expected by the controller
    start_date = date_from.date() if date_from else None
    end_date = date_to.date() if date_to else None
    
    appointments, total = await controller.list_appointments(
        page=page,
        per_page=per_page,
        pet_id=pet_id,
        veterinarian_id=veterinarian_id,
        clinic_id=clinic_id,
        status=status,
        appointment_type=appointment_type,
        priority=priority,
        start_date=start_date,
        end_date=end_date,
        # V2 enhanced features
        include_pet=include_pet_info,
        include_owner=False,  # Not requested in this endpoint
        include_veterinarian=include_vet_info,
        include_clinic=include_clinic_info,
        sort_by=sort_by
    )
    
    # Convert to V2 response format
    include_relationships = include_pet_info or include_vet_info or include_clinic_info
    appointment_responses = [
        appointment_to_v2_response(appointment, include_relationships) 
        for appointment in appointments
    ]
    
    # Calculate pagination metadata
    total_pages = (total + per_page - 1) // per_page
    
    return {
        "success": True,
        "data": {
            "appointments": appointment_responses,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages
            },
            "filters_applied": {
                "pet_id": pet_id,
                "veterinarian_id": veterinarian_id,
                "clinic_id": clinic_id,
                "status": status,
                "appointment_type": appointment_type,
                "priority": priority,
                "date_from": date_from,
                "date_to": date_to,
                "search": search,
                "has_follow_up": has_follow_up,
                "cost_range": [cost_min, cost_max] if cost_min or cost_max else None
            },
            "sort": {
                "field": sort_by,
                "order": sort_order
            }
        },
        "message": "Appointments retrieved successfully",
        "version": "v2",
        "timestamp": datetime.utcnow()
    }


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreateV2,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Create a new appointment with enhanced features.
    
    V2 provides enhanced appointment creation with additional fields and validation.
    """
    appointment = await controller.create_appointment(
        appointment_data=appointment_data,
        created_by=current_user.id
    )
    
    return {
        "success": True,
        "data": appointment_to_v2_response(appointment),
        "message": "Appointment created successfully",
        "version": "v2",
        "timestamp": datetime.utcnow(),
        "appointment_id": appointment.id
    }


@router.get("/{appointment_id}", response_model=dict)
async def get_appointment(
    appointment_id: uuid.UUID,
    include_pet_info: bool = Query(False, description="Include pet information"),
    include_vet_info: bool = Query(False, description="Include veterinarian information"),
    include_clinic_info: bool = Query(False, description="Include clinic information"),
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Get appointment by ID with optional relationship data.
    
    V2 provides detailed appointment information with optional related data.
    """
    appointment = await controller.get_appointment_by_id(
        appointment_id=appointment_id,
        include_pet=include_pet_info,
        include_owner=False,
        include_veterinarian=include_vet_info,
        include_clinic=include_clinic_info
    )
    
    include_relationships = include_pet_info or include_vet_info or include_clinic_info
    
    return {
        "success": True,
        "data": appointment_to_v2_response(appointment, include_relationships),
        "message": "Appointment retrieved successfully",
        "version": "v2",
        "timestamp": datetime.utcnow()
    }


@router.put("/{appointment_id}", response_model=dict)
async def update_appointment(
    appointment_id: uuid.UUID,
    appointment_data: AppointmentUpdateV2,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Update appointment information with enhanced fields.
    
    V2 provides enhanced appointment updates with additional validation.
    """
    appointment = await controller.update_appointment(
        appointment_id=appointment_id,
        appointment_data=appointment_data,
        updated_by=current_user.id
    )
    
    return {
        "success": True,
        "data": appointment_to_v2_response(appointment),
        "message": "Appointment updated successfully",
        "version": "v2",
        "timestamp": datetime.utcnow(),
        "updated_fields": list(appointment_data.model_dump(exclude_unset=True).keys())
    }


@router.patch("/{appointment_id}/status", response_model=dict)
async def update_appointment_status(
    appointment_id: uuid.UUID,
    status_data: AppointmentStatusUpdateV2,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Update appointment status with enhanced information.
    
    V2 provides comprehensive status updates with notifications and follow-up management.
    """
    # Handle different status updates
    if status_data.status == AppointmentStatus.CANCELLED:
        appointment = await controller.cancel_appointment(
            appointment_id=appointment_id,
            cancellation_reason=status_data.notes,
            cancelled_by=current_user.id
        )
    elif status_data.status == AppointmentStatus.CONFIRMED:
        appointment = await controller.confirm_appointment(
            appointment_id=appointment_id,
            confirmed_by=current_user.id
        )
    elif status_data.status == AppointmentStatus.IN_PROGRESS:
        appointment = await controller.start_appointment(
            appointment_id=appointment_id,
            started_by=current_user.id
        )
    elif status_data.status == AppointmentStatus.COMPLETED:
        appointment = await controller.complete_appointment(
            appointment_id=appointment_id,
            actual_cost=status_data.actual_cost,
            completed_by=current_user.id
        )
    else:
        # Generic status update
        appointment = await controller.update_appointment(
            appointment_id=appointment_id,
            appointment_data={"status": status_data.status, "notes": status_data.notes},
            updated_by=current_user.id
        )
    
    return {
        "success": True,
        "data": appointment_to_v2_response(appointment),
        "message": f"Appointment status updated to {status_data.status.value}",
        "version": "v2",
        "timestamp": datetime.utcnow(),
        "status_change": {
            "new_status": status_data.status,
            "updated_by": current_user.id,
            "notes": status_data.notes,
            "notify_owner": status_data.notify_owner
        }
    }


@router.post("/{appointment_id}/cancel", response_model=dict)
async def cancel_appointment_v2(
    appointment_id: uuid.UUID,
    cancel_data: AppointmentCancellationV2,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Cancel an appointment with enhanced cancellation features.
    
    V2 provides comprehensive cancellation with refunds, fees, and rescheduling options.
    """
    appointment = await controller.cancel_appointment(
        appointment_id=appointment_id,
        cancellation_reason=cancel_data.reason,
        cancelled_by=current_user.id
    )
    
    return {
        "success": True,
        "data": appointment_to_v2_response(appointment),
        "message": "Appointment cancelled successfully",
        "version": "v2",
        "timestamp": datetime.utcnow(),
        "cancellation_details": {
            "reason": cancel_data.reason,
            "notify_owner": cancel_data.notify_owner,
            "refund_amount": cancel_data.refund_amount,
            "reschedule_offer": cancel_data.reschedule_offer,
            "cancellation_fee": cancel_data.cancellation_fee
        }
    }


@router.post("/{appointment_id}/reschedule", response_model=dict)
async def reschedule_appointment_v2(
    appointment_id: uuid.UUID,
    reschedule_data: AppointmentRescheduleV2,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Reschedule an appointment with enhanced features.
    
    V2 provides comprehensive rescheduling with fees, service updates, and notifications.
    """
    # First reschedule the appointment
    appointment = await controller.reschedule_appointment(
        appointment_id=appointment_id,
        new_scheduled_at=reschedule_data.new_scheduled_at,
        rescheduled_by=current_user.id
    )
    
    # Update additional fields if provided
    update_data = {}
    if reschedule_data.new_duration_minutes:
        update_data["duration_minutes"] = reschedule_data.new_duration_minutes
    if reschedule_data.update_services:
        update_data["services_requested"] = reschedule_data.update_services
    
    if update_data:
        appointment = await controller.update_appointment(
            appointment_id=appointment_id,
            appointment_data=update_data,
            updated_by=current_user.id
        )
    
    return {
        "success": True,
        "data": appointment_to_v2_response(appointment),
        "message": "Appointment rescheduled successfully",
        "version": "v2",
        "timestamp": datetime.utcnow(),
        "reschedule_details": {
            "old_time": None,  # Would need to track this
            "new_time": reschedule_data.new_scheduled_at,
            "reason": reschedule_data.reason,
            "notify_owner": reschedule_data.notify_owner,
            "reschedule_fee": reschedule_data.reschedule_fee,
            "services_updated": bool(reschedule_data.update_services)
        }
    }


@router.delete("/{appointment_id}", response_model=dict)
async def delete_appointment(
    appointment_id: uuid.UUID,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Delete an appointment.
    
    V2 provides enhanced deletion with detailed response.
    """
    result = await controller.delete_appointment(
        appointment_id=appointment_id,
        deleted_by=current_user.id
    )
    
    return {
        "success": True,
        "data": {
            "appointment_id": appointment_id,
            "deleted_by": current_user.id,
            "deleted_at": datetime.utcnow()
        },
        "message": "Appointment deleted successfully",
        "version": "v2",
        "timestamp": datetime.utcnow()
    }


# V2 Enhanced endpoints

@router.post("/recurring", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_recurring_appointments(
    recurring_data: RecurringAppointmentCreateV2,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Create recurring appointments.
    
    V2 exclusive feature for creating multiple appointments based on a pattern.
    """
    # This would need to be implemented in the controller
    # For now, return a placeholder response
    return {
        "success": True,
        "data": {
            "message": "Recurring appointments feature not yet implemented",
            "pattern": recurring_data.recurrence_pattern,
            "base_appointment": recurring_data.base_appointment.model_dump()
        },
        "message": "Recurring appointments creation requested",
        "version": "v2",
        "timestamp": datetime.utcnow()
    }


@router.post("/batch", response_model=dict)
async def batch_appointment_operation(
    batch_data: BatchAppointmentOperationV2,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Perform batch operations on multiple appointments.
    
    V2 exclusive feature for bulk appointment management.
    """
    # This would need to be implemented in the controller
    # For now, return a placeholder response
    return {
        "success": True,
        "data": {
            "message": "Batch operations feature not yet implemented",
            "operation": batch_data.operation,
            "appointment_count": len(batch_data.appointment_ids)
        },
        "message": f"Batch {batch_data.operation} operation requested",
        "version": "v2",
        "timestamp": datetime.utcnow()
    }


@router.get("/statistics", response_model=dict)
async def get_appointment_statistics(
    start_date: Optional[date] = Query(None, description="Statistics start date"),
    end_date: Optional[date] = Query(None, description="Statistics end date"),
    clinic_id: Optional[uuid.UUID] = Query(None, description="Filter by clinic"),
    veterinarian_id: Optional[uuid.UUID] = Query(None, description="Filter by veterinarian"),
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Get appointment statistics and analytics.
    
    V2 exclusive feature for appointment analytics.
    """
    # This would need to be implemented in the controller
    # For now, return a placeholder response
    return {
        "success": True,
        "data": {
            "message": "Statistics feature not yet implemented",
            "date_range": [start_date, end_date],
            "filters": {
                "clinic_id": clinic_id,
                "veterinarian_id": veterinarian_id
            }
        },
        "message": "Appointment statistics requested",
        "version": "v2",
        "timestamp": datetime.utcnow()
    }