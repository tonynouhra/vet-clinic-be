"""
Notification-related Celery tasks.
"""
from app.core.celery_app import celery_app


@celery_app.task(bind=True)
def send_email_notification(self, recipient: str, subject: str, body: str):
    """
    Send email notification task.
    
    Args:
        recipient: Email recipient
        subject: Email subject
        body: Email body
    """
    # Implementation will be added in future tasks
    pass


@celery_app.task(bind=True)
def send_sms_notification(self, phone_number: str, message: str):
    """
    Send SMS notification task.
    
    Args:
        phone_number: Recipient phone number
        message: SMS message
    """
    # Implementation will be added in future tasks
    pass


@celery_app.task(bind=True)
def send_push_notification(self, user_id: str, title: str, body: str):
    """
    Send push notification task.
    
    Args:
        user_id: User ID
        title: Notification title
        body: Notification body
    """
    # Implementation will be added in future tasks
    pass