"""
Checklist router: generate and retrieve checklist items for a case.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Case, ChecklistItem, ChecklistItemStatus, User
from app.requirements_config.sc_private_party import REQUIRED_DOCUMENTS
from app.services.deps import get_current_user

router = APIRouter()


class ChecklistItemResponse(BaseModel):
    id: str
    requirement_key: str
    label: str
    description: str | None
    is_required: bool
    is_conditional: bool
    condition_note: str | None
    status: str

    model_config = {"from_attributes": True}


def _assert_case_access(case: Case | None, current_user: User) -> Case:
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.user_id != current_user.id and current_user.role.value not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    return case


@router.get("/{case_id}/checklist", response_model=list[ChecklistItemResponse])
def get_checklist(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChecklistItemResponse]:
    case = db.get(Case, case_id)
    case = _assert_case_access(case, current_user)

    # Auto-generate items if not yet created
    if not case.checklist_items:
        for doc in REQUIRED_DOCUMENTS:
            item = ChecklistItem(
                case_id=case.id,
                requirement_key=doc["key"],
                label=doc["label"],
                description=doc.get("description"),
                is_required=doc.get("is_required", True),
                is_conditional=doc.get("is_conditional", False),
                condition_note=doc.get("condition_note"),
                status=ChecklistItemStatus.missing,
            )
            db.add(item)
        db.commit()
        db.refresh(case)

    return [ChecklistItemResponse.model_validate(i) for i in case.checklist_items]
