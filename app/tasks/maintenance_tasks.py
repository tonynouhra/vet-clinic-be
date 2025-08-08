"""
System maintenance Celery tasks.
"""
from app.core.celery_app import celery_app


@celery_app.task(bind=True)
def cleanup_expired_sessions(self):
    """
    Clean up expired user sessions task.
    """
    # Implementation will be added in future tasks
    pass


@celery_app.task(bind=True)
def cleanup_old_files(self):
    """
    Clean up old uploaded files task.
    """
    # Implementation will be added in future tasks
    pass


@celery_app.task(bind=True)
def backup_database(self):
    """
    Database backup task.
    """
    # Implementation will be added in future tasks
    pass


@celery_app.task(bind=True)
def send_health_reminders(self):
    """
    Send scheduled health reminders task.
    
    This task runs daily to check for due reminders and send notifications.
    """
    import asyncio
    from datetime import date
    from app.core.database import get_db_session
    from app.pets.services import PetService
    from app.services.notification_service import NotificationService
    
    async def process_reminders():
        """Process due reminders asynchronously."""
        try:
            # Get database session
            async with get_db_session() as db:
                pet_service = PetService(db)
                notification_service = NotificationService()
                
                # Get due reminders
                due_reminders = await pet_service.get_due_reminders(date.today())
                
                sent_count = 0
                failed_count = 0
                
                for reminder in due_reminders:
                    try:
                        # Get pet and owner information
                        pet = await pet_service.get_pet_by_id(
                            reminder.pet_id, 
                            include_owner=True
                        )
                        
                        if not pet.owner:
                            print(f"No owner found for pet {pet.id}, skipping reminder {reminder.id}")
                            continue
                        
                        # Send notification
                        await notification_service.send_reminder_notification(
                            user=pet.owner,
                            pet=pet,
                            reminder=reminder
                        )
                        
                        # Mark reminder as sent
                        await pet_service.mark_reminder_sent(reminder.id)
                        sent_count += 1
                        
                    except Exception as e:
                        print(f"Failed to send reminder {reminder.id}: {str(e)}")
                        failed_count += 1
                
                print(f"Health reminders task completed: {sent_count} sent, {failed_count} failed")
                return {"sent": sent_count, "failed": failed_count}
                
        except Exception as e:
            print(f"Health reminders task failed: {str(e)}")
            raise
    
    # Run the async function
    return asyncio.run(process_reminders())
    pass