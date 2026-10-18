"""
Queue router — live-updating simulated wait times and queue status.

GET  /api/queue/locations            — public (auth) list of active locations
GET  /api/queue/{location_id}        — current snapshot (polling)
GET  /api/queue/{location_id}/stream — SSE stream (token via query param)
POST /api/queue/{location_id}/walkin — walk-in check-in (creates entry)

All data is simulated.  Label: "Simulated live data".
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models.models import (
    Case,
    Location,
    QueueEntry,
    QueueEntryStatus,
    QueueEvent,
    QueueEventType,
    User,
)
from app.services.auth_service import decode_access_token
from app.services.deps import get_current_user
from app.services.queue_simulator import estimate_wait_from_history

router = APIRouter()

_DISCLAIMER = "Simulated live data — not an official SCDMV queue feed."


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class QueueStatusResponse(BaseModel):
    location_id: str
    waiting_count: int
    in_service_count: int
    called_count: int
    estimated_wait_minutes: int | None
    p50_service_minutes: float | None
    p90_service_minutes: float | None
    sample_size: int
    method: str
    queue_status: str   # "empty" | "quiet" | "active" | "busy"
    last_updated: str
    simulated: bool = True
    disclaimer: str = _DISCLAIMER


class LocationSummary(BaseModel):
    id: str
    name: str
    city: str
    is_demo: bool


class WalkInResponse(BaseModel):
    queue_entry_id: str
    position: int
    estimated_wait_minutes: int | None
    disclaimer: str = _DISCLAIMER


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_snapshot(db: Session, location_id: str) -> QueueStatusResponse:
    """Build a queue snapshot for one location."""
    waiting = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.location_id == location_id,
            QueueEntry.status == QueueEntryStatus.waiting,
        )
        .count()
    )
    in_service = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.location_id == location_id,
            QueueEntry.status == QueueEntryStatus.in_service,
        )
        .count()
    )
    called = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.location_id == location_id,
            QueueEntry.status == QueueEntryStatus.called,
        )
        .count()
    )

    est = estimate_wait_from_history(db, location_id, waiting, in_service)

    total_active = waiting + in_service + called
    if total_active == 0:
        queue_status = "empty"
    elif waiting <= 2:
        queue_status = "quiet"
    elif waiting <= 8:
        queue_status = "active"
    else:
        queue_status = "busy"

    return QueueStatusResponse(
        location_id=location_id,
        waiting_count=waiting,
        in_service_count=in_service,
        called_count=called,
        estimated_wait_minutes=est["estimated_wait_minutes"],
        p50_service_minutes=est["p50_service_minutes"],
        p90_service_minutes=est["p90_service_minutes"],
        sample_size=est["sample_size"],
        method=est["method"],
        queue_status=queue_status,
        last_updated=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/locations", response_model=list[LocationSummary])
def list_locations_public(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LocationSummary]:
    """Public (authenticated) list of active demo locations."""
    locs = db.query(Location).filter(Location.is_active.is_(True)).all()
    return [
        LocationSummary(id=l.id, name=l.name, city=l.city, is_demo=l.is_demo)
        for l in locs
    ]


@router.get("/{location_id}", response_model=QueueStatusResponse)
def get_queue_status(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueueStatusResponse:
    return _build_snapshot(db, location_id)


def _get_user_from_token_or_header(
    token: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    header_user: Optional[User] = Depends(get_current_user),
) -> User:
    """For SSE: accept token via query param (EventSource can't set headers)."""
    return header_user  # get_current_user already resolved it


@router.get("/{location_id}/stream")
async def stream_queue(
    location_id: str,
    token: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Server-Sent Events stream.  Sends a snapshot every 5 seconds.
    Each event is: data: <JSON>\\n\\n
    Token may be passed as ?token=<jwt> because EventSource cannot set headers.
    Clients handle reconnection automatically.
    """
    # Resolve user from query-param token (EventSource can't send headers)
    from jose import JWTError
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    async def event_generator():
        while True:
            # Use a fresh session per tick to avoid stale reads
            db = SessionLocal()
            try:
                snapshot = _build_snapshot(db, location_id)
                payload = snapshot.model_dump_json()
                yield f"data: {payload}\n\n"
            except Exception as exc:
                error_payload = json.dumps({"error": str(exc), "simulated": True})
                yield f"data: {error_payload}\n\n"
            finally:
                db.close()
            await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering
        },
    )


@router.post("/{location_id}/walkin", response_model=WalkInResponse)
def walk_in_checkin(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WalkInResponse:
    """
    Demo walk-in check-in: creates a queue entry directly for the current user.
    Requires the user to have an active (draft) case.
    """
    from app.models.models import CaseStatus

    case = (
        db.query(Case)
        .filter(
            Case.user_id == current_user.id,
            Case.status == CaseStatus.draft,
        )
        .order_by(Case.created_at.desc())
        .first()
    )
    if not case:
        raise HTTPException(
            status_code=400,
            detail="No active registration case found. Create a case before checking in.",
        )

    # Check for existing active queue entry
    existing = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.case_id == case.id,
            QueueEntry.status.in_([
                QueueEntryStatus.waiting,
                QueueEntryStatus.called,
                QueueEntryStatus.in_service,
            ]),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Already in queue for this case.")

    now = datetime.now(timezone.utc)
    entry = QueueEntry(
        case_id=case.id,
        location_id=location_id,
        is_walk_in=True,
        checked_in_at=now,
        status=QueueEntryStatus.waiting,
    )
    db.add(entry)
    db.flush()

    # Assign position
    position = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.location_id == location_id,
            QueueEntry.status == QueueEntryStatus.waiting,
        )
        .count()
    )
    entry.position = position

    db.add(QueueEvent(
        queue_entry_id=entry.id,
        event_type=QueueEventType.checked_in,
        payload={"walk_in": True},
        ts=now,
    ))
    db.commit()
    db.refresh(entry)

    est = estimate_wait_from_history(db, location_id, position, 0)

    return WalkInResponse(
        queue_entry_id=entry.id,
        position=position,
        estimated_wait_minutes=est["estimated_wait_minutes"],
    )
