"""
V1 Appointment API Endpoints

This module contains all appointment-related API endpoints for version 1.
Uses the shared AppointmentController with V1-specific schemas and response formatting.
"""

from typing import List, Optional
import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.appointment import Appointment, AppointmentStatus, AppointmentType, AppointmentPriority
from app.appointments.controller import AppointmentController
from app.app_helpers.auth_helpers import get_current_user, require_role
from app.app_helpers.dependency_helpers import get_controller
from app.api.schemas.v1.appointments import (
    AppointmentCreateV1,
    AppointmentUpdateV1,
    AppointmentResponseV1,
    AppointmentListRequestV1,
    AppointmentListResponseV1,
    AppointmentCancelRequestV1,
    AppointmentRescheduleRequestV1,
    AppointmentCompleteRequestV1,
    AppointmentCreateResponseV1,
    AppointmentUpdateResponseV1,
    AppointmentGetResponseV1,
    AppointmentCancelResponseV1,
    AppointmentConfirmResponseV1,
    AppointmentStartResponseV1,
    AppointmentCompleteResponseV1,
    AppointmentRescheduleResponseV1,
    AppointmentDeleteResponseV1,
    AppointmentOperationSuccessV1
)

router = APIRouter(prefix="/appointments", tags=["appointments-v1"])


# Helper function to convert Appointment model to V1 response
def appointment_to_v1_response(appointment: Appointment) -> AppointmentResponseV1:
    """Convert Appointment model to V1 response schema."""
    return AppointmentResponseV1(
        id=appointment.id,
        pet_id=appointment.pet_id,
        pet_owner_id=appointment.pet_owner_id,
        veterinarian_id=appointment.veterinarian_id,
        clinic_id=appointment.clinic_id,
        appointment_type=appointment.appointment_type,
        scheduled_at=appointment.scheduled_at,
        reason=appointment.reason,
        status=appointment.status,
        duration_minutes=appointment.duration_minutes,
        priority=appointment.priority,
        symptoms=appointment.symptoms,
        notes=appointment.notes,
        special_instructions=appointment.special_instructions,
        estimated_cost=appointment.estimated_cost,
        actual_cost=appointment.actual_cost,
        follow_up_required=appointment.follow_up_required,
        follow_up_date=appointment.follow_up_date,
        follow_up_notes=appointment.follow_up_notes,
        confirmed_at=appointment.confirmed_at,
        started_at=appointment.started_at,
        completed_at=appointment.completed_at,
        cancelled_at=appointment.cancelled_at,
        cancellation_reason=appointment.cancellation_reason,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at
    )


@router.get("/", response_model=dict)
async def list_appointments(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    pet_id: Optional[uuid.UUID] = Query(None, description="Filter by pet ID"),
    pet_owner_id: Optional[uuid.UUID] = Query(None, description="Filter by pet owner ID"),
    veterinarian_id: Optional[uuid.UUID] = Query(None, description="Filter by veterinarian ID"),
    clinic_id: Optional[uuid.UUID] = Query(None, description="Filter by clinic ID"),
    status: Optional[AppointmentStatus] = Query(None, description="Filter by status"),
    appointment_type: Optional[AppointmentType] = Query(None, description="Filter by type"),
    priority: Optional[AppointmentPriority] = Query(None, description="Filter by priority"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    upcoming_only: bool = Query(False, description="Show only upcoming appointments"),
    today_only: bool = Query(False, description="Show only today's appointments"),
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    List appointments with pagination and filtering.
    
    V1 provides basic appointment listing with standard filters.
    """
    appointments, total = await controller.list_appointments(
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
        # V1 doesn't include related data
        include_pet=False,
        include_owner=False,
        include_veterinarian=False,
        include_clinic=False
    )
    
    # Convert to V1 response format
    appointment_responses = [appointment_to_v1_response(appointment) for appointment in appointments]
    
    # Calculate pagination metadata
    total_pages = (total + per_page - 1) // per_page
    
    return {
        "success": True,
        "data": {
            "appointments": appointment_responses,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        },
        "message": "Appointments retrieved successfully",
        "version": "v1"
    }


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreateV1,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Create a new appointment.
    
    V1 provides basic appointment creation functionality.
    """
    appointment = await controller.create_appointment(
        appointment_data=appointment_data,
        created_by=current_user.id
    )
    
    return {
        "success": True,
        "data": appointment_to_v1_response(appointment),
        "message": "Appointment created successfully",
        "version": "v1"
    }


@router.get("/{appointment_id}", response_model=dict)
async def get_appointment(
    appointment_id: uuid.UUID,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Get appointment by ID.
    
    V1 provides basic appointment details without related data.
    """
    appointment = await controller.get_appointment_by_id(
        appointment_id=appointment_id,
        # V1 doesn't include related data
        include_pet=False,
        include_owner=False,
        include_veterinarian=False,
        include_clinic=False
    )
    
    return {
        "success": True,
        "data": appointment_to_v1_response(appointment),
        "message": "Appointment retrieved successfully",
        "version": "v1"
    }


@router.put("/{appointment_id}", response_model=dict)
async def update_appointment(
    appointment_id: uuid.UUID,
    appointment_data: AppointmentUpdateV1,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Update appointment information.
    
    V1 provides basic appointment update functionality.
    """
    appointment = await controller.update_appointment(
        appointment_id=appointment_id,
        appointment_data=appointment_data,
        updated_by=current_user.id
    )
    
    return {
        "success": True,
        "data": appointment_to_v1_response(appointment),
        "message": "Appointment updated successfully",
        "version": "v1"
    }


@router.post("/{appointment_id}/cancel", response_model=dict)
async def cancel_appointment(
    appointment_id: uuid.UUID,
    cancel_data: AppointmentCancelRequestV1,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Cancel an appointment.
    
    V1 provides basic appointment cancellation.
    """
    appointment = await controller.cancel_appointment(
        appointment_id=appointment_id,
        cancellation_reason=cancel_data.cancellation_reason,
        cancelled_by=current_user.id
    )
    
    return {
        "success": True,
        "data": appointment_to_v1_response(appointment),
        "message": "Appointment cancelled successfully",
        "version": "v1"
    }


@router.post("/{appointment_id}/confirm", response_model=dict)
async def confirm_appointment(
    appointment_id: uuid.UUID,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Confirm an appointment.
    
    V1 provides basic appointment confirmation.
    """
    appointment = await controller.confirm_appointment(
        appointment_id=appointment_id,
        confirmed_by=current_user.id
    )
    
    return {
        "success": True,
        "data": appointment_to_v1_response(appointment),
        "message": "Appointment confirmed successfully",
        "version": "v1"
    }


@router.post("/{appointment_id}/start", response_model=dict)
async def start_appointment(
    appointment_id: uuid.UUID,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Start an appointment.
    
    V1 provides basic appointment start functionality.
    """
    appointment = await controller.start_appointment(
        appointment_id=appointment_id,
        started_by=current_user.id
    )
    
    return {
        "success": True,
        "data": appointment_to_v1_response(appointment),
        "message": "Appointment started successfully",
        "version": "v1"
    }


@router.post("/{appointment_id}/complete", response_model=dict)
async def complete_appointment(
    appointment_id: uuid.UUID,
    complete_data: AppointmentCompleteRequestV1,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Complete an appointment.
    
    V1 provides basic appointment completion.
    """
    appointment = await controller.complete_appointment(
        appointment_id=appointment_id,
        actual_cost=complete_data.actual_cost,
        completed_by=current_user.id
    )
    
    return {
        "success": True,
        "data": appointment_to_v1_response(appointment),
        "message": "Appointment completed successfully",
        "version": "v1"
    }


@router.post("/{appointment_id}/reschedule", response_model=dict)
async def reschedule_appointment(
    appointment_id: uuid.UUID,
    reschedule_data: AppointmentRescheduleRequestV1,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Reschedule an appointment.
    
    V1 provides basic appointment rescheduling.
    """
    appointment = await controller.reschedule_appointment(
        appointment_id=appointment_id,
        new_scheduled_at=reschedule_data.new_scheduled_at,
        rescheduled_by=current_user.id
    )
    
    return {
        "success": True,
        "data": appointment_to_v1_response(appointment),
        "message": "Appointment rescheduled successfully",
        "version": "v1"
    }


@router.delete("/{appointment_id}", response_model=dict)
async def delete_appointment(
    appointment_id: uuid.UUID,
    current_user = Depends(get_current_user),
    controller: AppointmentController = Depends(get_controller(AppointmentController))
):
    """
    Delete an appointment.
    
    V1 provides basic appointment deletion.
    """
    result = await controller.delete_appointment(
        appointment_id=appointment_id,
        deleted_by=current_user.id
    )
    
    return {
        "success": True,
        "data": {
            "appointment_id": appointment_id,
            "message": result["message"]
        },
        "message": "Appointment deleted successfully",
        "version": "v1"
    }