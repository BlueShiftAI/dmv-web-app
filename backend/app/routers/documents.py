"""
Documents router: upload, list, delete document files.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.models import Case, ChecklistItemStatus, Document, DocumentStatus, User
from app.services.deps import get_current_user

router = APIRouter()

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
# Minimal magic-byte signatures
MAGIC_BYTES: dict[bytes, str] = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"RIFF": "image/webp",
    b"%PDF": "application/pdf",
}


class DocumentResponse(BaseModel):
    id: str
    original_filename: str
    storage_filename: str
    mime_type: str
    size_bytes: int
    status: str
    checklist_item_id: str | None
    created_at: str

    model_config = {"from_attributes": True}


def _validate_magic(data: bytes, declared_mime: str) -> None:
    for magic, mime in MAGIC_BYTES.items():
        if data.startswith(magic):
            if mime != declared_mime:
                raise HTTPException(status_code=400, detail="File content does not match declared type")
            return
    raise HTTPException(status_code=400, detail="Unrecognised file signature")


@router.post("/{case_id}/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    case_id: str,
    file: UploadFile = File(...),
    checklist_item_id: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.user_id != current_user.id and current_user.role.value not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    data = await file.read()
    if len(data) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    _validate_magic(data[:8], file.content_type)

    storage_filename = f"{uuid.uuid4()}_{Path(file.filename).name}"
    dest_dir = Path(settings.upload_dir) / case_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / storage_filename

    with open(dest_path, "wb") as f:
        f.write(data)

    doc = Document(
        case_id=case_id,
        checklist_item_id=checklist_item_id,
        original_filename=file.filename,
        storage_filename=storage_filename,
        storage_path=str(dest_path),
        mime_type=file.content_type,
        size_bytes=len(data),
        uploaded_by=current_user.id,
    )
    db.add(doc)

    # Update checklist item status if linked
    if checklist_item_id:
        from app.models.models import ChecklistItem
        item = db.get(ChecklistItem, checklist_item_id)
        if item and item.case_id == case_id:
            item.status = ChecklistItemStatus.uploaded

    db.commit()
    db.refresh(doc)
    return DocumentResponse(
        id=doc.id,
        original_filename=doc.original_filename,
        storage_filename=doc.storage_filename,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        status=doc.status.value,
        checklist_item_id=doc.checklist_item_id,
        created_at=doc.created_at.isoformat(),
    )


@router.get("/{case_id}/documents", response_model=list[DocumentResponse])
def list_documents(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentResponse]:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.user_id != current_user.id and current_user.role.value not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    return [
        DocumentResponse(
            id=d.id,
            original_filename=d.original_filename,
            storage_filename=d.storage_filename,
            mime_type=d.mime_type,
            size_bytes=d.size_bytes,
            status=d.status.value,
            checklist_item_id=d.checklist_item_id,
            created_at=d.created_at.isoformat(),
        )
        for d in case.documents
    ]


@router.delete("/{case_id}/documents/{doc_id}", status_code=204, response_class=Response)
def delete_document(
    case_id: str,
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.user_id != current_user.id and current_user.role.value not in ("staff", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")

    doc = db.get(Document, doc_id)
    if not doc or doc.case_id != case_id:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove file from storage
    try:
        os.remove(doc.storage_path)
    except FileNotFoundError:
        pass  # already gone — still clean up DB record

    db.delete(doc)
    db.commit()
    return Response(status_code=204)
