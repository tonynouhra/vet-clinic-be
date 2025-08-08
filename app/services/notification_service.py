"""
Notification Service

Handles sending various types of notifications including email, SMS, and push notifications.
Supports reminder notifications, appointment notifications, and other system notifications.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, date
import logging
from app.models.user import User
from app.models.pet import Pet, Reminder
from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for handling notifications across different channels."""

    def __init__(self):
        self.email_enabled = getattr(settings, 'EMAIL_ENABLED', False)
        self.sms_enabled = getattr(settings, 'SMS_ENABLED', False)
        self.push_enabled = getattr(settings, 'PUSH_NOTIFICATIONS_ENABLED', False)

    async def send_reminder_notification(
        self,
        user: User,
        pet: Pet,
        reminder: Reminder,
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Send a reminder notification to the user.
        
        Args:
            user: User to notify
            pet: Pet the reminder is for
            reminder: Reminder object
            channels: List of channels to use (email, sms, push). If None, uses all available.
            
        Returns:
            Dict with channel success status
        """
        if channels is None:
            channels = []
            if self.email_enabled:
                channels.append('email')
            if self.sms_enabled:
                channels.append('sms')
            if self.push_enabled:
                channels.append('push')
        
        results = {}
        
        # Prepare notification content
        subject = f"Reminder: {reminder.title}"
        message = self._format_reminder_message(user, pet, reminder)
        
        # Send via each channel
        for channel in channels:
            try:
                if channel == 'email':
                    results['email'] = await self._send_email_notification(
                        user.email, subject, message, reminder
                    )
                elif channel == 'sms':
                    results['sms'] = await self._send_sms_notification(
                        user.phone if hasattr(user, 'phone') else None, message, reminder
                    )
                elif channel == 'push':
                    results['push'] = await self._send_push_notification(
                        user.id, subject, message, reminder
                    )
            except Exception as e:
                logger.error(f"Failed to send {channel} notification for reminder {reminder.id}: {str(e)}")
                results[channel] = False
        
        return results

    async def send_appointment_reminder(
        self,
        user: User,
        pet: Pet,
        appointment: Any,  # Appointment model
        reminder_type: str = "24h"
    ) -> Dict[str, bool]:
        """
        Send appointment reminder notification.
        
        Args:
            user: User to notify
            pet: Pet the appointment is for
            appointment: Appointment object
            reminder_type: Type of reminder (24h, 2h, etc.)
            
        Returns:
            Dict with channel success status
        """
        subject = f"Appointment Reminder: {pet.name}"
        message = self._format_appointment_reminder_message(user, pet, appointment, reminder_type)
        
        results = {}
        
        try:
            if self.email_enabled:
                results['email'] = await self._send_email_notification(
                    user.email, subject, message, appointment
                )
        except Exception as e:
            logger.error(f"Failed to send appointment reminder email: {str(e)}")
            results['email'] = False
        
        return results

    async def send_health_alert(
        self,
        user: User,
        pet: Pet,
        alert_type: str,
        message: str,
        urgent: bool = False
    ) -> Dict[str, bool]:
        """
        Send health alert notification.
        
        Args:
            user: User to notify
            pet: Pet the alert is for
            alert_type: Type of alert
            message: Alert message
            urgent: Is this an urgent alert
            
        Returns:
            Dict with channel success status
        """
        subject = f"{'URGENT: ' if urgent else ''}Health Alert for {pet.name}"
        
        results = {}
        
        try:
            if self.email_enabled:
                results['email'] = await self._send_email_notification(
                    user.email, subject, message, None
                )
            
            # For urgent alerts, also try SMS if available
            if urgent and self.sms_enabled and hasattr(user, 'phone') and user.phone:
                results['sms'] = await self._send_sms_notification(
                    user.phone, f"{subject}: {message}", None
                )
        except Exception as e:
            logger.error(f"Failed to send health alert: {str(e)}")
            results['email'] = False
        
        return results

    # Private methods for different notification channels

    async def _send_email_notification(
        self,
        email: str,
        subject: str,
        message: str,
        context: Any = None
    ) -> bool:
        """Send email notification."""
        try:
            # In a real implementation, this would use an email service like SendGrid, SES, etc.
            # For now, we'll just log the notification
            logger.info(f"EMAIL NOTIFICATION - To: {email}, Subject: {subject}")
            logger.info(f"Message: {message}")
            
            # Simulate email sending
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {email}: {str(e)}")
            return False

    async def _send_sms_notification(
        self,
        phone: Optional[str],
        message: str,
        context: Any = None
    ) -> bool:
        """Send SMS notification."""
        try:
            if not phone:
                return False
            
            # In a real implementation, this would use an SMS service like Twilio
            # For now, we'll just log the notification
            logger.info(f"SMS NOTIFICATION - To: {phone}")
            logger.info(f"Message: {message}")
            
            # Simulate SMS sending
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone}: {str(e)}")
            return False

    async def _send_push_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        context: Any = None
    ) -> bool:
        """Send push notification."""
        try:
            # In a real implementation, this would use a push service like FCM, APNs, etc.
            # For now, we'll just log the notification
            logger.info(f"PUSH NOTIFICATION - To User: {user_id}, Title: {title}")
            logger.info(f"Message: {message}")
            
            # Simulate push notification sending
            return True
            
        except Exception as e:
            logger.error(f"Failed to send push notification to user {user_id}: {str(e)}")
            return False

    # Message formatting methods

    def _format_reminder_message(self, user: User, pet: Pet, reminder: Reminder) -> str:
        """Format reminder message."""
        message = f"Hello {user.first_name},\n\n"
        message += f"This is a reminder for your pet {pet.name}:\n\n"
        message += f"Reminder: {reminder.title}\n"
        
        if reminder.description:
            message += f"Details: {reminder.description}\n"
        
        message += f"Due Date: {reminder.due_date.strftime('%B %d, %Y')}\n\n"
        
        if reminder.reminder_type == "vaccination":
            message += "Please schedule an appointment with your veterinarian to ensure your pet stays up to date with their vaccinations.\n\n"
        elif reminder.reminder_type == "medication":
            message += "Please ensure your pet receives their medication as prescribed.\n\n"
        elif reminder.reminder_type == "checkup":
            message += "It's time for your pet's regular checkup. Please schedule an appointment with your veterinarian.\n\n"
        
        message += "Thank you for keeping your pet healthy!\n\n"
        message += "Best regards,\nYour Veterinary Clinic Team"
        
        return message

    def _format_appointment_reminder_message(
        self, 
        user: User, 
        pet: Pet, 
        appointment: Any, 
        reminder_type: str
    ) -> str:
        """Format appointment reminder message."""
        time_text = "24 hours" if reminder_type == "24h" else "2 hours"
        
        message = f"Hello {user.first_name},\n\n"
        message += f"This is a reminder that {pet.name} has an appointment in {time_text}.\n\n"
        message += f"Appointment Details:\n"
        message += f"Date: {appointment.scheduled_at.strftime('%B %d, %Y')}\n"
        message += f"Time: {appointment.scheduled_at.strftime('%I:%M %p')}\n"
        
        if hasattr(appointment, 'veterinarian') and appointment.veterinarian:
            message += f"Veterinarian: Dr. {appointment.veterinarian.user.last_name}\n"
        
        if hasattr(appointment, 'clinic') and appointment.clinic:
            message += f"Location: {appointment.clinic.name}\n"
        
        message += f"\nPlease arrive 15 minutes early for check-in.\n\n"
        message += "If you need to reschedule or cancel, please contact us as soon as possible.\n\n"
        message += "Thank you!\n\n"
        message += "Best regards,\nYour Veterinary Clinic Team"
        
        return message

    # Utility methods

    async def get_notification_preferences(self, user_id: str) -> Dict[str, bool]:
        """Get user notification preferences."""
        # In a real implementation, this would fetch from database
        # For now, return default preferences
        return {
            "email_reminders": True,
            "sms_reminders": False,
            "push_reminders": True,
            "appointment_reminders": True,
            "health_alerts": True
        }

    async def update_notification_preferences(
        self, 
        user_id: str, 
        preferences: Dict[str, bool]
    ) -> bool:
        """Update user notification preferences."""
        try:
            # In a real implementation, this would update the database
            logger.info(f"Updated notification preferences for user {user_id}: {preferences}")
            return True
        except Exception as e:
            logger.error(f"Failed to update notification preferences for user {user_id}: {str(e)}")
            return False

    # Appointment-specific notification methods

    async def send_appointment_reminder_email(self, appointment: Any, reminder_type: str) -> bool:
        """Send appointment reminder email."""
        try:
            subject = f"Appointment Reminder - {appointment.pet.name}"
            message = self._format_appointment_reminder_message(
                appointment.pet_owner, appointment.pet, appointment, reminder_type
            )
            return await self._send_email_notification(
                appointment.pet_owner.email, subject, message, appointment
            )
        except Exception as e:
            logger.error(f"Failed to send appointment reminder email: {str(e)}")
            return False

    async def send_appointment_reminder_sms(self, appointment: Any, reminder_type: str) -> bool:
        """Send appointment reminder SMS."""
        try:
            message = self._format_appointment_reminder_sms(appointment, reminder_type)
            return await self._send_sms_notification(
                appointment.pet_owner.phone_number, message, appointment
            )
        except Exception as e:
            logger.error(f"Failed to send appointment reminder SMS: {str(e)}")
            return False

    async def send_appointment_reminder_push(self, appointment: Any, reminder_type: str) -> bool:
        """Send appointment reminder push notification."""
        try:
            title = f"Appointment Reminder - {appointment.pet.name}"
            message = f"Your appointment is in {reminder_type.replace('_', ' ')}"
            return await self._send_push_notification(
                str(appointment.pet_owner.id), title, message, appointment
            )
        except Exception as e:
            logger.error(f"Failed to send appointment reminder push: {str(e)}")
            return False

    async def send_appointment_confirmation_email(self, appointment: Any) -> bool:
        """Send appointment confirmation email."""
        try:
            subject = f"Appointment Confirmed - {appointment.pet.name}"
            message = self._format_appointment_confirmation_message(appointment)
            return await self._send_email_notification(
                appointment.pet_owner.email, subject, message, appointment
            )
        except Exception as e:
            logger.error(f"Failed to send appointment confirmation email: {str(e)}")
            return False

    async def send_appointment_confirmation_sms(self, appointment: Any) -> bool:
        """Send appointment confirmation SMS."""
        try:
            message = f"Appointment confirmed for {appointment.pet.name} on {appointment.scheduled_at.strftime('%m/%d/%Y at %I:%M %p')}"
            return await self._send_sms_notification(
                appointment.pet_owner.phone_number, message, appointment
            )
        except Exception as e:
            logger.error(f"Failed to send appointment confirmation SMS: {str(e)}")
            return False

    async def send_appointment_cancellation_email(self, appointment: Any) -> bool:
        """Send appointment cancellation email."""
        try:
            subject = f"Appointment Cancelled - {appointment.pet.name}"
            message = self._format_appointment_cancellation_message(appointment)
            return await self._send_email_notification(
                appointment.pet_owner.email, subject, message, appointment
            )
        except Exception as e:
            logger.error(f"Failed to send appointment cancellation email: {str(e)}")
            return False

    async def send_appointment_cancellation_sms(self, appointment: Any) -> bool:
        """Send appointment cancellation SMS."""
        try:
            message = f"Appointment cancelled for {appointment.pet.name} on {appointment.scheduled_at.strftime('%m/%d/%Y at %I:%M %p')}"
            return await self._send_sms_notification(
                appointment.pet_owner.phone_number, message, appointment
            )
        except Exception as e:
            logger.error(f"Failed to send appointment cancellation SMS: {str(e)}")
            return False

    async def send_appointment_reschedule_email(self, appointment: Any, old_scheduled_at: datetime) -> bool:
        """Send appointment reschedule email."""
        try:
            subject = f"Appointment Rescheduled - {appointment.pet.name}"
            message = self._format_appointment_reschedule_message(appointment, old_scheduled_at)
            return await self._send_email_notification(
                appointment.pet_owner.email, subject, message, appointment
            )
        except Exception as e:
            logger.error(f"Failed to send appointment reschedule email: {str(e)}")
            return False

    async def send_appointment_reschedule_sms(self, appointment: Any, old_scheduled_at: datetime) -> bool:
        """Send appointment reschedule SMS."""
        try:
            message = f"Appointment rescheduled for {appointment.pet.name} from {old_scheduled_at.strftime('%m/%d/%Y at %I:%M %p')} to {appointment.scheduled_at.strftime('%m/%d/%Y at %I:%M %p')}"
            return await self._send_sms_notification(
                appointment.pet_owner.phone_number, message, appointment
            )
        except Exception as e:
            logger.error(f"Failed to send appointment reschedule SMS: {str(e)}")
            return False

    # Additional message formatting methods

    def _format_appointment_reminder_sms(self, appointment: Any, reminder_type: str) -> str:
        """Format appointment reminder SMS message."""
        time_text = "24 hours" if reminder_type == "24_hour" else "2 hours"
        return f"Reminder: {appointment.pet.name} has an appointment in {time_text} on {appointment.scheduled_at.strftime('%m/%d/%Y at %I:%M %p')}"

    def _format_appointment_confirmation_message(self, appointment: Any) -> str:
        """Format appointment confirmation message."""
        message = f"Hello {appointment.pet_owner.first_name},\n\n"
        message += f"Your appointment for {appointment.pet.name} has been confirmed.\n\n"
        message += f"Appointment Details:\n"
        message += f"Date: {appointment.scheduled_at.strftime('%B %d, %Y')}\n"
        message += f"Time: {appointment.scheduled_at.strftime('%I:%M %p')}\n"
        message += f"Type: {appointment.appointment_type.value.replace('_', ' ').title()}\n"
        
        if hasattr(appointment, 'veterinarian') and appointment.veterinarian:
            message += f"Veterinarian: Dr. {appointment.veterinarian.user.last_name}\n"
        
        if hasattr(appointment, 'clinic') and appointment.clinic:
            message += f"Location: {appointment.clinic.name}\n"
        
        message += f"\nPlease arrive 15 minutes early for check-in.\n\n"
        message += "If you need to make any changes, please contact us as soon as possible.\n\n"
        message += "Thank you!\n\n"
        message += "Best regards,\nYour Veterinary Clinic Team"
        
        return message

    def _format_appointment_cancellation_message(self, appointment: Any) -> str:
        """Format appointment cancellation message."""
        message = f"Hello {appointment.pet_owner.first_name},\n\n"
        message += f"Your appointment for {appointment.pet.name} has been cancelled.\n\n"
        message += f"Cancelled Appointment Details:\n"
        message += f"Date: {appointment.scheduled_at.strftime('%B %d, %Y')}\n"
        message += f"Time: {appointment.scheduled_at.strftime('%I:%M %p')}\n"
        
        if appointment.cancellation_reason:
            message += f"Reason: {appointment.cancellation_reason}\n"
        
        message += f"\nIf you would like to reschedule, please contact us to book a new appointment.\n\n"
        message += "Thank you for your understanding.\n\n"
        message += "Best regards,\nYour Veterinary Clinic Team"
        
        return message

    def _format_appointment_reschedule_message(self, appointment: Any, old_scheduled_at: datetime) -> str:
        """Format appointment reschedule message."""
        message = f"Hello {appointment.pet_owner.first_name},\n\n"
        message += f"Your appointment for {appointment.pet.name} has been rescheduled.\n\n"
        message += f"Previous Appointment:\n"
        message += f"Date: {old_scheduled_at.strftime('%B %d, %Y')}\n"
        message += f"Time: {old_scheduled_at.strftime('%I:%M %p')}\n\n"
        message += f"New Appointment:\n"
        message += f"Date: {appointment.scheduled_at.strftime('%B %d, %Y')}\n"
        message += f"Time: {appointment.scheduled_at.strftime('%I:%M %p')}\n"
        
        if hasattr(appointment, 'veterinarian') and appointment.veterinarian:
            message += f"Veterinarian: Dr. {appointment.veterinarian.user.last_name}\n"
        
        if hasattr(appointment, 'clinic') and appointment.clinic:
            message += f"Location: {appointment.clinic.name}\n"
        
        message += f"\nPlease arrive 15 minutes early for check-in.\n\n"
        message += "If you have any questions, please contact us.\n\n"
        message += "Thank you!\n\n"
        message += "Best regards,\nYour Veterinary Clinic Team"
        
        return message