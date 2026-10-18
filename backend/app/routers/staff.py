"""
Staff router: queue management and dashboard metrics.
All data is synthetic demo data.

Endpoints:
  GET  /api/staff/queue/{location_id}           — active queue entries
  POST /api/staff/queue/{entry_id}/call         — call waiting customer
  POST /api/staff/queue/{entry_id}/start        — start service
  POST /api/staff/queue/{entry_id}/complete     — complete service
  POST /api/staff/queue/{entry_id}/flag         — flag for document issue
  POST /api/staff/queue/{entry_id}/no_show      — mark as no-show
  GET  /api/staff/appointments/{location_id}    — today's appointments
  GET  /api/staff/metrics/{location_id}         — dashboard metrics
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import (
    Appointment,
    AppointmentStatus,
    Case,
    QueueEntry,
    QueueEntryStatus,
    QueueEvent,
    QueueEventType,
    Slot,
    User,
    UserRole,
)
from app.services.deps import require_staff

router = APIRouter()

_DISCLAIMER = "Synthetic demo metrics — not real SCDMV data."


# ---------------------------------------------------------------------------
# Shared schemas
# ---------------------------------------------------------------------------

class QueueEntryDetail(BaseModel):
    id: str
    case_id: str
    location_id: str
    status: str
    position: int | None
    is_walk_in: bool
    checked_in_at: str | None
    called_at: str | None
    service_started_at: str | None
    service_completed_at: str | None
    flagged: bool
    wait_minutes: float | None       # minutes from check-in to now (or service start)
    service_minutes: float | None    # minutes from service_started_at to completed


def _entry_to_detail(e: QueueEntry) -> QueueEntryDetail:
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    wait: float | None = None
    if e.checked_in_at:
        end = e.service_started_at or now
        wait = round((end - e.checked_in_at).total_seconds() / 60, 1)

    svc: float | None = None
    if e.service_started_at and e.service_completed_at:
        svc = round((e.service_completed_at - e.service_started_at).total_seconds() / 60, 1)

    # "flagged" is stored as a doc_delay QueueEvent
    flagged = any(ev.event_type == QueueEventType.document_delay for ev in (e.events or []))

    return QueueEntryDetail(
        id=e.id,
        case_id=e.case_id,
        location_id=e.location_id,
        status=e.status.value,
        position=e.position,
        is_walk_in=e.is_walk_in,
        checked_in_at=e.checked_in_at.isoformat() if e.checked_in_at else None,
        called_at=e.called_at.isoformat() if e.called_at else None,
        service_started_at=e.service_started_at.isoformat() if e.service_started_at else None,
        service_completed_at=e.service_completed_at.isoformat() if e.service_completed_at else None,
        flagged=flagged,
        wait_minutes=wait,
        service_minutes=svc,
    )


# ---------------------------------------------------------------------------
# Queue list
# ---------------------------------------------------------------------------

@router.get("/queue/{location_id}", response_model=list[QueueEntryDetail])
def staff_queue(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> list[QueueEntryDetail]:
    entries = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.location_id == location_id,
            QueueEntry.status.in_([
                QueueEntryStatus.waiting,
                QueueEntryStatus.called,
                QueueEntryStatus.in_service,
            ]),
        )
        .order_by(QueueEntry.checked_in_at)
        .all()
    )
    # Eagerly load events to compute flagged status
    for e in entries:
        _ = e.events
    return [_entry_to_detail(e) for e in entries]


# ---------------------------------------------------------------------------
# Queue actions
# ---------------------------------------------------------------------------

@router.post("/queue/{entry_id}/call", status_code=200)
def call_customer(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    entry = db.get(QueueEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    if entry.status != QueueEntryStatus.waiting:
        raise HTTPException(status_code=400, detail="Entry is not in waiting status")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    entry.status = QueueEntryStatus.called
    entry.called_at = now
    entry.staff_id = current_user.id

    db.add(QueueEvent(
        queue_entry_id=entry.id,
        event_type=QueueEventType.called,
        payload={"staff_id": current_user.id},
        ts=now,
    ))

    # Create in-app notification for the case owner
    _create_notification(
        db=db,
        case_id=entry.case_id,
        title="You've been called!",
        body="A staff member is ready to see you. Please proceed to the service window.",
        notification_type="called",
        entry_id=entry.id,
    )

    db.commit()
    return {"message": "Customer called", "entry_id": entry.id}


@router.post("/queue/{entry_id}/start", status_code=200)
def start_service(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    entry = db.get(QueueEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    if entry.status not in (QueueEntryStatus.called, QueueEntryStatus.waiting):
        raise HTTPException(status_code=400, detail="Entry cannot start service from current status")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    entry.status = QueueEntryStatus.in_service
    entry.service_started_at = now

    db.add(QueueEvent(
        queue_entry_id=entry.id,
        event_type=QueueEventType.service_started,
        payload={"staff_id": current_user.id},
        ts=now,
    ))
    db.commit()
    return {"message": "Service started", "entry_id": entry.id}


@router.post("/queue/{entry_id}/complete", status_code=200)
def complete_service(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    entry = db.get(QueueEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    if entry.status not in (QueueEntryStatus.called, QueueEntryStatus.in_service):
        raise HTTPException(status_code=400, detail="Entry cannot be completed from current status")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Auto-set service_started_at if staff skipped that step
    if not entry.service_started_at:
        entry.service_started_at = now
    entry.status = QueueEntryStatus.completed
    entry.service_completed_at = now

    db.add(QueueEvent(
        queue_entry_id=entry.id,
        event_type=QueueEventType.service_completed,
        payload={"staff_id": current_user.id},
        ts=now,
    ))
    db.commit()
    return {"message": "Service completed", "entry_id": entry.id}


@router.post("/queue/{entry_id}/flag", status_code=200)
def flag_document_issue(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    """Flag a queue entry for a document-related delay."""
    entry = db.get(QueueEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    if entry.status not in (QueueEntryStatus.waiting, QueueEntryStatus.called,
                             QueueEntryStatus.in_service):
        raise HTTPException(status_code=400, detail="Cannot flag a closed entry")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(QueueEvent(
        queue_entry_id=entry.id,
        event_type=QueueEventType.document_delay,
        payload={"staff_id": current_user.id, "flagged_at": now.isoformat()},
        ts=now,
    ))
    db.commit()
    return {"message": "Entry flagged for document review", "entry_id": entry.id}


@router.post("/queue/{entry_id}/no_show", status_code=200)
def mark_no_show(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    """Mark a called customer as no-show (waited too long without responding)."""
    entry = db.get(QueueEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    if entry.status not in (QueueEntryStatus.waiting, QueueEntryStatus.called):
        raise HTTPException(status_code=400, detail="Can only mark waiting/called entries as no-show")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    entry.status = QueueEntryStatus.no_show
    entry.no_show_at = now

    db.add(QueueEvent(
        queue_entry_id=entry.id,
        event_type=QueueEventType.no_show,
        payload={"staff_id": current_user.id, "reason": "did_not_respond"},
        ts=now,
    ))
    db.commit()
    return {"message": "Marked as no-show", "entry_id": entry.id}


# ---------------------------------------------------------------------------
# Upcoming appointments
# ---------------------------------------------------------------------------

class AppointmentItem(BaseModel):
    id: str
    case_id: str
    confirmation_code: str
    status: str
    start_time: str
    is_checked_in: bool


@router.get("/appointments/{location_id}", response_model=list[AppointmentItem])
def upcoming_appointments(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> list[AppointmentItem]:
    """Return today's active appointments for a location."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    rows = (
        db.query(Appointment, Slot)
        .join(Slot, Slot.id == Appointment.slot_id)
        .filter(
            Slot.location_id == location_id,
            Slot.start_time >= today_start,
            Slot.start_time < today_end,
            Appointment.status.in_([
                AppointmentStatus.booked,
                AppointmentStatus.confirmed,
            ]),
        )
        .order_by(Slot.start_time)
        .all()
    )

    result = []
    for appt, slot in rows:
        # Check if a queue entry exists for this appointment
        checked_in = (
            db.query(QueueEntry)
            .filter(
                QueueEntry.appointment_id == appt.id,
                QueueEntry.status.in_([
                    QueueEntryStatus.waiting,
                    QueueEntryStatus.called,
                    QueueEntryStatus.in_service,
                ]),
            )
            .first()
        ) is not None
        result.append(AppointmentItem(
            id=appt.id,
            case_id=appt.case_id,
            confirmation_code=appt.confirmation_code,
            status=appt.status.value,
            start_time=slot.start_time.isoformat(),
            is_checked_in=checked_in,
        ))
    return result


# ---------------------------------------------------------------------------
# Dashboard metrics
# ---------------------------------------------------------------------------

class HourBucket(BaseModel):
    hour: int               # 0–23
    completed: int
    avg_service_minutes: float | None


class MetricsResponse(BaseModel):
    location_id: str
    period_hours: int
    total_completed: int
    total_no_shows: int
    total_doc_delays: int
    median_wait_minutes: float | None
    p90_wait_minutes: float | None
    median_service_minutes: float | None
    p90_service_minutes: float | None
    completions_by_hour: list[HourBucket]
    disclaimer: str = _DISCLAIMER


@router.get("/metrics/{location_id}", response_model=MetricsResponse)
def get_metrics(
    location_id: str,
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> MetricsResponse:
    hours = min(max(hours, 1), 168)  # clamp 1h–7d
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)

    # Completed entries in window
    completed_entries = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.location_id == location_id,
            QueueEntry.status == QueueEntryStatus.completed,
            QueueEntry.service_completed_at >= since,
        )
        .all()
    )

    # No-shows in window
    no_shows = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.location_id == location_id,
            QueueEntry.status == QueueEntryStatus.no_show,
            QueueEntry.no_show_at >= since,
        )
        .count()
    )

    # Document delay events in window
    doc_delays = (
        db.query(QueueEvent)
        .join(QueueEntry, QueueEntry.id == QueueEvent.queue_entry_id)
        .filter(
            QueueEntry.location_id == location_id,
            QueueEvent.event_type == QueueEventType.document_delay,
            QueueEvent.ts >= since,
        )
        .count()
    )

    # Wait times (check-in → service_started)
    wait_times: list[float] = []
    service_times: list[float] = []

    # Completions bucketed by hour of service_completed_at
    by_hour: dict[int, list[float]] = defaultdict(list)

    for e in completed_entries:
        if e.checked_in_at and e.service_started_at:
            w = (e.service_started_at - e.checked_in_at).total_seconds() / 60
            wait_times.append(w)
        if e.service_started_at and e.service_completed_at:
            s = (e.service_completed_at - e.service_started_at).total_seconds() / 60
            service_times.append(s)
            h = e.service_completed_at.hour
            by_hour[h].append(s)

    def _percentile(data: list[float], pct: float) -> float | None:
        if not data:
            return None
        s = sorted(data)
        idx = (len(s) - 1) * pct / 100
        lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
        return round(s[lo] + (s[hi] - s[lo]) * (idx - lo), 1)

    completions_by_hour = [
        HourBucket(
            hour=h,
            completed=len(times),
            avg_service_minutes=round(sum(times) / len(times), 1) if times else None,
        )
        for h, times in sorted(by_hour.items())
    ]

    return MetricsResponse(
        location_id=location_id,
        period_hours=hours,
        total_completed=len(completed_entries),
        total_no_shows=no_shows,
        total_doc_delays=doc_delays,
        median_wait_minutes=_percentile(wait_times, 50),
        p90_wait_minutes=_percentile(wait_times, 90),
        median_service_minutes=_percentile(service_times, 50),
        p90_service_minutes=_percentile(service_times, 90),
        completions_by_hour=completions_by_hour,
    )


# ---------------------------------------------------------------------------
# Internal helper — create in-app notification for a case's owner
# ---------------------------------------------------------------------------

def _create_notification(
    db: Session,
    case_id: str,
    title: str,
    body: str,
    notification_type: str,
    entry_id: str,
) -> None:
    """Insert a Notification row for the user who owns case_id."""
    from app.models.models import Notification  # avoid circular at module level
    case = db.get(Case, case_id)
    if not case:
        return
    notif = Notification(
        user_id=case.user_id,
        title=title,
        body=body,
        notification_type=notification_type,
        entity_id=entry_id,
    )
    db.add(notif)
    # caller must commit
