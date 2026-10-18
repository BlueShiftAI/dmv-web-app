"""
Draft router: save and resume Form 400 draft data.
GET  /api/cases/{case_id}/draft           — retrieve current draft
PUT  /api/cases/{case_id}/draft           — save/update draft (partial ok)
GET  /api/cases/{case_id}/draft/pdf       — download PDF preparation summary
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Case, FormDraft, User
from app.schemas.form_400 import FORM_400_METADATA, Form400Draft
from app.services.deps import get_current_user
from app.services.pdf_service import generate_preparation_pdf

router = APIRouter()

FORM_TYPE = "form_400"


class DraftResponse(BaseModel):
    id: str
    case_id: str
    form_type: str
    data: dict
    version: int
    is_complete: bool
    updated_at: str
    metadata: dict


class DraftUpdateRequest(BaseModel):
    data: dict
    is_complete: bool = False


def _get_case_authorized(case_id: str, current_user: User, db: Session) -> Case:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.user_id != current_user.id and current_user.role.value not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    return case


@router.get("/{case_id}/draft", response_model=DraftResponse)
def get_draft(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DraftResponse:
    case = _get_case_authorized(case_id, current_user, db)

    draft = (
        db.query(FormDraft)
        .filter(FormDraft.case_id == case_id, FormDraft.form_type == FORM_TYPE)
        .first()
    )
    if not draft:
        # Auto-create an empty draft
        draft = FormDraft(case_id=case_id, form_type=FORM_TYPE, data={})
        db.add(draft)
        db.commit()
        db.refresh(draft)

    return DraftResponse(
        id=draft.id,
        case_id=draft.case_id,
        form_type=draft.form_type,
        data=draft.data,
        version=draft.version,
        is_complete=draft.is_complete,
        updated_at=draft.updated_at.isoformat(),
        metadata=FORM_400_METADATA,
    )


@router.put("/{case_id}/draft", response_model=DraftResponse)
def save_draft(
    case_id: str,
    payload: DraftUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DraftResponse:
    case = _get_case_authorized(case_id, current_user, db)

    # Validate the incoming data shape (partial validation — all sections optional)
    try:
        Form400Draft.model_validate(payload.data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    draft = (
        db.query(FormDraft)
        .filter(FormDraft.case_id == case_id, FormDraft.form_type == FORM_TYPE)
        .first()
    )
    if not draft:
        draft = FormDraft(case_id=case_id, form_type=FORM_TYPE, data=payload.data)
        db.add(draft)
    else:
        draft.data = payload.data
        draft.version += 1
        draft.is_complete = payload.is_complete

    # Update case VIN if provided in vehicle section
    vehicle = payload.data.get("vehicle")
    if vehicle and vehicle.get("vin"):
        case.vin = vehicle["vin"].upper()

    db.commit()
    db.refresh(draft)

    return DraftResponse(
        id=draft.id,
        case_id=draft.case_id,
        form_type=draft.form_type,
        data=draft.data,
        version=draft.version,
        is_complete=draft.is_complete,
        updated_at=draft.updated_at.isoformat(),
        metadata=FORM_400_METADATA,
    )


@router.get("/{case_id}/draft/pdf")
def download_pdf(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    case = _get_case_authorized(case_id, current_user, db)

    draft = (
        db.query(FormDraft)
        .filter(FormDraft.case_id == case_id, FormDraft.form_type == FORM_TYPE)
        .first()
    )
    draft_data = draft.data if draft else {}

    pdf_bytes = generate_preparation_pdf(case_id=case_id, draft_data=draft_data)

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="dmv-prep-summary-{case_id[:8]}.pdf"'
        },
    )
