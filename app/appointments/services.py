"""
Version-agnostic Appointment Service

This service handles data access and core business logic for appointment-related
operations across all API versions. It supports dynamic parameters to
accommodate different API version requirements.
"""

from typing import List, Tuple, Optional, Dict, Any, Union
from datetime import datetime, date, timedelta
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, delete, String
from sqlalchemy.orm import selectinload

from app.models.appointment import (
    Appointment, 
    AppointmentSlot, 
    AppointmentStatus, 
    AppointmentType, 
    AppointmentPriority
)
from app.core.exceptions import VetClinicException, NotFoundError, ValidationError


class AppointmentService:
    """Version-agnostic service for appointment data access and core business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_appointments(
        self,
        page: int = 1,
        per_page: int = 10,
        pet_id: Optional[uuid.UUID] = None,
        pet_owner_id: Optional[uuid.UUID] = None,
        veterinarian_id: Optional[uuid.UUID] = None,
        clinic_id: Optional[uuid.UUID] = None,
        status: Optional[Union[AppointmentStatus, str]] = None,
        appointment_type: Optional[Union[AppointmentType, str]] = None,
        priority: Optional[Union[AppointmentPriority, str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        upcoming_only: bool = False,
        today_only: bool = False,
        include_pet: bool = False,  # V2 parameter
        include_owner: bool = False,  # V2 parameter
        include_veterinarian: bool = False,  # V2 parameter
        include_clinic: bool = False,  # V2 parameter
        sort_by: Optional[str] = None,  # V2 parameter
        **kwargs
    ) -> Tuple[List[Appointment], int]:
        """
        List appointments with pagination and filtering.
        Supports dynamic parameters for different API versions.
        
        Args:
            page: Page number (1-based)
            per_page: Items per page
            pet_id: Filter by pet ID
            pet_owner_id: Filter by pet owner ID
            veterinarian_id: Filter by veterinarian ID
            clinic_id: Filter by clinic ID
            status: Filter by appointment status
            appointment_type: Filter by appointment type
            priority: Filter by priority
            start_date: Filter by start date
            end_date: Filter by end date
            upcoming_only: Show only upcoming appointments
            today_only: Show only today's appointments
            include_pet: Include pet information (V2)
            include_owner: Include owner information (V2)
            include_veterinarian: Include veterinarian information (V2)
            include_clinic: Include clinic information (V2)
            sort_by: Sort by field (V2)
            **kwargs: Additional parameters for future versions
            
        Returns:
            Tuple of (appointments list, total count)
        """
        try:
            # Build base query
            query = select(Appointment)
            count_query = select(func.count(Appointment.id))
            
            # Apply filters
            conditions = []
            
            if pet_id:
                conditions.append(Appointment.pet_id == pet_id)
            
            if pet_owner_id:
                conditions.append(Appointment.pet_owner_id == pet_owner_id)
            
            if veterinarian_id:
                conditions.append(Appointment.veterinarian_id == veterinarian_id)
            
            if clinic_id:
                conditions.append(Appointment.clinic_id == clinic_id)
            
            if status:
                if isinstance(status, str):
                    try:
                        status = AppointmentStatus(status)
                    except ValueError:
                        raise ValidationError(f"Invalid appointment status: {status}")
                conditions.append(Appointment.status == status)
            
            if appointment_type:
                if isinstance(appointment_type, str):
                    try:
                        appointment_type = AppointmentType(appointment_type)
                    except ValueError:
                        raise ValidationError(f"Invalid appointment type: {appointment_type}")
                conditions.append(Appointment.appointment_type == appointment_type)
            
            if priority:
                if isinstance(priority, str):
                    try:
                        priority = AppointmentPriority(priority)
                    except ValueError:
                        raise ValidationError(f"Invalid priority: {priority}")
                conditions.append(Appointment.priority == priority)
            
            # Date filters
            if start_date:
                start_datetime = datetime.combine(start_date, datetime.min.time())
                conditions.append(Appointment.scheduled_at >= start_datetime)
            
            if end_date:
                end_datetime = datetime.combine(end_date, datetime.max.time())
                conditions.append(Appointment.scheduled_at <= end_datetime)
            
            if upcoming_only:
                now = datetime.utcnow()
                conditions.append(Appointment.scheduled_at > now)
                conditions.append(Appointment.status.in_([
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED
                ]))
            
            if today_only:
                today = datetime.utcnow().date()
                start_of_day = datetime.combine(today, datetime.min.time())
                end_of_day = datetime.combine(today, datetime.max.time())
                conditions.append(Appointment.scheduled_at.between(start_of_day, end_of_day))
            
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
            
            # Add relationships if requested (V2)
            if include_pet:
                query = query.options(selectinload(Appointment.pet))
            
            if include_owner:
                query = query.options(selectinload(Appointment.pet_owner))
            
            if include_veterinarian:
                query = query.options(selectinload(Appointment.veterinarian))
            
            if include_clinic:
                query = query.options(selectinload(Appointment.clinic))
            
            # Get total count
            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Apply sorting (V2 feature)
            if sort_by:
                if sort_by == "scheduled_at":
                    query = query.order_by(Appointment.scheduled_at)
                elif sort_by == "scheduled_at_desc":
                    query = query.order_by(Appointment.scheduled_at.desc())
                elif sort_by == "priority":
                    # Custom priority ordering
                    query = query.order_by(Appointment.priority.desc())
                elif sort_by == "status":
                    query = query.order_by(Appointment.status)
                elif sort_by == "created_at":
                    query = query.order_by(Appointment.created_at.desc())
                else:
                    query = query.order_by(Appointment.scheduled_at)
            else:
                query = query.order_by(Appointment.scheduled_at)
            
            # Apply pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            # Execute query
            result = await self.db.execute(query)
            appointments = result.scalars().all()
            
            return list(appointments), total
            
        except Exception as e:
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to list appointments: {str(e)}")

    async def get_appointment_by_id(
        self,
        appointment_id: uuid.UUID,
        include_pet: bool = False,
        include_owner: bool = False,
        include_veterinarian: bool = False,
        include_clinic: bool = False,
        **kwargs
    ) -> Appointment:
        """
        Get appointment by ID with optional related data.
        
        Args:
            appointment_id: Appointment UUID
            include_pet: Include pet information (V2)
            include_owner: Include owner information (V2)
            include_veterinarian: Include veterinarian information (V2)
            include_clinic: Include clinic information (V2)
            **kwargs: Additional parameters for future versions
            
        Returns:
            Appointment object
            
        Raises:
            NotFoundError: If appointment not found
        """
        try:
            query = select(Appointment).where(Appointment.id == appointment_id)
            
            # Add optional relationships based on version needs
            if include_pet:
                query = query.options(selectinload(Appointment.pet))
            
            if include_owner:
                query = query.options(selectinload(Appointment.pet_owner))
            
            if include_veterinarian:
                query = query.options(selectinload(Appointment.veterinarian))
            
            if include_clinic:
                query = query.options(selectinload(Appointment.clinic))
            
            result = await self.db.execute(query)
            appointment = result.scalar_one_or_none()
            
            if not appointment:
                raise NotFoundError(f"Appointment with id {appointment_id} not found")
            
            return appointment
            
        except Exception as e:
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(f"Failed to get appointment by id: {str(e)}")

    async def create_appointment(
        self,
        pet_id: uuid.UUID,
        pet_owner_id: uuid.UUID,
        veterinarian_id: uuid.UUID,
        clinic_id: uuid.UUID,
        appointment_type: Union[AppointmentType, str],
        scheduled_at: datetime,
        reason: str,
        duration_minutes: int = 30,
        priority: Union[AppointmentPriority, str] = AppointmentPriority.NORMAL,
        symptoms: Optional[str] = None,
        notes: Optional[str] = None,
        special_instructions: Optional[str] = None,
        services_requested: Optional[List[str]] = None,
        estimated_cost: Optional[float] = None,
        follow_up_required: bool = False,
        follow_up_date: Optional[datetime] = None,
        follow_up_notes: Optional[str] = None,
        **kwargs
    ) -> Appointment:
        """
        Create a new appointment.
        Supports dynamic parameters for different API versions.
        
        try:
            # Handle enum pa
            if isinstance(appointment_ty:
                try:
                    appointment_type)
                except ValueError:
                    raise ValidationError(f"Inval
            
            if isinstance(priority, str):
                try:
                    priority = App
                except ValueError:
                    raise ValidationError(f"Invalid pr")
            
            # Validate scheduled time is i
            if scheduled_at <= datetime.utcnow():
                raise ValidationError("App")
            
            # Create appointment data
            a = {
                t_id,
                "pet_owner_id": pet_owr_id,
            d,
               
                "appointment_type": appointment_,
           _at,
            ,
                "priority": priority
                "reason": reason.strip(),
                "sym
                "notes": notes.strip() if notes else None,
                "special_instructi
                "services_requested": services_requested,
            
                "follow_up_required": fol,
                "folp_date,
                "follow_up_notes": follow_up_notes.strip() i
                "status": AppointmHEDULED
            }
            
            # Create new appointment
            new_appointment = Appointment(**appoi)
            
            tment)
            await self.db.commit()
            await self.db.refres)
            
            return new_appointment
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
                raise
            raise VetClinicException(")

    async def update_appointment(
        self,
        appointment_id: uuid.UUID,
        scheduled_at: Optional[datetime] = None,
        appointment_type: Optional[Union[Appointm
        priority: Optional[Union[AppointmentPriority, str
        reason: Optional[str] = None,
        symptoms: Optional[str] = None,
        notes: Optional[str] = None,
        speci
        serv
        estimated_cost: Optional[floe,
        actual_cost: Optional[float] = None,
        foll,
        follow_up_date: Optional[datetim= None,
        follow_up_notes: Optional[
        duration_minutes: Optional[int] = None,
        **kw
    ) -> Appointment:
        """U""
        try:
            appointment = await self
            
            # Update ded
            if scheduled_at is not None:

                    raise Validate")
             at
            
            if appointment_type is not None:
                if isinstance(appointment_type, str):
                    try:
                        appointment_t_type)
                    except ValueError:
                        raise Valida
                appointment.appointment_type = appope
            
            if priority is not None:
                if isinstance(priority, str):
                    try:
                        priority = AppointmentPrioority)
                    except ValueError:
                        raise ValidationError(f")
                y
            
           e:
                appointment.reason = rep()
            if symptoms is not None:
        se None
            if nNone:
                appointment.notes = no
           t None:
            
            if services_requested is not None:
            
            if estimated_cost is not None:
                appointment.estimated_coed_cost
            if actual_cost is not None:
                appointment.actual_cost = actual_cost
            if follow_up_required is not None:
            p_required
            if follow_up_date is not None:
                appointment.follow_up_date = follow_u
            if follow_up
                appointment.follow_up_notes = follow_up_notes.strip() if fol
            if duration_minutes is notone:
                appointment.duration_minutes = duration_minutes
            
            
            await self.db.refresh(ap)
            
            return appoi
            
        except Exception as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException
            
            raise VetClinicExcepti)

    async def cancel_appointment(
        self,
        appointment_id: uuid.UUID,
        cancellation_reason: Optional[str] = None
    ) -> Appointment:
        """Cancel an appointment."""
        try:
            appointment = await self.get_appointment_by_id(appointm
            
            if not hasattr(appointment, "can_be_cancelled")
                raise ValidationError(fcelled")
            
            appointment.cancel(cancellation_re
            
            await self.db.commit()
            await self.db.refresh(appointment)
            
            return appointment
            
        except Exception as e:
            
            if isinstance(e, VetCl:
                raise
            )

    async de:
        """Confirm an appointm
        try:
            appointment = await self.get_appointm
            
            if appointment.status != AppointmentStatus.SCHEDULED:
rmed")
            
            a
            
            await self.db.commit()
            await selent)
            
            return appointment
           
        excepon as e:
            await self.db.rollback()
            if isinstance(e, VetClinicException):
            e
            raistr(e)}")

    async dt:
        """Snt."""
        try:
            
            
            if appointment.status not in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]:
            ted")
            
            ()
            
            await self.db.commit()
            
            
            ent
            
        except Exception as e:
            await self.db.rollback()
            if isinst
                raise
}")

    async dt(
        self,
        
        actua
    ) -> Appointment:
        """C
        try:
            appointment = await self.gntment_id)
            
            S:
                raise ValidationError(f"Only in-progress appointments can ted")
            
            appointment.complete(actual_cost)
            
            it()
            await self.db.refreshent)
            
            return appointment
            
        exce
            await self.db.roll)
            on):
                raise
            raise VetClinicException

    async def resched
        self,
,
        new_scheduled_at: datetime
    ) -> Ap
        """Reschedule an appo
        ry:
            ad)
            
            uled:
                ")
            
           
            e")
            
            nd status
            appointment.scheduled_at = new_scheduled_at
            appointment.status = AppointmentStatus.SCHEDULED  # Reset to scheduled
            n
            
            mit()
            await self.db.refresh()
            
            tment
            
        exce as e:
            await self.db.rollk()
            if isinstance(e, VetClinion):
                raise
            raise Vet

) -> None:
        """Hard delete an appointme"
        try:
            appointment = await se)
            
            await selointment)
           t()
            
         as e:
            ak()
            if isinstance(e, VetClinicExcepton):
                raise
            ")

    async def get_available_slots(
        self,
        vete
        clinic_id: uuid.UUID,
        starate,
        end_date: Optional[date] = None,
        duration_minutes: int = 30,
        **kwargs
    ) -> List[AppointmentSlot]:
        """G"
        try:
            if end_date is None:
            
            
            e())
            end_datetime = dat())
            
            query = select(AppointmentSlot).where
                and_(
                    AppointmentSlot.veterinarian_id == veterinarian_id,

                    AppointmentSlot.setime,
             
                    AppointmentSlo
                    AppointmentSlolse,
                    A
           
            ).order_by(Appointment)
            
            ry)
            slots = result.scalars().all()
            
            ts
            avai
            
           slots
            
        except Exception as e:
            e)}")

    async def get_calendar_view(
        self,
        veterinarian_id: Optional[uuid.UUID] = None,
        clinic_id: Optional[uuid.UUID] = None,
        star= None,
        end_date: Optional[date] = None,
        view_type: str = "week",
        **kwargs
    ) -> Dict[str, Any]:
        """G""
        try:
            if start_date is None:
            ate()
            
            ype
            if end_date is None:
                if view_type == "day:
                    end_date = start_date
                elif ":
                    end_date = start_date + timedelta(days=6)
:
                    # Get last day of the month
            == 12:
                        end_date = ays=1)
        :
             1)
                else:
           
            
            start_datetime = datetime.combine(start_date, datetime.min.time())
            me())
            
            # Build appointment qu
            re(
                and_(
                    Appointment.scheme,
                    Appointment.scheduled_at <= eetime
                )
            ).options(
pet),
                selectinload(Appointmeowner),
             
                selectinlo)
            )
            
            # Ap filters
            if veterinarian_id:
           
            if clinic_id:
        linic_id)
            
            appointment_quert)
            
            # Get appointments
            appointment_result = await self.db.execute(appointm
            ).all()
            
            # Build availability query
           
            _(
                    AppointmentSlot.start_time >= start_datetime,
            
                    AppointmentS,
                    AppointmentSlot.is_se
                )
            )
            
            
                slot_d)
            if clinic_id:
            id)
            
            slot_query = slot_query.order_by(Appotime)
            
            # Get available slots
            y)
            slots = slot_resul()
            
ar
            calendar_appointments = []
            fintments:
                calendar_appointmenpend({
                    "id": str(appointment.,
                    "title": f"{appointm",
                
                    "end_ti
           es,
                    "status": appointment.status.value,
        ue,
             
                    "pet_id": str(appointment.
                    "pet_name": appointment. None,
                    "pet_owner_id": str(
                    "pet_owner_name": f"{appointment.pet_owner.ne,
            d),
                one,
                    "clinic_id":id),
           ,
            ost,
                    "actual_cost": appointment.actual_cost,
            
                    "can_buled
                })
            
             calendar
            available_slts = []
            for slot in slots:
                if not slot.is_fully_booked:
            
                        "id": str(slot.id),
            ),
                        "end_time": slot.end_timet(),
                        "duration_minutes": slot.tes,
            ot_type,
                        "remaining_ca,
            
                        "clini_id),
                        "is_available": True

            
            #s
            total_appointments = le
            appointments_by_s = {}
            for appointme
                status = appointment.staalue
                appointments_by_sta0) + 1
            
            # Calculate utilizate
           
            booked_slots = len([slot for> 0])
        e 0
            
            return {
                "view_type": view_
                "start_date": start_date.isoformat),
                "end_date": end_date.isoformat),
                "appointments": calendar_appointments,
                "available_slots": available_slots,
            
                ,
                    "appointments_by_status": a_status,
           ,
            )
                },
                "filters": {
            None,
                    "clinic_id": str(clinic_id) if clinic_id else None
                }
            }
            
        except Except
            raise VetClinicException(f"Failed to get calendar view: {st

    async def check_appointment_conflicts(
        self,
        veterinarian_id: uuid.UUID,
        scheduled_at: datetime,
        duration_minutes: int = 30,
        exclude_a= None,
        **kwargs
    ) -> Lisment]:
        """Check for appointment conflicts before
        try:
            king
            appointment_start = scheduled_at
            appointment_end = scheduled_at + timedelta(minutes=duration_minutes)
            
            # Build conflict queryh
            
            query = select(Apphere(
                and_(
n_id,
                    Appointment.us.in_([
             
                        AppointmentStatus.CONFIRMED,
                        AppointmentStatus.IN_PS
                    ]),
                    # Check for time ovee
                    # and ends a
                d,
                    functetime(
           duled_at, 
                        '+' + func.cast(Appointment.durationutes'
        at
             
            ).options(
                selectinload(Appointment.pet),
                selectinload(Appointment.peowner)
            )
            
            # Exclude specific appointment if provided (for resuling)
            :
                d)
            
           ery)
            l()
            
            return list(conflicts)
            
        except Exception as e:
            raise VetClinicExcep")(e)}: {strctsonflitment cppoink aled to checFaiion(f"t
    a
sync def get_appointment_statistics(
        self,
        veterinarian_id: Optional[uuid.UUID] = None,
        clinic_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Get appointment statistics for reporting and analytics."""
        try:
            # Default to current month if no dates provided
            if start_date is None:
                today = datetime.utcnow().date()
                start_date = date(today.year, today.month, 1)
            
            if end_date is None:
                # Get last day of the month
                if start_date.month == 12:
                    end_date = date(start_date.year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
            
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            # Build base query
            query = select(Appointment).where(
                and_(
                    Appointment.scheduled_at >= start_datetime,
                    Appointment.scheduled_at <= end_datetime
                )
            )
            
            # Apply filters
            if veterinarian_id:
                query = query.where(Appointment.veterinarian_id == veterinarian_id)
            if clinic_id:
                query = query.where(Appointment.clinic_id == clinic_id)
            
            result = await self.db.execute(query)
            appointments = result.scalars().all()
            
            # Calculate statistics
            total_appointments = len(appointments)
            
            # Count by status
            status_counts = {}
            for status in AppointmentStatus:
                status_counts[status.value] = 0
            
            for appointment in appointments:
                status_counts[appointment.status.value] += 1
            
            # Count by type
            type_counts = {}
            for appointment_type in AppointmentType:
                type_counts[appointment_type.value] = 0
            
            for appointment in appointments:
                type_counts[appointment.appointment_type.value] += 1
            
            # Count by priority
            priority_counts = {}
            for priority in AppointmentPriority:
                priority_counts[priority.value] = 0
            
            for appointment in appointments:
                priority_counts[appointment.priority.value] += 1
            
            # Calculate revenue statistics
            total_estimated_revenue = sum(
                appointment.estimated_cost or 0 
                for appointment in appointments 
                if appointment.estimated_cost
            )
            
            total_actual_revenue = sum(
                appointment.actual_cost or 0 
                for appointment in appointments 
                if appointment.actual_cost and appointment.status == AppointmentStatus.COMPLETED
            )
            
            completed_appointments = [
                appointment for appointment in appointments 
                if appointment.status == AppointmentStatus.COMPLETED
            ]
            
            average_appointment_cost = (
                total_actual_revenue / len(completed_appointments) 
                if completed_appointments else 0
            )
            
            # Calculate completion rate
            scheduled_or_confirmed = len([
                appointment for appointment in appointments 
                if appointment.status in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED]
            ])
            
            completion_rate = (
                status_counts[AppointmentStatus.COMPLETED.value] / scheduled_or_confirmed * 100
                if scheduled_or_confirmed > 0 else 0
            )
            
            # Calculate no-show rate
            no_show_rate = (
                status_counts[AppointmentStatus.NO_SHOW.value] / total_appointments * 100
                if total_appointments > 0 else 0
            )
            
            # Calculate cancellation rate
            cancellation_rate = (
                status_counts[AppointmentStatus.CANCELLED.value] / total_appointments * 100
                if total_appointments > 0 else 0
            )
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "filters": {
                    "veterinarian_id": str(veterinarian_id) if veterinarian_id else None,
                    "clinic_id": str(clinic_id) if clinic_id else None
                },
                "totals": {
                    "total_appointments": total_appointments,
                    "completed_appointments": len(completed_appointments),
                    "total_estimated_revenue": round(total_estimated_revenue, 2),
                    "total_actual_revenue": round(total_actual_revenue, 2),
                    "average_appointment_cost": round(average_appointment_cost, 2)
                },
                "counts_by_status": status_counts,
                "counts_by_type": type_counts,
                "counts_by_priority": priority_counts,
                "rates": {
                    "completion_rate": round(completion_rate, 2),
                    "no_show_rate": round(no_show_rate, 2),
                    "cancellation_rate": round(cancellation_rate, 2)
                }
            }
            
        except Exception as e:
            raise VetClinicException(f"Failed to get appointment statistics: {str(e)}")

    async def create_appointment_slots(
        self,
        veterinarian_id: uuid.UUID,
        clinic_id: uuid.UUID,
        start_date: date,
        end_date: date,
        start_time: str = "09:00",
        end_time: str = "17:00",
        slot_duration: int = 30,
        break_duration: int = 0,
        exclude_weekends: bool = True,
        **kwargs
    ) -> List[AppointmentSlot]:
        """Create appointment slots for a veterinarian at a clinic."""
        try:
            created_slots = []
            current_date = start_date
            
            # Parse start and end times
            start_hour, start_minute = map(int, start_time.split(':'))
            end_hour, end_minute = map(int, end_time.split(':'))
            
            while current_date <= end_date:
                # Skip weekends if requested
                if exclude_weekends and current_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                    current_date += timedelta(days=1)
                    continue
                
                # Create slots for the current day
                current_time = datetime.combine(current_date, datetime.min.time()).replace(
                    hour=start_hour, minute=start_minute
                )
                day_end_time = datetime.combine(current_date, datetime.min.time()).replace(
                    hour=end_hour, minute=end_minute
                )
                
                while current_time + timedelta(minutes=slot_duration) <= day_end_time:
                    slot_end_time = current_time + timedelta(minutes=slot_duration)
                    
                    # Check if slot already exists
                    existing_slot_query = select(AppointmentSlot).where(
                        and_(
                            AppointmentSlot.veterinarian_id == veterinarian_id,
                            AppointmentSlot.clinic_id == clinic_id,
                            AppointmentSlot.start_time == current_time
                        )
                    )
                    
                    existing_result = await self.db.execute(existing_slot_query)
                    existing_slot = existing_result.scalar_one_or_none()
                    
                    if not existing_slot:
                        # Create new slot
                        new_slot = AppointmentSlot(
                            veterinarian_id=veterinarian_id,
                            clinic_id=clinic_id,
                            start_time=current_time,
                            end_time=slot_end_time,
                            duration_minutes=slot_duration,
                            is_available=True,
                            is_blocked=False,
                            slot_type="regular",
                            max_bookings=1,
                            current_bookings=0
                        )
                        
                        self.db.add(new_slot)
                        created_slots.append(new_slot)
                    
                    # Move to next slot
                    current_time = slot_end_time + timedelta(minutes=break_duration)
                
                current_date += timedelta(days=1)
            
            await self.db.commit()
            
            # Refresh all created slots
            for slot in created_slots:
                await self.db.refresh(slot)
            
            return created_slots
            
        except Exception as e:
            await self.db.rollback()
            raise VetClinicException(f"Failed to create appointment slots: {str(e)}")