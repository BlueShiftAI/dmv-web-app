"""
Appointments router: slots, booking, cancellation, check-in.
All slots and appointments are simulated demo data.
"""
from __future__ import annotations

import random
import string
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Appointment, AppointmentStatus, Case, QueueEntry, Slot, User
from app.services.deps import get_current_user

router = APIRouter()


def _confirmation_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SlotResponse(BaseModel):
    id: str
    location_id: str
    start_time: str
    end_time: str
    capacity: int
    booked_count: int
    available: bool

    model_config = {"from_attributes": True}


class BookRequest(BaseModel):
    case_id: str
    slot_id: str
    notes: str | None = None


class AppointmentResponse(BaseModel):
    id: str
    case_id: str
    slot_id: str
    status: str
    confirmation_code: str
    booked_at: str
    start_time: str
    disclaimer: str = (
        "This is a prototype appointment, not an official SCDMV booking. "
        "It does not guarantee immediate service at the appointment time."
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=AppointmentResponse | None)
def get_appointment_for_case(
    case_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AppointmentResponse | None:
    """Return the active (booked/confirmed) appointment for a case, if any."""
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    appt = (
        db.query(Appointment)
        .join(Slot, Slot.id == Appointment.slot_id)
        .filter(
            Appointment.case_id == case_id,
            Appointment.status.in_([AppointmentStatus.booked, AppointmentStatus.confirmed]),
        )
        .first()
    )
    if not appt:
        return None  # FastAPI serialises None -> null

    slot = db.get(Slot, appt.slot_id)
    return AppointmentResponse(
        id=appt.id,
        case_id=appt.case_id,
        slot_id=appt.slot_id,
        status=appt.status.value,
        confirmation_code=appt.confirmation_code,
        booked_at=appt.booked_at.isoformat(),
        start_time=slot.start_time.isoformat(),
    )


@router.get("/slots", response_model=list[SlotResponse])
def list_slots(
    location_id: str = Query(...),
    date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SlotResponse]:
    try:
        date_dt = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")

    slots = (
        db.query(Slot)
        .filter(
            Slot.location_id == location_id,
            Slot.is_active.is_(True),
            Slot.start_time >= date_dt,
            Slot.start_time < date_dt.replace(hour=23, minute=59),
        )
        .order_by(Slot.start_time)
        .all()
    )
    return [
        SlotResponse(
            id=s.id,
            location_id=s.location_id,
            start_time=s.start_time.isoformat(),
            end_time=s.end_time.isoformat(),
            capacity=s.capacity,
            booked_count=s.booked_count,
            available=s.booked_count < s.capacity,
        )
        for s in slots
    ]


@router.post("", response_model=AppointmentResponse, status_code=201)
def book_appointment(
    payload: BookRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AppointmentResponse:
    case = db.get(Case, payload.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Lock the slot row to prevent double-booking
    slot = db.query(Slot).with_for_update().filter(Slot.id == payload.slot_id).first()
    if not slot or not slot.is_active:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.booked_count >= slot.capacity:
        raise HTTPException(status_code=409, detail="Slot is fully booked")

    # Check for existing active appointment on this case
    existing = (
        db.query(Appointment)
        .filter(
            Appointment.case_id == payload.case_id,
            Appointment.status.in_([AppointmentStatus.booked, AppointmentStatus.confirmed]),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Case already has an active appointment")

    slot.booked_count += 1
    appt = Appointment(
        case_id=payload.case_id,
        slot_id=payload.slot_id,
        confirmation_code=_confirmation_code(),
        notes=payload.notes,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    db.refresh(slot)

    return AppointmentResponse(
        id=appt.id,
        case_id=appt.case_id,
        slot_id=appt.slot_id,
        status=appt.status.value,
        confirmation_code=appt.confirmation_code,
        booked_at=appt.booked_at.isoformat(),
        start_time=slot.start_time.isoformat(),
    )


@router.delete("/{appt_id}", status_code=204, response_class=Response)
def cancel_appointment(
    appt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    appt = db.get(Appointment, appt_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    case = db.get(Case, appt.case_id)
    if case.user_id != current_user.id and current_user.role.value not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    if appt.status in (AppointmentStatus.cancelled, AppointmentStatus.completed):
        raise HTTPException(status_code=400, detail="Appointment already closed")

    appt.status = AppointmentStatus.cancelled
    appt.cancelled_at = datetime.utcnow()

    slot = db.get(Slot, appt.slot_id)
    if slot and slot.booked_count > 0:
        slot.booked_count -= 1

    db.commit()
    return Response(status_code=204)


@router.post("/{appt_id}/checkin", status_code=200)
def checkin(
    appt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    appt = db.get(Appointment, appt_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    case = db.get(Case, appt.case_id)
    if case.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if appt.status == AppointmentStatus.cancelled:
        raise HTTPException(status_code=400, detail="Appointment is cancelled")

    appt.status = AppointmentStatus.confirmed
    appt.confirmed_at = datetime.utcnow()

    slot = db.get(Slot, appt.slot_id)
    entry = QueueEntry(
        case_id=case.id,
        location_id=slot.location_id,
        appointment_id=appt.id,
        checked_in_at=datetime.utcnow(),
        is_walk_in=False,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {"message": "Checked in", "queue_entry_id": entry.id}
