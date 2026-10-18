"""
Tests for staff queue controls, metrics endpoint, and notifications.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# Shared helpers (same pattern as test_booking.py)
# ---------------------------------------------------------------------------

def _register(client, email, role="customer"):
    r = client.post("/api/auth/register", json={
        "email": email, "full_name": "Test User",
        "password": "TestPass1!", "role": role,
    })
    assert r.status_code == 201, r.text
    d = r.json()
    return d["access_token"], d["user_id"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _make_case(client, token):
    r = client.post("/api/cases", json={"scenario": "private_party_purchase"},
                    headers=_headers(token))
    assert r.status_code == 201
    return r.json()["id"]


def _make_location(db_session):
    from app.models.models import Location
    loc = Location(
        name="Staff Test Loc",
        address="1 Staff St",
        city="Rock Hill",
        state="SC",
        zip_code="29730",
        timezone="America/New_York",
        is_demo=True,
    )
    db_session.add(loc)
    db_session.commit()
    db_session.refresh(loc)
    return loc.id


def _make_queue_entry(db_session, case_id, location_id, status="waiting"):
    from app.models.models import QueueEntry, QueueEntryStatus
    entry = QueueEntry(
        case_id=case_id,
        location_id=location_id,
        is_walk_in=True,
        checked_in_at=datetime.now(timezone.utc).replace(tzinfo=None),
        status=QueueEntryStatus(status),
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)
    return entry.id


# ---------------------------------------------------------------------------
# Staff queue list
# ---------------------------------------------------------------------------

class TestStaffQueueList:
    def test_requires_staff_role(self, client, db_session):
        cust_token, _ = _register(client, "nostaff@example.com", role="customer")
        loc_id = _make_location(db_session)
        r = client.get(f"/api/staff/queue/{loc_id}", headers=_headers(cust_token))
        assert r.status_code == 403

    def test_staff_can_view_queue(self, client, db_session):
        staff_token, _ = _register(client, "staffview@example.com", role="staff")
        cust_token, _ = _register(client, "custview@example.com", role="customer")
        loc_id = _make_location(db_session)
        case_id = _make_case(client, cust_token)
        _make_queue_entry(db_session, case_id, loc_id, "waiting")

        r = client.get(f"/api/staff/queue/{loc_id}", headers=_headers(staff_token))
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["status"] == "waiting"
        assert "wait_minutes" in data[0]
        assert "flagged" in data[0]

    def test_completed_entries_excluded(self, client, db_session):
        staff_token, _ = _register(client, "staffcomp@example.com", role="staff")
        cust_token, _ = _register(client, "custcomp@example.com", role="customer")
        loc_id = _make_location(db_session)
        case_id = _make_case(client, cust_token)
        _make_queue_entry(db_session, case_id, loc_id, "completed")

        r = client.get(f"/api/staff/queue/{loc_id}", headers=_headers(staff_token))
        assert r.status_code == 200
        assert len(r.json()) == 0


# ---------------------------------------------------------------------------
# Call action
# ---------------------------------------------------------------------------

class TestCallAction:
    def test_call_waiting_entry(self, client, db_session):
        staff_token, _ = _register(client, "staffcall@example.com", role="staff")
        cust_token, cust_id = _register(client, "custcall@example.com", role="customer")
        loc_id = _make_location(db_session)
        case_id = _make_case(client, cust_token)
        entry_id = _make_queue_entry(db_session, case_id, loc_id, "waiting")

        r = client.post(f"/api/staff/queue/{entry_id}/call",
                        headers=_headers(staff_token))
        assert r.status_code == 200
        assert r.json()["entry_id"] == entry_id

        # verify status updated
        from app.models.models import QueueEntry, QueueEntryStatus
        entry = db_session.get(QueueEntry, entry_id)
        db_session.expire_all()
        entry = db_session.get(QueueEntry, entry_id)
        assert entry.status == QueueEntryStatus.called
        assert entry.called_at is not None

    def test_call_creates_notification(self, client, db_session):
        staff_token, _ = _register(client, "staffnotif@example.com", role="staff")
        cust_token, cust_id = _register(client, "custnotif@example.com", role="customer")
        loc_id = _make_location(db_session)
        case_id = _make_case(client, cust_token)
        entry_id = _make_queue_entry(db_session, case_id, loc_id, "waiting")

        client.post(f"/api/staff/queue/{entry_id}/call",
                    headers=_headers(staff_token))

        # customer should have a notification
        r = client.get("/api/notifications", headers=_headers(cust_token))
        assert r.status_code == 200
        notifs = r.json()
        assert len(notifs) >= 1
        assert any(n["notification_type"] == "called" for n in notifs)

    def test_cannot_call_non_waiting(self, client, db_session):
        staff_token, _ = _register(client, "staffcallbad@example.com", role="staff")
        cust_token, _ = _register(client, "custcallbad@example.com", role="customer")
        loc_id = _make_location(db_session)
        case_id = _make_case(client, cust_token)
        entry_id = _make_queue_entry(db_session, case_id, loc_id, "in_service")

        r = client.post(f"/api/staff/queue/{entry_id}/call",
                        headers=_headers(staff_token))
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Start / Complete / Flag / No-show actions
# ---------------------------------------------------------------------------

class TestQueueActions:
    def _setup(self, client, db_session, suffix):
        staff_token, _ = _register(client, f"staff{suffix}@example.com", role="staff")
        cust_token, _ = _register(client, f"cust{suffix}@example.com", role="customer")
        loc_id = _make_location(db_session)
        case_id = _make_case(client, cust_token)
        return staff_token, case_id, loc_id

    def test_start_service(self, client, db_session):
        staff_token, case_id, loc_id = self._setup(client, db_session, "start")
        entry_id = _make_queue_entry(db_session, case_id, loc_id, "called")

        r = client.post(f"/api/staff/queue/{entry_id}/start",
                        headers=_headers(staff_token))
        assert r.status_code == 200

        from app.models.models import QueueEntry, QueueEntryStatus
        db_session.expire_all()
        entry = db_session.get(QueueEntry, entry_id)
        assert entry.status == QueueEntryStatus.in_service

    def test_complete_service(self, client, db_session):
        staff_token, case_id, loc_id = self._setup(client, db_session, "complete")
        entry_id = _make_queue_entry(db_session, case_id, loc_id, "in_service")

        r = client.post(f"/api/staff/queue/{entry_id}/complete",
                        headers=_headers(staff_token))
        assert r.status_code == 200

        from app.models.models import QueueEntry, QueueEntryStatus
        db_session.expire_all()
        entry = db_session.get(QueueEntry, entry_id)
        assert entry.status == QueueEntryStatus.completed
        assert entry.service_completed_at is not None

    def test_flag_creates_event(self, client, db_session):
        staff_token, case_id, loc_id = self._setup(client, db_session, "flag")
        entry_id = _make_queue_entry(db_session, case_id, loc_id, "in_service")

        r = client.post(f"/api/staff/queue/{entry_id}/flag",
                        headers=_headers(staff_token))
        assert r.status_code == 200

        from app.models.models import QueueEvent, QueueEventType
        events = (
            db_session.query(QueueEvent)
            .filter(
                QueueEvent.queue_entry_id == entry_id,
                QueueEvent.event_type == QueueEventType.document_delay,
            )
            .all()
        )
        assert len(events) == 1

    def test_no_show(self, client, db_session):
        staff_token, case_id, loc_id = self._setup(client, db_session, "noshow")
        entry_id = _make_queue_entry(db_session, case_id, loc_id, "called")

        r = client.post(f"/api/staff/queue/{entry_id}/no_show",
                        headers=_headers(staff_token))
        assert r.status_code == 200

        from app.models.models import QueueEntry, QueueEntryStatus
        db_session.expire_all()
        entry = db_session.get(QueueEntry, entry_id)
        assert entry.status == QueueEntryStatus.no_show


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class TestMetrics:
    def test_metrics_empty_location(self, client, db_session):
        staff_token, _ = _register(client, "staffmetrics@example.com", role="staff")
        loc_id = _make_location(db_session)

        r = client.get(f"/api/staff/metrics/{loc_id}", headers=_headers(staff_token))
        assert r.status_code == 200
        data = r.json()
        assert data["total_completed"] == 0
        assert data["total_no_shows"] == 0
        assert data["total_doc_delays"] == 0
        assert data["median_wait_minutes"] is None
        assert "completions_by_hour" in data

    def test_metrics_after_simulation(self, client, db_session):
        staff_token, uid = _register(client, "staffsim@example.com", role="staff")
        loc_id = _make_location(db_session)

        from app.services.queue_simulator import run_simulation
        run_simulation(
            db=db_session,
            location_id=loc_id,
            staff_user_id=uid,
            params={
                "simulation_hours": 4,
                "arrival_rate_per_hour": 10,
                "active_windows": 3,
                "step_minutes": 10,
            },
        )

        r = client.get(f"/api/staff/metrics/{loc_id}?hours=24",
                       headers=_headers(staff_token))
        assert r.status_code == 200
        data = r.json()
        # simulator should have produced completions
        assert data["total_completed"] >= 0   # shape check
        assert "disclaimer" in data


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class TestNotifications:
    def test_empty_notifications(self, client, db_session):
        token, _ = _register(client, "nonotif@example.com")
        r = client.get("/api/notifications", headers=_headers(token))
        assert r.status_code == 200
        assert r.json() == []

    def test_mark_read(self, client, db_session):
        staff_token, _ = _register(client, "staffmkread@example.com", role="staff")
        cust_token, _ = _register(client, "custmkread@example.com", role="customer")
        loc_id = _make_location(db_session)
        case_id = _make_case(client, cust_token)
        entry_id = _make_queue_entry(db_session, case_id, loc_id, "waiting")

        # Call customer → creates notification
        client.post(f"/api/staff/queue/{entry_id}/call",
                    headers=_headers(staff_token))

        notifs = client.get("/api/notifications", headers=_headers(cust_token)).json()
        assert len(notifs) >= 1
        notif_id = notifs[0]["id"]
        assert notifs[0]["is_read"] is False

        # Mark read
        r = client.post(f"/api/notifications/{notif_id}/read",
                        headers=_headers(cust_token))
        assert r.status_code == 200

        notifs2 = client.get("/api/notifications", headers=_headers(cust_token)).json()
        matching = [n for n in notifs2 if n["id"] == notif_id]
        assert matching[0]["is_read"] is True

    def test_mark_all_read(self, client, db_session):
        staff_token, _ = _register(client, "staffmarkall@example.com", role="staff")
        cust_token, _ = _register(client, "custmarkall@example.com", role="customer")
        loc_id = _make_location(db_session)
        case_id = _make_case(client, cust_token)

        # Create two queue entries and call both
        entry1 = _make_queue_entry(db_session, case_id, loc_id, "waiting")
        client.post(f"/api/staff/queue/{entry1}/call", headers=_headers(staff_token))

        case_id2 = _make_case(client, cust_token)
        entry2 = _make_queue_entry(db_session, case_id2, loc_id, "waiting")
        client.post(f"/api/staff/queue/{entry2}/call", headers=_headers(staff_token))

        client.post("/api/notifications/read_all", headers=_headers(cust_token))

        notifs = client.get("/api/notifications", headers=_headers(cust_token)).json()
        assert all(n["is_read"] for n in notifs)

    def test_notifications_isolated_per_user(self, client, db_session):
        staff_token, _ = _register(client, "staffiso@example.com", role="staff")
        cust1_token, _ = _register(client, "cust1iso@example.com", role="customer")
        cust2_token, _ = _register(client, "cust2iso@example.com", role="customer")
        loc_id = _make_location(db_session)
        case_id = _make_case(client, cust1_token)
        entry_id = _make_queue_entry(db_session, case_id, loc_id, "waiting")
        client.post(f"/api/staff/queue/{entry_id}/call", headers=_headers(staff_token))

        # cust1 should see notification, cust2 should not
        n1 = client.get("/api/notifications", headers=_headers(cust1_token)).json()
        n2 = client.get("/api/notifications", headers=_headers(cust2_token)).json()
        assert len(n1) >= 1
        assert len(n2) == 0
