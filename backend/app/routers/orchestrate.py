"""
Orchestrate router — tool endpoints + chat proxy.

Tool endpoints are callable by the Orchestrate agent.
Every endpoint enforces authentication — the backend NEVER trusts a user ID
supplied by the model; it always resolves identity from the JWT.

Read-only tools: no additional confirmation required.
Write tools (book, cancel): require explicit `confirm_token == "CONFIRM"` in
the request body to prevent accidental or unconstrained agent actions.

All tool responses include a `simulated` flag and `disclaimer` field.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import (
    Appointment,
    AppointmentStatus,
    Case,
    QueueEntry,
    QueueEntryStatus,
    Slot,
    User,
)
from app.routers.appointments import _confirmation_code
from app.routers.queue import _build_snapshot
from app.services.deps import get_current_user
from app.services.orchestrate_service import (
    MOCK_DISCLAIMER,
    call_orchestrate,
    get_mock_response,
)

router = APIRouter()

_DISCLAIMER = (
    "Educational prototype. Not affiliated with the SCDMV. "
    "All data are simulated."
)


# ---------------------------------------------------------------------------
# Tool: checklist summary
# ---------------------------------------------------------------------------

@router.get("/tools/checklist")
def tool_checklist(
    case_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return checklist completion summary for a case."""
    from app.models.models import ChecklistItem, ChecklistItemStatus

    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    items = db.query(ChecklistItem).filter(ChecklistItem.case_id == case_id).all()
    total = len(items)
    reviewed = sum(1 for i in items if i.status == ChecklistItemStatus.reviewed)
    uploaded = sum(1 for i in items if i.status.value in ("uploaded", "uploaded_pending"))
    missing = sum(1 for i in items if i.status == ChecklistItemStatus.missing)
    flagged = sum(1 for i in items if i.status == ChecklistItemStatus.needs_replacement)

    return {
        "case_id": case_id,
        "total_items": total,
        "reviewed": reviewed,
        "uploaded_pending": uploaded,
        "missing": missing,
        "needs_replacement": flagged,
        "ready_to_proceed": missing == 0 and flagged == 0,
        "simulated": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Tool: draft summary
# ---------------------------------------------------------------------------

@router.get("/tools/draft")
def tool_draft(
    case_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return form draft completion status for a case."""
    from app.models.models import FormDraft

    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    draft = (
        db.query(FormDraft)
        .filter(FormDraft.case_id == case_id, FormDraft.form_type == "form_400")
        .order_by(FormDraft.version.desc())
        .first()
    )
    if not draft:
        return {
            "case_id": case_id,
            "form_type": "form_400",
            "has_draft": False,
            "is_complete": False,
            "version": 0,
            "simulated": True,
            "disclaimer": _DISCLAIMER,
        }

    data = draft.data or {}
    sections_filled = sum(
        1 for key in ("vehicle", "buyer", "seller", "purchase")
        if data.get(key)
    )
    return {
        "case_id": case_id,
        "form_type": draft.form_type,
        "has_draft": True,
        "is_complete": draft.is_complete,
        "version": draft.version,
        "sections_filled": sections_filled,
        "sections_total": 4,
        "has_vin": bool(data.get("vehicle", {}).get("vin") if isinstance(data.get("vehicle"), dict) else False),
        "simulated": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Tool: queue snapshot
# ---------------------------------------------------------------------------

@router.get("/tools/queue")
def tool_queue(
    location_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return current queue snapshot for a location."""
    snap = _build_snapshot(db, location_id)
    return snap.model_dump()


# ---------------------------------------------------------------------------
# Tool: tax status
# ---------------------------------------------------------------------------

@router.get("/tools/tax")
def tool_tax(
    vin: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return simulated tax status for a VIN."""
    from app.models.models import TaxRecord

    record = (
        db.query(TaxRecord)
        .filter(TaxRecord.vin == vin.upper())
        .order_by(TaxRecord.as_of_date.desc())
        .first()
    )
    if not record:
        return {
            "vin": vin.upper(),
            "status": "not_found",
            "provider": "York County Treasurer (Simulated)",
            "simulated": True,
            "disclaimer": _DISCLAIMER,
        }
    return {
        "vin": record.vin,
        "status": record.status.value,
        "amount_cents": record.amount_cents,
        "county": record.county,
        "tax_year": record.tax_year,
        "as_of_date": record.as_of_date.isoformat(),
        "provider": "York County Treasurer (Simulated)",
        "simulated": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Tool: ownership status
# ---------------------------------------------------------------------------

@router.get("/tools/ownership")
def tool_ownership(
    vin: str = Query(...),
    seller_name: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return simulated ownership match for a VIN and seller name."""
    from app.models.models import OwnershipRecord

    record = (
        db.query(OwnershipRecord)
        .filter(OwnershipRecord.vin == vin.upper())
        .order_by(OwnershipRecord.as_of_date.desc())
        .first()
    )
    if not record:
        return {
            "vin": vin.upper(),
            "status": "not_found",
            "provider": "SCDMV Title Records (Simulated)",
            "simulated": True,
            "disclaimer": _DISCLAIMER,
        }

    name_match = seller_name.strip().lower() in record.owner_name.lower()
    return {
        "vin": record.vin,
        "status": "match" if name_match else "no_match",
        "record_owner_name": record.owner_name,
        "county": record.county,
        "as_of_date": record.as_of_date.isoformat(),
        "provider": "SCDMV Title Records (Simulated)",
        "simulated": True,
        "disclaimer": (
            _DISCLAIMER + " A simulated match does NOT legally verify ownership or "
            "authority to sell. Original signed title is required."
        ),
    }


# ---------------------------------------------------------------------------
# Tool: available slots
# ---------------------------------------------------------------------------

@router.get("/tools/slots")
def tool_slots(
    location_id: str = Query(...),
    date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return available appointment slots for a location and date."""
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
    available = [
        {
            "id": s.id,
            "start_time": s.start_time.isoformat(),
            "end_time": s.end_time.isoformat(),
            "capacity": s.capacity,
            "booked_count": s.booked_count,
            "available": s.booked_count < s.capacity,
        }
        for s in slots
        if s.booked_count < s.capacity
    ]
    return {
        "location_id": location_id,
        "date": date,
        "available_count": len(available),
        "slots": available,
        "simulated": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Tool: book appointment (write — requires explicit confirmation token)
# ---------------------------------------------------------------------------

class BookToolRequest(BaseModel):
    case_id: str
    slot_id: str
    confirm_token: str   # must equal "CONFIRM" — prevents silent agent booking


@router.post("/tools/book")
def tool_book(
    payload: BookToolRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Book an appointment via Orchestrate tool.
    Requires confirm_token == 'CONFIRM' to prevent unconstrained agent booking.
    """
    if payload.confirm_token != "CONFIRM":
        raise HTTPException(
            status_code=400,
            detail=(
                "confirm_token must be 'CONFIRM'. "
                "The assistant must display the proposed booking to the user "
                "and receive explicit approval before calling this tool."
            ),
        )

    case = db.get(Case, payload.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    slot = db.query(Slot).with_for_update().filter(Slot.id == payload.slot_id).first()
    if not slot or not slot.is_active:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.booked_count >= slot.capacity:
        raise HTTPException(status_code=409, detail="Slot is fully booked")

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
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    db.refresh(slot)

    return {
        "appointment_id": appt.id,
        "confirmation_code": appt.confirmation_code,
        "start_time": slot.start_time.isoformat(),
        "status": appt.status.value,
        "simulated": True,
        "disclaimer": (
            "Prototype appointment booked. Not an official SCDMV booking. "
            "Does not guarantee immediate service at the appointment time."
        ),
    }


# ---------------------------------------------------------------------------
# Tool: cancel appointment (write — requires explicit confirmation token)
# ---------------------------------------------------------------------------

class CancelToolRequest(BaseModel):
    appointment_id: str
    confirm_token: str


@router.post("/tools/cancel")
def tool_cancel(
    payload: CancelToolRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Cancel an appointment via Orchestrate tool. Requires confirm_token == 'CONFIRM'."""
    if payload.confirm_token != "CONFIRM":
        raise HTTPException(
            status_code=400,
            detail="confirm_token must be 'CONFIRM'.",
        )

    appt = db.get(Appointment, payload.appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    case = db.get(Case, appt.case_id)
    if case.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if appt.status in (AppointmentStatus.cancelled, AppointmentStatus.completed):
        raise HTTPException(status_code=400, detail="Appointment is already closed")

    appt.status = AppointmentStatus.cancelled
    appt.cancelled_at = datetime.now(timezone.utc).replace(tzinfo=None)

    slot = db.get(Slot, appt.slot_id)
    if slot and slot.booked_count > 0:
        slot.booked_count -= 1

    db.commit()
    return {
        "appointment_id": appt.id,
        "status": "cancelled",
        "simulated": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Chat proxy endpoint
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    orchestrate_enabled: bool
    simulated: bool
    disclaimer: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """
    Chat proxy. Routes to real Orchestrate when configured, mock otherwise.
    Never exposes credentials to the browser.
    """
    from app.config import settings

    session_id = payload.session_id or str(uuid.uuid4())

    if settings.orchestrate_enabled:
        try:
            reply = await call_orchestrate(
                session_id=session_id,
                message=payload.message,
                history=payload.history,
            )
            return ChatResponse(
                reply=reply,
                session_id=session_id,
                orchestrate_enabled=True,
                simulated=False,
                disclaimer=(
                    "Responses powered by IBM watsonx Orchestrate. "
                    "The assistant must not invent requirements or override "
                    "backend data. Always verify at scdmv.net."
                ),
            )
        except Exception as exc:
            # Fall back to mock on any Orchestrate error
            reply = (
                f"_(Orchestrate unavailable: {type(exc).__name__}. "
                f"Falling back to demo mode.)_\n\n"
                + get_mock_response(payload.message)
            )
            return ChatResponse(
                reply=reply,
                session_id=session_id,
                orchestrate_enabled=False,
                simulated=True,
                disclaimer=MOCK_DISCLAIMER,
            )
    else:
        reply = get_mock_response(payload.message)
        return ChatResponse(
            reply=reply,
            session_id=session_id,
            orchestrate_enabled=False,
            simulated=True,
            disclaimer=MOCK_DISCLAIMER,
        )
