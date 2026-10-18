"""Initial schema — all tables

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("customer","staff","admin", name="userrole"), nullable=False, server_default="customer"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # locations
    op.create_table(
        "locations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text, nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state", sa.String(2), nullable=False, server_default="SC"),
        sa.Column("zip_code", sa.String(10), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="America/New_York"),
        sa.Column("is_demo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )

    # cases
    op.create_table(
        "cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("location_id", sa.String(36), sa.ForeignKey("locations.id")),
        sa.Column("status", sa.Enum("draft","submitted","in_review","approved","rejected","completed", name="casestatus"), nullable=False, server_default="draft"),
        sa.Column("scenario", sa.String(100), nullable=False, server_default="private_party_purchase"),
        sa.Column("vin", sa.String(17)),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_cases_user_id", "cases", ["user_id"])
    op.create_index("ix_cases_vin", "cases", ["vin"])

    # form_drafts
    op.create_table(
        "form_drafts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("form_type", sa.String(50), nullable=False),
        sa.Column("data", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_complete", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_form_drafts_case_id", "form_drafts", ["case_id"])

    # checklist_items
    op.create_table(
        "checklist_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("requirement_key", sa.String(100), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_conditional", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("condition_note", sa.Text),
        sa.Column("status", sa.Enum("missing","uploaded","reviewed","needs_replacement","waived", name="checklistitemstatus"), nullable=False, server_default="missing"),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_checklist_items_case_id", "checklist_items", ["case_id"])

    # documents
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("checklist_item_id", sa.String(36), sa.ForeignKey("checklist_items.id")),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_filename", sa.String(255), nullable=False, unique=True),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("status", sa.Enum("uploaded_pending","reviewed","needs_replacement", name="documentstatus"), nullable=False, server_default="uploaded_pending"),
        sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("reviewed_at", sa.DateTime),
        sa.Column("staff_notes", sa.Text),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_documents_case_id", "documents", ["case_id"])

    # slots
    op.create_table(
        "slots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("location_id", sa.String(36), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("start_time", sa.DateTime, nullable=False),
        sa.Column("end_time", sa.DateTime, nullable=False),
        sa.Column("capacity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("booked_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("location_id", "start_time", name="uq_slot_location_start"),
    )
    op.create_index("ix_slots_location_id", "slots", ["location_id"])

    # appointments
    op.create_table(
        "appointments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("slot_id", sa.String(36), sa.ForeignKey("slots.id"), nullable=False),
        sa.Column("status", sa.Enum("booked","confirmed","cancelled","no_show","completed", name="appointmentstatus"), nullable=False, server_default="booked"),
        sa.Column("confirmation_code", sa.String(12), nullable=False, unique=True),
        sa.Column("booked_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime),
        sa.Column("cancelled_at", sa.DateTime),
        sa.Column("cancellation_reason", sa.Text),
        sa.Column("notes", sa.Text),
    )
    op.create_index("ix_appointments_case_id", "appointments", ["case_id"])

    # queue_entries
    op.create_table(
        "queue_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("location_id", sa.String(36), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("appointment_id", sa.String(36), sa.ForeignKey("appointments.id")),
        sa.Column("status", sa.Enum("waiting","called","in_service","completed","no_show","cancelled", name="queueentrystatus"), nullable=False, server_default="waiting"),
        sa.Column("position", sa.Integer),
        sa.Column("is_walk_in", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("checked_in_at", sa.DateTime),
        sa.Column("called_at", sa.DateTime),
        sa.Column("service_started_at", sa.DateTime),
        sa.Column("service_completed_at", sa.DateTime),
        sa.Column("no_show_at", sa.DateTime),
        sa.Column("staff_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_queue_entries_case_id", "queue_entries", ["case_id"])
    op.create_index("ix_queue_entries_location_id", "queue_entries", ["location_id"])

    # queue_events
    op.create_table(
        "queue_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("queue_entry_id", sa.String(36), sa.ForeignKey("queue_entries.id"), nullable=False),
        sa.Column("event_type", sa.Enum("arrived","checked_in","called","service_started","service_completed","document_delay","no_show","cancelled", name="queueeventtype"), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("ts", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_queue_events_queue_entry_id", "queue_events", ["queue_entry_id"])

    # tax_records
    op.create_table(
        "tax_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("vin", sa.String(17), nullable=False),
        sa.Column("status", sa.Enum("paid","unpaid","not_found","provider_unavailable", name="taxstatus"), nullable=False),
        sa.Column("amount_cents", sa.Integer),
        sa.Column("county", sa.String(100), nullable=False, server_default="York County"),
        sa.Column("tax_year", sa.Integer),
        sa.Column("as_of_date", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text),
    )
    op.create_index("ix_tax_records_vin", "tax_records", ["vin"])

    # ownership_records
    op.create_table(
        "ownership_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("vin", sa.String(17), nullable=False),
        sa.Column("owner_name", sa.String(255), nullable=False),
        sa.Column("owner_id_hash", sa.String(64)),
        sa.Column("county", sa.String(100), nullable=False, server_default="York County"),
        sa.Column("plate_number", sa.String(20)),
        sa.Column("title_number", sa.String(50)),
        sa.Column("as_of_date", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("is_demo", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_ownership_records_vin", "ownership_records", ["vin"])

    # push_subscriptions
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("endpoint", sa.Text, nullable=False),
        sa.Column("keys", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])

    # audit_events
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100)),
        sa.Column("entity_id", sa.String(36)),
        sa.Column("payload", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("ts", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"])

    # notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False, server_default="info"),
        sa.Column("entity_id", sa.String(36)),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("audit_events")
    op.drop_table("push_subscriptions")
    op.drop_table("ownership_records")
    op.drop_table("tax_records")
    op.drop_table("queue_events")
    op.drop_table("queue_entries")
    op.drop_table("appointments")
    op.drop_table("slots")
    op.drop_table("documents")
    op.drop_table("checklist_items")
    op.drop_table("form_drafts")
    op.drop_table("cases")
    op.drop_table("locations")
    op.drop_table("users")
    # drop enums
    for e in ["userrole","casestatus","checklistitemstatus","documentstatus",
              "appointmentstatus","queueentrystatus","queueeventtype","taxstatus","ownershipstatus"]:
        sa.Enum(name=e).drop(op.get_bind(), checkfirst=True)
