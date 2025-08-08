"""
Appointment-related background tasks for reminders and notifications.
"""

from datetime import datetime, timedelta
from typing import List, Optional
import uuid
from celery import Celery
from sqlalchemy import select, and_, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.appointment import Appointment, AppointmentSlot, AppointmentStatus
from app.services.notification_service import NotificationService
from app.core.celery_app import celery_app


@celery_app.task(name="send_appointment_reminders")
def send_appointment_reminders():
    """
    Send appointment reminders for upcoming appointments.
    This task should be run periodically (e.g., every hour).
    """
    import asyncio
    return asyncio.run(_send_appointment_reminders_async())


async def _send_appointment_reminders_async():
    """Async implementation of appointment reminder sending."""
    try:
        async with get_db() as db:
            notification_service = NotificationService()
            
            # Send 24-hour reminders
            await _send_24_hour_reminders(db, notification_service)
            
            # Send 2-hour reminders
            await _send_2_hour_reminders(db, notification_service)
            
            return {"success": True, "message": "Appointment reminders sent successfully"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _send_24_hour_reminders(db: AsyncSession, notification_service: NotificationService):
    """Send 24-hour appointment reminders."""
    # Calculate time window for 24-hour reminders (23-25 hours from now)
    now = datetime.utcnow()
    start_time = now + timedelta(hours=23)
    end_time = now + timedelta(hours=25)
    
    # Query for appointments needing 24-hour reminders
    query = select(Appointment).where(
        and_(
            Appointment.scheduled_at >= start_time,
            Appointment.scheduled_at <= end_time,
            Appointment.status.in_([
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.CONFIRMED
            ]),
            Appointment.reminder_sent_24h == False
        )
    ).options(
        selectinload(Appointment.pet),
        selectinload(Appointment.pet_owner),
        selectinload(Appointment.veterinarian),
        selectinload(Appointment.clinic)
    )
    
    result = await db.execute(query)
    appointments = result.scalars().all()
    
    for appointment in appointments:
        try:
            # Send email reminder
            await notification_service.send_appointment_reminder_email(
                appointment=appointment,
                reminder_type="24_hour"
            )
            
            # Send SMS reminder if phone number available
            if hasattr(appointment.pet_owner, 'phone_number') and appointment.pet_owner.phone_number:
                await notification_service.send_appointment_reminder_sms(
                    appointment=appointment,
                    reminder_type="24_hour"
                )
            
            # Mark reminder as sent
            appointment.reminder_sent_24h = True
            appointment.reminder_sent_24h_at = now
            
        except Exception as e:
            # Log error but continue with other appointments
            print(f"Failed to send 24-hour reminder for appointment {appointment.id}: {str(e)}")
    
    await db.commit()


async def _send_2_hour_reminders(db: AsyncSession, notification_service: NotificationService):
    """Send 2-hour appointment reminders."""
    # Calculate time window for 2-hour reminders (1.5-2.5 hours from now)
    now = datetime.utcnow()
    start_time = now + timedelta(hours=1.5)
    end_time = now + timedelta(hours=2.5)
    
    # Query for appointments needing 2-hour reminders
    query = select(Appointment).where(
        and_(
            Appointment.scheduled_at >= start_time,
            Appointment.scheduled_at <= end_time,
            Appointment.status.in_([
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.CONFIRMED
            ]),
            Appointment.reminder_sent_2h == False
        )
    ).options(
        selectinload(Appointment.pet),
        selectinload(Appointment.pet_owner),
        selectinload(Appointment.veterinarian),
        selectinload(Appointment.clinic)
    )
    
    result = await db.execute(query)
    appointments = result.scalars().all()
    
    for appointment in appointments:
        try:
            # Send email reminder
            await notification_service.send_appointment_reminder_email(
                appointment=appointment,
                reminder_type="2_hour"
            )
            
            # Send SMS reminder if phone number available
            if hasattr(appointment.pet_owner, 'phone_number') and appointment.pet_owner.phone_number:
                await notification_service.send_appointment_reminder_sms(
                    appointment=appointment,
                    reminder_type="2_hour"
                )
            
            # Send push notification if supported
            await notification_service.send_appointment_reminder_push(
                appointment=appointment,
                reminder_type="2_hour"
            )
            
            # Mark reminder as sent
            appointment.reminder_sent_2h = True
            appointment.reminder_sent_2h_at = now
            
        except Exception as e:
            # Log error but continue with other appointments
            print(f"Failed to send 2-hour reminder for appointment {appointment.id}: {str(e)}")
    
    await db.commit()


@celery_app.task(name="send_appointment_confirmation")
def send_appointment_confirmation(appointment_id: str):
    """
    Send appointment confirmation notification.
    """
    import asyncio
    return asyncio.run(_send_appointment_confirmation_async(uuid.UUID(appointment_id)))


async def _send_appointment_confirmation_async(appointment_id: uuid.UUID):
    """Async implementation of appointment confirmation sending."""
    try:
        async with get_db() as db:
            notification_service = NotificationService()
            
            # Get appointment with related data
            query = select(Appointment).where(Appointment.id == appointment_id).options(
                selectinload(Appointment.pet),
                selectinload(Appointment.pet_owner),
                selectinload(Appointment.veterinarian),
                selectinload(Appointment.clinic)
            )
            
            result = await db.execute(query)
            appointment = result.scalar_one_or_none()
            
            if not appointment:
                return {"success": False, "error": "Appointment not found"}
            
            # Send confirmation email
            await notification_service.send_appointment_confirmation_email(appointment)
            
            # Send confirmation SMS if phone number available
            if hasattr(appointment.pet_owner, 'phone_number') and appointment.pet_owner.phone_number:
                await notification_service.send_appointment_confirmation_sms(appointment)
            
            return {"success": True, "message": "Appointment confirmation sent successfully"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


@celery_app.task(name="send_appointment_cancellation")
def send_appointment_cancellation(appointment_id: str):
    """
    Send appointment cancellation notification.
    """
    import asyncio
    return asyncio.run(_send_appointment_cancellation_async(uuid.UUID(appointment_id)))


async def _send_appointment_cancellation_async(appointment_id: uuid.UUID):
    """Async implementation of appointment cancellation sending."""
    try:
        async with get_db() as db:
            notification_service = NotificationService()
            
            # Get appointment with related data
            query = select(Appointment).where(Appointment.id == appointment_id).options(
                selectinload(Appointment.pet),
                selectinload(Appointment.pet_owner),
                selectinload(Appointment.veterinarian),
                selectinload(Appointment.clinic)
            )
            
            result = await db.execute(query)
            appointment = result.scalar_one_or_none()
            
            if not appointment:
                return {"success": False, "error": "Appointment not found"}
            
            # Send cancellation email
            await notification_service.send_appointment_cancellation_email(appointment)
            
            # Send cancellation SMS if phone number available
            if hasattr(appointment.pet_owner, 'phone_number') and appointment.pet_owner.phone_number:
                await notification_service.send_appointment_cancellation_sms(appointment)
            
            return {"success": True, "message": "Appointment cancellation notification sent successfully"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


@celery_app.task(name="send_appointment_reschedule")
def send_appointment_reschedule(appointment_id: str, old_scheduled_at: str):
    """
    Send appointment reschedule notification.
    """
    import asyncio
    old_time = datetime.fromisoformat(old_scheduled_at.replace('Z', '+00:00'))
    return asyncio.run(_send_appointment_reschedule_async(uuid.UUID(appointment_id), old_time))


async def _send_appointment_reschedule_async(appointment_id: uuid.UUID, old_scheduled_at: datetime):
    """Async implementation of appointment reschedule sending."""
    try:
        async with get_db() as db:
            notification_service = NotificationService()
            
            # Get appointment with related data
            query = select(Appointment).where(Appointment.id == appointment_id).options(
                selectinload(Appointment.pet),
                selectinload(Appointment.pet_owner),
                selectinload(Appointment.veterinarian),
                selectinload(Appointment.clinic)
            )
            
            result = await db.execute(query)
            appointment = result.scalar_one_or_none()
            
            if not appointment:
                return {"success": False, "error": "Appointment not found"}
            
            # Send reschedule email
            await notification_service.send_appointment_reschedule_email(
                appointment, old_scheduled_at
            )
            
            # Send reschedule SMS if phone number available
            if hasattr(appointment.pet_owner, 'phone_number') and appointment.pet_owner.phone_number:
                await notification_service.send_appointment_reschedule_sms(
                    appointment, old_scheduled_at
                )
            
            return {"success": True, "message": "Appointment reschedule notification sent successfully"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


@celery_app.task(name="send_follow_up_reminders")
def send_follow_up_reminders():
    """
    Send follow-up reminders for completed appointments that require follow-up.
    This task should be run daily.
    """
    import asyncio
    return asyncio.run(_send_follow_up_reminders_async())


async def _send_follow_up_reminders_async():
    """Async implementation of follow-up reminder sending."""
    try:
        async with get_db() as db:
            notification_service = NotificationService()
            
            # Get appointments that need follow-up reminders
            today = datetime.utcnow().date()
            
            query = select(Appointment).where(
                and_(
                    Appointment.status == AppointmentStatus.COMPLETED,
                    Appointment.follow_up_required == True,
                    Appointment.follow_up_date <= datetime.combine(today, datetime.max.time()),
                    # Add a flag to track if follow-up reminder was sent
                    # For now, we'll check if follow_up_date is today or past
                )
            ).options(
                selectinload(Appointment.pet),
                selectinload(Appointment.pet_owner),
                selectinload(Appointment.veterinarian),
                selectinload(Appointment.clinic)
            )
            
            result = await db.execute(query)
            appointments = result.scalars().all()
            
            sent_count = 0
            for appointment in appointments:
                try:
                    # Send follow-up reminder email
                    await notification_service.send_follow_up_reminder_email(appointment)
                    
                    # Send follow-up reminder SMS if phone number available
                    if hasattr(appointment.pet_owner, 'phone_number') and appointment.pet_owner.phone_number:
                        await notification_service.send_follow_up_reminder_sms(appointment)
                    
                    sent_count += 1
                    
                except Exception as e:
                    # Log error but continue with other appointments
                    print(f"Failed to send follow-up reminder for appointment {appointment.id}: {str(e)}")
            
            return {
                "success": True, 
                "message": f"Follow-up reminders sent successfully",
                "sent_count": sent_count,
                "total_appointments": len(appointments)
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}


@celery_app.task(name="cleanup_expired_slots")
def cleanup_expired_slots():
    """
    Clean up expired appointment slots.
    This task should be run daily to remove old slots.
    """
    import asyncio
    return asyncio.run(_cleanup_expired_slots_async())


async def _cleanup_expired_slots_async():
    """Async implementation of expired slot cleanup."""
    try:
        async with get_db() as db:
            # Delete slots that are older than 30 days and not booked
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            # First, get count of slots to be deleted
            count_query = select(func.count(AppointmentSlot.id)).where(
                and_(
                    AppointmentSlot.start_time < cutoff_date,
                    AppointmentSlot.current_bookings == 0
                )
            )
            
            count_result = await db.execute(count_query)
            slots_to_delete = count_result.scalar() or 0
            
            # Delete the expired slots
            delete_query = delete(AppointmentSlot).where(
                and_(
                    AppointmentSlot.start_time < cutoff_date,
                    AppointmentSlot.current_bookings == 0
                )
            )
            
            await db.execute(delete_query)
            await db.commit()
            
            return {
                "success": True,
                "message": f"Cleaned up {slots_to_delete} expired appointment slots",
                "deleted_count": slots_to_delete
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}


@celery_app.task(name="update_appointment_statuses")
def update_appointment_statuses():
    """
    Update appointment statuses based on current time.
    This task should be run every hour to mark appointments as no-show if they weren't started.
    """
    import asyncio
    return asyncio.run(_update_appointment_statuses_async())


async def _update_appointment_statuses_async():
    """Async implementation of appointment status updates."""
    try:
        async with get_db() as db:
            now = datetime.utcnow()
            
            # Mark appointments as no-show if they're more than 30 minutes past scheduled time
            # and still in scheduled or confirmed status
            no_show_cutoff = now - timedelta(minutes=30)
            
            query = select(Appointment).where(
                and_(
                    Appointment.scheduled_at < no_show_cutoff,
                    Appointment.status.in_([
                        AppointmentStatus.SCHEDULED,
                        AppointmentStatus.CONFIRMED
                    ])
                )
            )
            
            result = await db.execute(query)
            appointments = result.scalars().all()
            
            updated_count = 0
            for appointment in appointments:
                appointment.status = AppointmentStatus.NO_SHOW
                updated_count += 1
            
            await db.commit()
            
            return {
                "success": True,
                "message": f"Updated {updated_count} appointments to no-show status",
                "updated_count": updated_count
            }
            
    except Exception as e:
        return {"success": False, "error": str(e)}