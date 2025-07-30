"""
Celery application configuration.
"""
from celery import Celery

from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "vet_clinic",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.notification_tasks",
        "app.tasks.report_tasks",
        "app.tasks.maintenance_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Task routing
celery_app.conf.task_routes = {
    "app.tasks.notification_tasks.*": {"queue": "notifications"},
    "app.tasks.report_tasks.*": {"queue": "reports"},
    "app.tasks.maintenance_tasks.*": {"queue": "maintenance"},
}