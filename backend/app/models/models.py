"""
SQLAlchemy ORM models for the DMV Web App.

Covers:
  - Users and roles
  - Locations
  - Registration cases and form drafts
  - Requirements / checklist items
  - Uploaded document metadata
  - Appointment slots and appointments
  - Queue entries and timestamped events
  - Synthetic tax and ownership records
  - Push-notification subscriptions
  - Audit events
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    customer = "customer"
    staff = "staff"
    admin = "admin"


class CaseStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    completed = "completed"


class ChecklistItemStatus(str, enum.Enum):
    missing = "missing"
    uploaded = "uploaded"
    reviewed = "reviewed"
    needs_replacement = "needs_replacement"
    waived = "waived"


class DocumentStatus(str, enum.Enum):
    uploaded_pending = "uploaded_pending"
    reviewed = "reviewed"
    needs_replacement = "needs_replacement"


class AppointmentStatus(str, enum.Enum):
    booked = "booked"
    confirmed = "confirmed"
    cancelled = "cancelled"
    no_show = "no_show"
    completed = "completed"


class QueueEntryStatus(str, enum.Enum):
    waiting = "waiting"
    called = "called"
    in_service = "in_service"
    completed = "completed"
    no_show = "no_show"
    cancelled = "cancelled"


class QueueEventType(str, enum.Enum):
    arrived = "arrived"
    checked_in = "checked_in"
    called = "called"
    service_started = "service_started"
    service_completed = "service_completed"
    document_delay = "document_delay"
    no_show = "no_show"
    cancelled = "cancelled"


class TaxStatus(str, enum.Enum):
    paid = "paid"
    unpaid = "unpaid"
    not_found = "not_found"
    provider_unavailable = "provider_unavailable"


class OwnershipStatus(str, enum.Enum):
    match = "match"
    no_match = "no_match"
    not_found = "not_found"
    provider_unavailable = "provider_unavailable"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.customer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    cases: Mapped[list["Case"]] = relationship("Case", back_populates="user")
    push_subscriptions: Mapped[list["PushSubscription"]] = relationship(
        "PushSubscription", back_populates="user"
    )
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="user")
    audit_events: Mapped[list["AuditEvent"]] = relationship("AuditEvent", back_populates="user")


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------

class Location(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False, default="SC")
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    timezone: Mapped[str] = mapped_column(String(50), default="America/New_York")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    slots: Mapped[list["Slot"]] = relationship("Slot", back_populates="location")
    queue_entries: Mapped[list["QueueEntry"]] = relationship(
        "QueueEntry", back_populates="location"
    )


# ---------------------------------------------------------------------------
# Registration Cases
# ---------------------------------------------------------------------------

class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    location_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("locations.id"))
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus), default=CaseStatus.draft)
    scenario: Mapped[str] = mapped_column(String(100), default="private_party_purchase")
    vin: Mapped[str | None] = mapped_column(String(17), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    user: Mapped["User"] = relationship("User", back_populates="cases")
    location: Mapped["Location | None"] = relationship("Location")
    form_drafts: Mapped[list["FormDraft"]] = relationship("FormDraft", back_populates="case")
    checklist_items: Mapped[list["ChecklistItem"]] = relationship(
        "ChecklistItem", back_populates="case"
    )
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="case")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="case")
    queue_entries: Mapped[list["QueueEntry"]] = relationship("QueueEntry", back_populates="case")


# ---------------------------------------------------------------------------
# Form Drafts
# ---------------------------------------------------------------------------

class FormDraft(Base):
    __tablename__ = "form_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    form_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "form_400"
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    case: Mapped["Case"] = relationship("Case", back_populates="form_drafts")


# ---------------------------------------------------------------------------
# Checklist Items
# ---------------------------------------------------------------------------

class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    requirement_key: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    is_conditional: Mapped[bool] = mapped_column(Boolean, default=False)
    condition_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ChecklistItemStatus] = mapped_column(
        Enum(ChecklistItemStatus), default=ChecklistItemStatus.missing
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    case: Mapped["Case"] = relationship("Case", back_populates="checklist_items")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="checklist_item")


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    checklist_item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("checklist_items.id")
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.uploaded_pending
    )
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    staff_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    case: Mapped["Case"] = relationship("Case", back_populates="documents")
    checklist_item: Mapped["ChecklistItem | None"] = relationship(
        "ChecklistItem", back_populates="documents"
    )


# ---------------------------------------------------------------------------
# Appointment Slots
# ---------------------------------------------------------------------------

class Slot(Base):
    __tablename__ = "slots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    location_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("locations.id"), nullable=False, index=True
    )
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # UTC
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)    # UTC
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    booked_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    location: Mapped["Location"] = relationship("Location", back_populates="slots")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="slot")

    __table_args__ = (
        UniqueConstraint("location_id", "start_time", name="uq_slot_location_start"),
    )


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------

class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    slot_id: Mapped[str] = mapped_column(String(36), ForeignKey("slots.id"), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus), default=AppointmentStatus.booked
    )
    confirmation_code: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    booked_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    case: Mapped["Case"] = relationship("Case", back_populates="appointments")
    slot: Mapped["Slot"] = relationship("Slot", back_populates="appointments")


# ---------------------------------------------------------------------------
# Queue Entries
# ---------------------------------------------------------------------------

class QueueEntry(Base):
    __tablename__ = "queue_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    location_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("locations.id"), nullable=False, index=True
    )
    appointment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("appointments.id"))
    status: Mapped[QueueEntryStatus] = mapped_column(
        Enum(QueueEntryStatus), default=QueueEntryStatus.waiting
    )
    position: Mapped[int | None] = mapped_column(Integer)
    is_walk_in: Mapped[bool] = mapped_column(Boolean, default=False)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime)
    called_at: Mapped[datetime | None] = mapped_column(DateTime)
    service_started_at: Mapped[datetime | None] = mapped_column(DateTime)
    service_completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    no_show_at: Mapped[datetime | None] = mapped_column(DateTime)
    staff_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    case: Mapped["Case"] = relationship("Case", back_populates="queue_entries")
    location: Mapped["Location"] = relationship("Location", back_populates="queue_entries")
    events: Mapped[list["QueueEvent"]] = relationship("QueueEvent", back_populates="queue_entry")


# ---------------------------------------------------------------------------
# Queue Events (immutable audit log of queue state transitions)
# ---------------------------------------------------------------------------

class QueueEvent(Base):
    __tablename__ = "queue_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    queue_entry_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("queue_entries.id"), nullable=False, index=True
    )
    event_type: Mapped[QueueEventType] = mapped_column(Enum(QueueEventType), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ts: Mapped[datetime] = mapped_column(DateTime, default=_now)

    queue_entry: Mapped["QueueEntry"] = relationship("QueueEntry", back_populates="events")


# ---------------------------------------------------------------------------
# Synthetic Tax Records
# ---------------------------------------------------------------------------

class TaxRecord(Base):
    __tablename__ = "tax_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    vin: Mapped[str] = mapped_column(String(17), nullable=False, index=True)
    status: Mapped[TaxStatus] = mapped_column(Enum(TaxStatus), nullable=False)
    amount_cents: Mapped[int | None] = mapped_column(Integer)  # in cents
    county: Mapped[str] = mapped_column(String(100), default="York County")
    tax_year: Mapped[int | None] = mapped_column(Integer)
    as_of_date: Mapped[datetime] = mapped_column(DateTime, default=_now)
    notes: Mapped[str | None] = mapped_column(Text)


# ---------------------------------------------------------------------------
# Synthetic Ownership Records
# ---------------------------------------------------------------------------

class OwnershipRecord(Base):
    __tablename__ = "ownership_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    vin: Mapped[str] = mapped_column(String(17), nullable=False, index=True)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Hashed for demo — never store real SSN or DL number
    owner_id_hash: Mapped[str | None] = mapped_column(String(64))
    county: Mapped[str] = mapped_column(String(100), default="York County")
    plate_number: Mapped[str | None] = mapped_column(String(20))
    title_number: Mapped[str | None] = mapped_column(String(50))
    as_of_date: Mapped[datetime] = mapped_column(DateTime, default=_now)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


# ---------------------------------------------------------------------------
# In-App Notifications
# ---------------------------------------------------------------------------

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, default="info")
    entity_id: Mapped[str | None] = mapped_column(String(36))   # queue_entry_id, appt_id, etc.
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped["User"] = relationship("User", back_populates="notifications")


# ---------------------------------------------------------------------------
# Push Notification Subscriptions
# ---------------------------------------------------------------------------

class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    keys: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped["User"] = relationship("User", back_populates="push_subscriptions")


# ---------------------------------------------------------------------------
# Audit Events
# ---------------------------------------------------------------------------

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    ts: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped["User | None"] = relationship("User", back_populates="audit_events")
