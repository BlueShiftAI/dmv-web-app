"""
Cases router: create, retrieve, and list registration cases.

Status transitions (simulated — not legally binding):
  Customer:  draft → submitted          POST /{id}/submit
  Staff:     submitted → in_review      PATCH /{id}/status  {"status": "in_review"}
             in_review → approved       PATCH /{id}/status  {"status": "approved"}
             in_review → rejected       PATCH /{id}/status  {"status": "rejected"}
             rejected  → in_review      PATCH /{id}/status  {"status": "in_review"}  (re-open)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Case, CaseStatus, Notification, User
from app.services.deps import get_current_user, require_staff

router = APIRouter()


class CaseCreateRequest(BaseModel):
    location_id: str | None = None
    scenario: str = "private_party_purchase"
    vin: str | None = None


class CaseResponse(BaseModel):
    id: str
    user_id: str
    status: str
    scenario: str
    vin: str | None
    created_at: str | None = None
    updated_at: str | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[CaseResponse])
def list_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CaseResponse]:
    cases = (
        db.query(Case)
        .filter(Case.user_id == current_user.id)
        .order_by(Case.created_at.desc())
        .all()
    )
    return [
        CaseResponse(
            id=c.id,
            user_id=c.user_id,
            status=c.status.value,
            scenario=c.scenario,
            vin=c.vin,
            created_at=c.created_at.isoformat() if c.created_at else None,
            updated_at=c.updated_at.isoformat() if c.updated_at else None,
        )
        for c in cases
    ]


@router.post("", response_model=CaseResponse, status_code=201)
def create_case(
    payload: CaseCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CaseResponse:
    if payload.scenario != "private_party_purchase":
        raise HTTPException(
            status_code=400,
            detail=(
                "This scenario isn\u2019t covered in this demo. "
                "Please visit scdmv.net or contact the Rock Hill SCDMV office directly."
            ),
        )
    case = Case(
        user_id=current_user.id,
        location_id=payload.location_id,
        scenario=payload.scenario,
        vin=payload.vin,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return CaseResponse(
        id=case.id,
        user_id=case.user_id,
        status=case.status.value,
        scenario=case.scenario,
        vin=case.vin,
        created_at=case.created_at.isoformat() if case.created_at else None,
        updated_at=case.updated_at.isoformat() if case.updated_at else None,
    )


# ---------------------------------------------------------------------------
# Staff: list submitted and in-review cases across all users
# (must be registered BEFORE the /{case_id} dynamic route)
# ---------------------------------------------------------------------------

@router.get("/pending", response_model=list[CaseResponse])
def list_pending_cases(
    db: Session = Depends(get_db),
    staff_user: User = Depends(require_staff),
) -> list[CaseResponse]:
    """
    Staff-only: return all cases in submitted or in_review status.
    Ordered newest first.
    """
    cases = (
        db.query(Case)
        .filter(Case.status.in_([CaseStatus.submitted, CaseStatus.in_review]))
        .order_by(Case.created_at.desc())
        .all()
    )
    return [
        CaseResponse(
            id=c.id,
            user_id=c.user_id,
            status=c.status.value,
            scenario=c.scenario,
            vin=c.vin,
            created_at=c.created_at.isoformat() if c.created_at else None,
            updated_at=c.updated_at.isoformat() if c.updated_at else None,
        )
        for c in cases
    ]


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CaseResponse:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.user_id != current_user.id and current_user.role.value not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    return CaseResponse(
        id=case.id,
        user_id=case.user_id,
        status=case.status.value,
        scenario=case.scenario,
        vin=case.vin,
        created_at=case.created_at.isoformat() if case.created_at else None,
        updated_at=case.updated_at.isoformat() if case.updated_at else None,
    )


# ---------------------------------------------------------------------------
# Customer: submit a case for staff review
# ---------------------------------------------------------------------------

@router.post("/{case_id}/submit", response_model=CaseResponse)
def submit_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CaseResponse:
    """
    Transition a case from draft → submitted.
    Only the case owner may submit; case must be in draft status.
    This is a simulated submission — no real government system is contacted.
    """
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if case.status != CaseStatus.draft:
        raise HTTPException(
            status_code=400,
            detail=f"Case cannot be submitted from status '{case.status.value}'. Only draft cases may be submitted.",
        )

    case.status = CaseStatus.submitted
    db.add(Notification(
        user_id=current_user.id,
        title="Case submitted for review",
        body=(
            "Your registration case has been submitted and is awaiting staff review. "
            "This is a simulated submission — not an official SCDMV filing."
        ),
        notification_type="info",
        entity_id=case_id,
    ))
    db.commit()
    db.refresh(case)
    return CaseResponse(
        id=case.id,
        user_id=case.user_id,
        status=case.status.value,
        scenario=case.scenario,
        vin=case.vin,
        created_at=case.created_at.isoformat() if case.created_at else None,
        updated_at=case.updated_at.isoformat() if case.updated_at else None,
    )


# ---------------------------------------------------------------------------
# Staff: advance or change case status
# ---------------------------------------------------------------------------

_STAFF_ALLOWED_TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.submitted: {CaseStatus.in_review},
    CaseStatus.in_review: {CaseStatus.approved, CaseStatus.rejected},
    CaseStatus.rejected:  {CaseStatus.in_review},   # re-open after customer corrects
}

_STATUS_NOTIFICATIONS: dict[CaseStatus, tuple[str, str]] = {
    CaseStatus.in_review: (
        "Your case is under review",
        "A staff member has started reviewing your registration case.",
    ),
    CaseStatus.approved: (
        "Case approved — preparation complete",
        (
            "Your registration preparation has been reviewed and approved. "
            "This is a demo approval only — bring your documents to the Rock Hill SCDMV office "
            "to complete the official registration."
        ),
    ),
    CaseStatus.rejected: (
        "Case returned — action required",
        (
            "Your registration case has been returned by staff. "
            "Please review the staff notes, correct any issues, and resubmit."
        ),
    ),
}


class CaseStatusUpdateRequest(BaseModel):
    status: str
    staff_notes: str | None = None


@router.patch("/{case_id}/status", response_model=CaseResponse)
def update_case_status(
    case_id: str,
    payload: CaseStatusUpdateRequest,
    db: Session = Depends(get_db),
    staff_user: User = Depends(require_staff),
) -> CaseResponse:
    """
    Staff-only: transition a case through the review lifecycle.
    Allowed transitions:
      submitted  → in_review
      in_review  → approved | rejected
      rejected   → in_review  (re-open)
    """
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    try:
        new_status = CaseStatus(payload.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown status '{payload.status}'")

    allowed = _STAFF_ALLOWED_TRANSITIONS.get(case.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot transition from '{case.status.value}' to '{new_status.value}'. "
                f"Allowed: {[s.value for s in allowed] or 'none'}"
            ),
        )

    case.status = new_status

    # Notify the case owner
    notif_title, notif_body = _STATUS_NOTIFICATIONS.get(
        new_status,
        ("Case status updated", f"Your case status changed to {new_status.value}."),
    )
    if payload.staff_notes:
        notif_body = f"{notif_body}\n\nStaff notes: {payload.staff_notes}"
    db.add(Notification(
        user_id=case.user_id,
        title=notif_title,
        body=notif_body,
        notification_type="info" if new_status == CaseStatus.in_review else (
            "success" if new_status == CaseStatus.approved else "warning"
        ),
        entity_id=case_id,
    ))

    db.commit()
    db.refresh(case)
    return CaseResponse(
        id=case.id,
        user_id=case.user_id,
        status=case.status.value,
        scenario=case.scenario,
        vin=case.vin,
        created_at=case.created_at.isoformat() if case.created_at else None,
        updated_at=case.updated_at.isoformat() if case.updated_at else None,
    )
