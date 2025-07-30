"""
Version-agnostic Appointment Service

This service handles data access and core business logic for appointment-related
operations across all API versions.
"""

from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appointment


class AppointmentService:
    """Version-agnostic service for appointment data access and core business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # TODO: Implement appointment service methods in subsequent tasks
    pass