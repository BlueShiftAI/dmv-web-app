"""
Notifications router — in-app alerts for customers.

GET  /api/notifications          — list unread (and recent read) notifications
POST /api/notifications/{id}/read — mark one notification as read
POST /api/notifications/read_all  — mark all as read
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Notification, User
from app.services.deps import get_current_user

router = APIRouter()


class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    notification_type: str
    entity_id: str | None
    is_read: bool
    created_at: str


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 30,
) -> list[NotificationResponse]:
    """Return up to `limit` most-recent notifications for the current user."""
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        NotificationResponse(
            id=n.id,
            title=n.title,
            body=n.body,
            notification_type=n.notification_type,
            entity_id=n.entity_id,
            is_read=n.is_read,
            created_at=n.created_at.isoformat(),
        )
        for n in rows
    ]


@router.post("/{notif_id}/read", status_code=200)
def mark_read(
    notif_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    notif = db.get(Notification, notif_id)
    if notif and notif.user_id == current_user.id:
        notif.is_read = True
        db.commit()
    return {"ok": True}


@router.post("/read_all", status_code=200)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False),
    ).update({"is_read": True})
    db.commit()
    return {"ok": True}
