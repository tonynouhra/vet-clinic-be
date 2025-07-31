"""
V2 Appointment Schemas - Enhanced appointment management schemas for API version 2.

These schemas define the structure of appointment-related requests and responses
for V2 endpoints with enhanced features like recurring appointments, advanced filtering,
batch operations, and detailed appointment analytics.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
import uuid
from pydantic import Field, validator

from app.models.appointment import AppointmentStatus, AppointmentType, AppointmentPriority
from app.api.schemas.validators import (
    validate_positive_integer,
    positive_int_field,
    non_empty_string_field
)
from . import (
    BaseSchema,
    TimestampMixin,
    IDMixin,
    PaginationRequest,
    create_v2_response,
    create_v2_list_response
)


# Enhanced Appointment schemas for V2
class AppointmentBaseV2(BaseSchema):
    """Base appointment schema with common fields for V2."""
    pet_id: uuid.UUID = Field(..., description="Pet ID")
    veterinarian_id: uuid.UUID = Field(..., description="Veterinarian ID")
    clinic_id: uuid.UUID = Field(..., description="Clinic ID")
    appointment_type: AppointmentType = Field(..., description="Appointment type")
    scheduled_at: datetime = Field(..., description="Scheduled appointment time")
    duration_minutes: int = positive_int_field("Duration in minutes", default=30)
    reason: str = non_empty_string_field("Reason for appointment")


class AppointmentCreateV2(AppointmentBaseV2):
    """Schema for creating an appointment in V2 with enhanced fields."""
    priority: Optional[AppointmentPriority] = Field(AppointmentPriority.NORMAL, description="Appointment priority")
    symptoms: Optional[str] = Field(None, description="Pet symptoms")
    notes: Optional[str] = Field(None, description="Additional notes")
    special_instructions: Optional[str] = Field(None, description="Special instructions")
    estimated_cost: Optional[float] = Field(None, ge=0, description="Estimated cost")
    
    # V2 Enhanced features
    services_requested: Optional[List[str]] = Field(None, description="List of requested services")
    recurring_pattern: Optional[Dict[str, Any]] = Field(None, description="Recurring appointment pattern")
    reminder_preferences: Optional[Dict[str, bool]] = Field(None, description="Reminder preferences")
    pre_appointment_checklist: Optional[List[str]] = Field(None, description="Pre-appointment checklist items")
    emergency_contact: Optional[Dict[str, str]] = Field(None, description="Emergency contact for appointment")

    @validator('scheduled_at')
    def validate_scheduled_at(cls, v):
        if v <= datetime.now():
            raise ValueError('Appointment must be scheduled in the future')
        return v

    @validator('duration_minutes')
    def validate_duration(cls, v):
        if v < 15 or v > 480:  # 15 minutes to 8 hours
            raise ValueError('Duration must be between 15 and 480 minutes')
        return v

    @validator('services_requested')
    def validate_services_requested(cls, v):
        if v is not None:
            if len(v) == 0:
                raise ValueError('Services requested cannot be empty if provided')
            # Remove duplicates and empty strings
            return list(set(service.strip() for service in v if service.strip()))
        return v

    @validator('recurring_pattern')
    def validate_recurring_pattern(cls, v):
        if v is not None:
            required_fields = ['frequency', 'interval']
            for field in required_fields:
                if field not in v:
                    raise ValueError(f'Recurring pattern must include {field}')
            
            valid_frequencies = ['daily', 'weekly', 'monthly', 'yearly']
            if v['frequency'] not in valid_frequencies:
                raise ValueError(f'Frequency must be one of: {", ".join(valid_frequencies)}')
            
            if not isinstance(v['interval'], int) or v['interval'] < 1:
                raise ValueError('Interval must be a positive integer')
        return v


class AppointmentUpdateV2(BaseSchema):
    """Schema for updating an appointment in V2 with enhanced fields."""
    appointment_type: Optional[AppointmentType] = Field(None, description="Appointment type")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled appointment time")
    duration_minutes: Optional[int] = Field(None, gt=0, description="Duration in minutes")
    reason: Optional[str] = Field(None, min_length=1, description="Reason for appointment")
    priority: Optional[AppointmentPriority] = Field(None, description="Appointment priority")
    symptoms: Optional[str] = Field(None, description="Pet symptoms")
    notes: Optional[str] = Field(None, description="Additional notes")
    special_instructions: Optional[str] = Field(None, description="Special instructions")
    estimated_cost: Optional[float] = Field(None, ge=0, description="Estimated cost")
    
    # V2 Enhanced features
    services_requested: Optional[List[str]] = Field(None, description="List of requested services")
    reminder_preferences: Optional[Dict[str, bool]] = Field(None, description="Reminder preferences")
    pre_appointment_checklist: Optional[List[str]] = Field(None, description="Pre-appointment checklist items")
    emergency_contact: Optional[Dict[str, str]] = Field(None, description="Emergency contact for appointment")

    @validator('scheduled_at')
    def validate_scheduled_at(cls, v):
        if v is not None and v <= datetime.now():
            raise ValueError('Appointment must be scheduled in the future')
        return v

    @validator('duration_minutes')
    def validate_duration(cls, v):
        if v is not None and (v < 15 or v > 480):
            raise ValueError('Duration must be between 15 and 480 minutes')
        return v

    @validator('reason')
    def validate_reason(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Reason cannot be empty')
        return v.strip() if v else v

    @validator('services_requested')
    def validate_services_requested(cls, v):
        if v is not None:
            if len(v) == 0:
                return []
            return list(set(service.strip() for service in v if service.strip()))
        return v


class PetInfoV2(BaseSchema):
    """V2 pet information schema for appointment responses."""
    id: uuid.UUID = Field(..., description="Pet ID")
    name: str = Field(..., description="Pet name")
    species: str = Field(..., description="Pet species")
    breed: Optional[str] = Field(None, description="Pet breed")

    class Config:
        from_attributes = True


class VeterinarianInfoV2(BaseSchema):
    """V2 veterinarian information schema for appointment responses."""
    id: uuid.UUID = Field(..., description="Veterinarian ID")
    first_name: str = Field(..., description="Veterinarian first name")
    last_name: str = Field(..., description="Veterinarian last name")
    specialization: Optional[str] = Field(None, description="Veterinarian specialization")

    class Config:
        from_attributes = True


class ClinicInfoV2(BaseSchema):
    """V2 clinic information schema for appointment responses."""
    id: uuid.UUID = Field(..., description="Clinic ID")
    name: str = Field(..., description="Clinic name")
    address: Optional[str] = Field(None, description="Clinic address")
    phone: Optional[str] = Field(None, description="Clinic phone")

    class Config:
        from_attributes = True


class AppointmentResponseV2(AppointmentBaseV2, IDMixin, TimestampMixin):
    """Schema for appointment response in V2 with enhanced fields."""
    pet_owner_id: uuid.UUID = Field(..., description="Pet owner ID")
    status: AppointmentStatus = Field(..., description="Appointment status")
    priority: AppointmentPriority = Field(..., description="Appointment priority")
    symptoms: Optional[str] = Field(None, description="Pet symptoms")
    notes: Optional[str] = Field(None, description="Additional notes")
    special_instructions: Optional[str] = Field(None, description="Special instructions")
    estimated_cost: Optional[float] = Field(None, description="Estimated cost")
    actual_cost: Optional[float] = Field(None, description="Actual cost")
    
    # Status timestamps
    confirmed_at: Optional[datetime] = Field(None, description="Confirmation timestamp")
    checked_in_at: Optional[datetime] = Field(None, description="Check-in timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    cancelled_at: Optional[datetime] = Field(None, description="Cancellation timestamp")
    cancellation_reason: Optional[str] = Field(None, description="Cancellation reason")
    
    # Follow-up information
    follow_up_required: bool = Field(..., description="Follow-up required")
    follow_up_date: Optional[datetime] = Field(None, description="Follow-up date")
    follow_up_notes: Optional[str] = Field(None, description="Follow-up notes")
    
    # V2 Enhanced features
    services_requested: Optional[List[str]] = Field(None, description="List of requested services")
    reminder_sent_24h: bool = Field(..., description="24-hour reminder sent")
    reminder_sent_2h: bool = Field(..., description="2-hour reminder sent")
    reminder_sent_24h_at: Optional[datetime] = Field(None, description="24-hour reminder timestamp")
    reminder_sent_2h_at: Optional[datetime] = Field(None, description="2-hour reminder timestamp")
    pre_appointment_checklist: Optional[List[str]] = Field(None, description="Pre-appointment checklist items")
    emergency_contact: Optional[Dict[str, str]] = Field(None, description="Emergency contact for appointment")
    
    # V2 Relationship data (optional)
    pet: Optional[PetInfoV2] = Field(None, description="Pet information")
    veterinarian: Optional[VeterinarianInfoV2] = Field(None, description="Veterinarian information")
    clinic: Optional[ClinicInfoV2] = Field(None, description="Clinic information")

    class Config:
        from_attributes = True


# Enhanced list and pagination schemas
class AppointmentListRequestV2(PaginationRequest):
    """Schema for appointment list request in V2 with enhanced filtering."""
    pet_id: Optional[uuid.UUID] = Field(None, description="Filter by pet ID")
    veterinarian_id: Optional[uuid.UUID] = Field(None, description="Filter by veterinarian ID")
    clinic_id: Optional[uuid.UUID] = Field(None, description="Filter by clinic ID")
    status: Optional[AppointmentStatus] = Field(None, description="Filter by status")
    appointment_type: Optional[AppointmentType] = Field(None, description="Filter by appointment type")
    priority: Optional[AppointmentPriority] = Field(None, description="Filter by priority")
    date_from: Optional[datetime] = Field(None, description="Filter appointments from date")
    date_to: Optional[datetime] = Field(None, description="Filter appointments to date")
    
    # V2 Enhanced filtering
    include_pet_info: bool = Field(False, description="Include pet information in response")
    include_vet_info: bool = Field(False, description="Include veterinarian information in response")
    include_clinic_info: bool = Field(False, description="Include clinic information in response")
    search: Optional[str] = Field(None, description="Search in reason, symptoms, or notes")
    has_follow_up: Optional[bool] = Field(None, description="Filter by follow-up requirement")
    cost_min: Optional[float] = Field(None, ge=0, description="Minimum cost filter")
    cost_max: Optional[float] = Field(None, ge=0, description="Maximum cost filter")
    sort_by: Optional[str] = Field("scheduled_at", description="Sort field")
    sort_order: Optional[str] = Field("asc", description="Sort order (asc/desc)")

    @validator('date_to')
    def validate_date_range(cls, v, values):
        if v is not None and 'date_from' in values and values['date_from'] is not None:
            if v <= values['date_from']:
                raise ValueError('date_to must be after date_from')
        return v

    @validator('cost_max')
    def validate_cost_range(cls, v, values):
        if v is not None and 'cost_min' in values and values['cost_min'] is not None:
            if v <= values['cost_min']:
                raise ValueError('cost_max must be greater than cost_min')
        return v

    @validator('sort_by')
    def validate_sort_by(cls, v):
        valid_fields = ['scheduled_at', 'created_at', 'status', 'priority', 'estimated_cost', 'actual_cost']
        if v not in valid_fields:
            raise ValueError(f'sort_by must be one of: {", ".join(valid_fields)}')
        return v

    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v.lower() not in ['asc', 'desc']:
            raise ValueError('sort_order must be "asc" or "desc"')
        return v.lower()


# Enhanced status management schemas
class AppointmentStatusUpdateV2(BaseSchema):
    """Schema for updating appointment status in V2 with enhanced information."""
    status: AppointmentStatus = Field(..., description="New appointment status")
    notes: Optional[str] = Field(None, description="Status update notes")
    actual_cost: Optional[float] = Field(None, ge=0, description="Actual cost (for completed appointments)")
    follow_up_required: Optional[bool] = Field(None, description="Follow-up required")
    follow_up_date: Optional[datetime] = Field(None, description="Follow-up date")
    follow_up_notes: Optional[str] = Field(None, description="Follow-up notes")
    notify_owner: bool = Field(True, description="Send notification to pet owner")

    @validator('follow_up_date')
    def validate_follow_up_date(cls, v, values):
        if v is not None:
            if v <= datetime.now():
                raise ValueError('Follow-up date must be in the future')
            if 'follow_up_required' in values and not values.get('follow_up_required'):
                raise ValueError('Follow-up date can only be set when follow-up is required')
        return v


class AppointmentCancellationV2(BaseSchema):
    """Schema for cancelling an appointment in V2 with enhanced information."""
    reason: str = non_empty_string_field("Cancellation reason")
    notify_owner: bool = Field(True, description="Send notification to pet owner")
    refund_amount: Optional[float] = Field(None, ge=0, description="Refund amount")
    reschedule_offer: bool = Field(False, description="Offer to reschedule")
    cancellation_fee: Optional[float] = Field(None, ge=0, description="Cancellation fee")

    @validator('reason')
    def validate_reason(cls, v):
        if len(v.strip()) < 5:
            raise ValueError('Cancellation reason must be at least 5 characters')
        return v.strip()


class AppointmentRescheduleV2(BaseSchema):
    """Schema for rescheduling an appointment in V2 with enhanced information."""
    new_scheduled_at: datetime = Field(..., description="New scheduled time")
    new_duration_minutes: Optional[int] = Field(None, gt=0, description="New duration in minutes")
    reason: Optional[str] = Field(None, description="Reschedule reason")
    notify_owner: bool = Field(True, description="Send notification to pet owner")
    reschedule_fee: Optional[float] = Field(None, ge=0, description="Reschedule fee")
    update_services: Optional[List[str]] = Field(None, description="Update requested services")

    @validator('new_scheduled_at')
    def validate_new_scheduled_at(cls, v):
        if v <= datetime.now():
            raise ValueError('New appointment time must be in the future')
        return v

    @validator('new_duration_minutes')
    def validate_new_duration(cls, v):
        if v is not None and (v < 15 or v > 480):
            raise ValueError('Duration must be between 15 and 480 minutes')
        return v


# Recurring appointments schemas
class RecurringAppointmentCreateV2(BaseSchema):
    """Schema for creating recurring appointments in V2."""
    base_appointment: AppointmentCreateV2 = Field(..., description="Base appointment details")
    recurrence_pattern: Dict[str, Any] = Field(..., description="Recurrence pattern")
    end_date: Optional[date] = Field(None, description="End date for recurrence")
    max_occurrences: Optional[int] = Field(None, gt=0, le=52, description="Maximum number of occurrences")

    @validator('recurrence_pattern')
    def validate_recurrence_pattern(cls, v):
        required_fields = ['frequency', 'interval']
        for field in required_fields:
            if field not in v:
                raise ValueError(f'Recurrence pattern must include {field}')
        
        valid_frequencies = ['daily', 'weekly', 'monthly', 'yearly']
        if v['frequency'] not in valid_frequencies:
            raise ValueError(f'Frequency must be one of: {", ".join(valid_frequencies)}')
        
        if not isinstance(v['interval'], int) or v['interval'] < 1:
            raise ValueError('Interval must be a positive integer')
        return v

    @validator('end_date')
    def validate_end_date(cls, v, values):
        if v is not None:
            if v <= date.today():
                raise ValueError('End date must be in the future')
        return v


# Batch operations schemas
class BatchAppointmentOperationV2(BaseSchema):
    """Schema for batch appointment operations in V2."""
    appointment_ids: List[uuid.UUID] = Field(..., min_items=1, max_items=50, description="Appointment IDs")
    operation: str = Field(..., description="Operation type")
    operation_data: Optional[Dict[str, Any]] = Field(None, description="Operation-specific data")
    
    @validator('operation')
    def validate_operation(cls, v):
        allowed_operations = ['cancel', 'confirm', 'reschedule', 'update_status', 'send_reminders']
        if v not in allowed_operations:
            raise ValueError(f'Operation must be one of: {", ".join(allowed_operations)}')
        return v


# Statistics and analytics schemas
class AppointmentStatisticsV2(BaseSchema):
    """Schema for appointment statistics in V2."""
    total_appointments: int = Field(..., description="Total appointments")
    appointments_by_status: Dict[str, int] = Field(..., description="Appointments grouped by status")
    appointments_by_type: Dict[str, int] = Field(..., description="Appointments grouped by type")
    average_duration: float = Field(..., description="Average appointment duration")
    total_revenue: float = Field(..., description="Total revenue from appointments")
    average_cost: float = Field(..., description="Average appointment cost")
    no_show_rate: float = Field(..., description="No-show rate percentage")
    cancellation_rate: float = Field(..., description="Cancellation rate percentage")


# Response models using helper functions
AppointmentResponseModelV2 = create_v2_response(AppointmentResponseV2)
AppointmentListResponseModelV2 = create_v2_list_response(AppointmentResponseV2)
AppointmentStatisticsResponseModelV2 = create_v2_response(AppointmentStatisticsV2)

# Enhanced success response for operations
class AppointmentOperationSuccessV2(BaseSchema):
    """Schema for successful appointment operations in V2."""
    success: bool = Field(True, description="Operation success flag")
    message: str = Field(..., description="Success message")
    appointment_id: Optional[uuid.UUID] = Field(None, description="Appointment ID if applicable")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Operation timestamp")
    affected_appointments: Optional[List[uuid.UUID]] = Field(None, description="IDs of affected appointments")


# Enhanced error response specific to appointment operations
class AppointmentErrorResponseV2(BaseSchema):
    """Schema for appointment operation errors in V2."""
    success: bool = Field(False, description="Operation success flag")
    message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Specific error code")
    field_errors: Optional[Dict[str, List[str]]] = Field(None, description="Field-specific errors")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


# Export all schemas
__all__ = [
    "AppointmentBaseV2",
    "AppointmentCreateV2",
    "AppointmentUpdateV2",
    "PetInfoV2",
    "VeterinarianInfoV2",
    "ClinicInfoV2",
    "AppointmentResponseV2",
    "AppointmentListRequestV2",
    "AppointmentStatusUpdateV2",
    "AppointmentCancellationV2",
    "AppointmentRescheduleV2",
    "RecurringAppointmentCreateV2",
    "BatchAppointmentOperationV2",
    "AppointmentStatisticsV2",
    "AppointmentResponseModelV2",
    "AppointmentListResponseModelV2",
    "AppointmentStatisticsResponseModelV2",
    "AppointmentOperationSuccessV2",
    "AppointmentErrorResponseV2",
]