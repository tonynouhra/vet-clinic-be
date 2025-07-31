"""
V1 Appointment Schemas - Basic appointment management schemas for API version 1.

These schemas define the structure of appointment-related requests and responses
for V1 endpoints with basic appointment functionality.
"""

from typing import Optional, List
from datetime import datetime, date
import uuid
from pydantic import Field

from app.models.appointment import AppointmentStatus, AppointmentType, AppointmentPriority
from app.api.schemas.validators import (
    non_empty_string_field,
    positive_float_field,
    positive_int_field
)
from . import (
    BaseSchema,
    TimestampMixin,
    IDMixin,
    PaginationRequest,
    create_v1_response,
    create_v1_list_response
)


# Base Appointment schemas
class AppointmentBaseV1(BaseSchema):
    """Base appointment schema with common fields for V1."""
    pet_id: uuid.UUID = Field(description="Pet ID")
    pet_owner_id: uuid.UUID = Field(description="Pet owner ID")
    veterinarian_id: uuid.UUID = Field(description="Veterinarian ID")
    clinic_id: uuid.UUID = Field(description="Clinic ID")
    appointment_type: AppointmentType = Field(description="Type of appointment")
    scheduled_at: datetime = Field(description="Scheduled date and time")
    reason: str = non_empty_string_field("Reason for appointment")


class AppointmentCreateV1(AppointmentBaseV1):
    """Schema for creating an appointment in V1."""
    duration_minutes: int = Field(30, description="Duration in minutes", ge=15, le=480)
    priority: AppointmentPriority = Field(AppointmentPriority.NORMAL, description="Priority level")
    symptoms: Optional[str] = Field(None, description="Pet symptoms")
    notes: Optional[str] = Field(None, description="Additional notes")
    special_instructions: Optional[str] = Field(None, description="Special instructions")
    estimated_cost: Optional[float] = positive_float_field("Estimated cost", default=None)
    follow_up_required: bool = Field(False, description="Whether follow-up is required")
    follow_up_date: Optional[datetime] = Field(None, description="Follow-up date if required")
    follow_up_notes: Optional[str] = Field(None, description="Follow-up notes")


class AppointmentUpdateV1(BaseSchema):
    """Schema for updating an appointment in V1."""
    scheduled_at: Optional[datetime] = Field(None, description="New scheduled date and time")
    appointment_type: Optional[AppointmentType] = Field(None, description="New appointment type")
    priority: Optional[AppointmentPriority] = Field(None, description="New priority level")
    reason: Optional[str] = Field(None, description="New reason", min_length=1)
    symptoms: Optional[str] = Field(None, description="New symptoms")
    notes: Optional[str] = Field(None, description="New notes")
    special_instructions: Optional[str] = Field(None, description="New special instructions")
    estimated_cost: Optional[float] = positive_float_field("New estimated cost", default=None)
    follow_up_required: Optional[bool] = Field(None, description="New follow-up requirement")
    follow_up_date: Optional[datetime] = Field(None, description="New follow-up date")
    follow_up_notes: Optional[str] = Field(None, description="New follow-up notes")
    duration_minutes: Optional[int] = Field(None, description="New duration", ge=15, le=480)


class AppointmentResponseV1(AppointmentBaseV1, IDMixin, TimestampMixin):
    """Schema for appointment response in V1."""
    id: uuid.UUID = Field(description="Appointment unique identifier")
    status: AppointmentStatus = Field(description="Current appointment status")
    duration_minutes: int = Field(description="Duration in minutes")
    priority: AppointmentPriority = Field(description="Priority level")
    symptoms: Optional[str] = Field(None, description="Pet symptoms")
    notes: Optional[str] = Field(None, description="Additional notes")
    special_instructions: Optional[str] = Field(None, description="Special instructions")
    estimated_cost: Optional[float] = Field(None, description="Estimated cost")
    actual_cost: Optional[float] = Field(None, description="Actual cost if completed")
    follow_up_required: bool = Field(description="Whether follow-up is required")
    follow_up_date: Optional[datetime] = Field(None, description="Follow-up date")
    follow_up_notes: Optional[str] = Field(None, description="Follow-up notes")
    confirmed_at: Optional[datetime] = Field(None, description="Confirmation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    cancelled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    cancellation_reason: Optional[str] = Field(None, description="Cancellation reason")


# List and pagination schemas
class AppointmentListRequestV1(PaginationRequest):
    """Schema for appointment list request in V1."""
    pet_id: Optional[uuid.UUID] = Field(None, description="Filter by pet ID")
    pet_owner_id: Optional[uuid.UUID] = Field(None, description="Filter by pet owner ID")
    veterinarian_id: Optional[uuid.UUID] = Field(None, description="Filter by veterinarian ID")
    clinic_id: Optional[uuid.UUID] = Field(None, description="Filter by clinic ID")
    status: Optional[AppointmentStatus] = Field(None, description="Filter by status")
    appointment_type: Optional[AppointmentType] = Field(None, description="Filter by type")
    priority: Optional[AppointmentPriority] = Field(None, description="Filter by priority")
    start_date: Optional[date] = Field(None, description="Filter by start date")
    end_date: Optional[date] = Field(None, description="Filter by end date")
    upcoming_only: bool = Field(False, description="Show only upcoming appointments")
    today_only: bool = Field(False, description="Show only today's appointments")


class AppointmentListResponseV1(BaseSchema):
    """Schema for appointment list response in V1."""
    appointments: List[AppointmentResponseV1] = Field(description="List of appointments")
    total: int = Field(description="Total number of appointments")
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")


# Status change schemas
class AppointmentCancelRequestV1(BaseSchema):
    """Schema for cancelling an appointment in V1."""
    cancellation_reason: Optional[str] = Field(None, description="Reason for cancellation")


class AppointmentRescheduleRequestV1(BaseSchema):
    """Schema for rescheduling an appointment in V1."""
    new_scheduled_at: datetime = Field(description="New scheduled date and time")


class AppointmentCompleteRequestV1(BaseSchema):
    """Schema for completing an appointment in V1."""
    actual_cost: Optional[float] = positive_float_field("Actual cost of appointment", default=None)


# Success and error response schemas
class AppointmentOperationSuccessV1(BaseSchema):
    """Schema for successful appointment operations in V1."""
    success: bool = Field(True, description="Operation success flag")
    message: str = Field(description="Success message")
    appointment_id: Optional[uuid.UUID] = Field(None, description="Appointment ID if applicable")


class AppointmentErrorResponseV1(BaseSchema):
    """Schema for appointment operation errors in V1."""
    success: bool = Field(False, description="Operation success flag")
    message: str = Field(description="Error message")
    error_code: Optional[str] = Field(None, description="Specific error code")
    field_errors: Optional[List[str]] = Field(None, description="Field-specific errors")


# Response models using helper functions
AppointmentResponseModelV1 = create_v1_response(AppointmentResponseV1)
AppointmentListResponseModelV1 = create_v1_list_response(AppointmentResponseV1)

# Specialized response models for different operations
AppointmentCreateResponseV1 = create_v1_response(AppointmentResponseV1)
AppointmentUpdateResponseV1 = create_v1_response(AppointmentResponseV1)
AppointmentGetResponseV1 = create_v1_response(AppointmentResponseV1)
AppointmentCancelResponseV1 = create_v1_response(AppointmentResponseV1)
AppointmentConfirmResponseV1 = create_v1_response(AppointmentResponseV1)
AppointmentStartResponseV1 = create_v1_response(AppointmentResponseV1)
AppointmentCompleteResponseV1 = create_v1_response(AppointmentResponseV1)
AppointmentRescheduleResponseV1 = create_v1_response(AppointmentResponseV1)
AppointmentDeleteResponseV1 = create_v1_response(AppointmentOperationSuccessV1)


# Export all schemas
__all__ = [
    "AppointmentBaseV1",
    "AppointmentCreateV1",
    "AppointmentUpdateV1",
    "AppointmentResponseV1",
    "AppointmentListRequestV1",
    "AppointmentListResponseV1",
    "AppointmentCancelRequestV1",
    "AppointmentRescheduleRequestV1",
    "AppointmentCompleteRequestV1",
    "AppointmentOperationSuccessV1",
    "AppointmentErrorResponseV1",
    "AppointmentResponseModelV1",
    "AppointmentListResponseModelV1",
    "AppointmentCreateResponseV1",
    "AppointmentUpdateResponseV1",
    "AppointmentGetResponseV1",
    "AppointmentCancelResponseV1",
    "AppointmentConfirmResponseV1",
    "AppointmentStartResponseV1",
    "AppointmentCompleteResponseV1",
    "AppointmentRescheduleResponseV1",
    "AppointmentDeleteResponseV1",
]