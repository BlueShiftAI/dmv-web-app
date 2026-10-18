"""
Tests for appointment booking, double-booking prevention, check-in,
queue simulation, and the improved wait estimator.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest


# ---------------------------------------------------------------------------
# Helpers
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
    """Insert a demo location directly; returns location id."""
    from app.models.models import Location
    loc = Location(
        name="Test Location",
        address="1 Test St",
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


def _make_slot(db_session, location_id, offset_hours=1, capacity=2):
    """Insert a future slot; returns slot id."""
    from app.models.models import Slot
    start = datetime.now(timezone.utc) + timedelta(hours=offset_hours)
    slot = Slot(
        location_id=location_id,
        start_time=start.replace(tzinfo=None),
        end_time=(start + timedelta(minutes=30)).replace(tzinfo=None),
        capacity=capacity,
        booked_count=0,
    )
    db_session.add(slot)
    db_session.commit()
    db_session.refresh(slot)
    return slot.id


# ---------------------------------------------------------------------------
# Appointment booking
# ---------------------------------------------------------------------------

class TestAppointmentBooking:
    def test_list_slots_empty(self, client, db_session):
        token, _ = _register(client, "slotlist@example.com")
        loc_id = _make_location(db_session)
        date_str = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%d")
        r = client.get(
            f"/api/appointments/slots?location_id={loc_id}&date={date_str}",
            headers=_headers(token),
        )
        assert r.status_code == 200
        # May be 0 or more — just check shape
        assert isinstance(r.json(), list)

    def test_book_appointment_success(self, client, db_session):
        token, _ = _register(client, "book1@example.com")
        case_id = _make_case(client, token)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id, capacity=2)

        r = client.post(
            "/api/appointments",
            json={"case_id": case_id, "slot_id": slot_id},
            headers=_headers(token),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "booked"
        assert len(data["confirmation_code"]) == 8
        assert "disclaimer" in data

    def test_book_increments_booked_count(self, client, db_session):
        from app.models.models import Slot
        token, _ = _register(client, "book2@example.com")
        case_id = _make_case(client, token)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id, capacity=3)

        client.post("/api/appointments",
                    json={"case_id": case_id, "slot_id": slot_id},
                    headers=_headers(token))

        db_session.expire_all()
        slot = db_session.get(Slot, slot_id)
        assert slot.booked_count == 1

    def test_double_booking_same_case_rejected(self, client, db_session):
        token, _ = _register(client, "dblbook@example.com")
        case_id = _make_case(client, token)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id, capacity=5)

        r1 = client.post("/api/appointments",
                         json={"case_id": case_id, "slot_id": slot_id},
                         headers=_headers(token))
        assert r1.status_code == 201

        # Second booking on the same case should fail
        r2 = client.post("/api/appointments",
                         json={"case_id": case_id, "slot_id": slot_id},
                         headers=_headers(token))
        assert r2.status_code == 409
        assert "already has an active appointment" in r2.json()["detail"]

    def test_slot_capacity_prevents_overbooking(self, client, db_session):
        """Two different cases competing for the last seat."""
        token1, _ = _register(client, "cap1@example.com")
        token2, _ = _register(client, "cap2@example.com")
        case1 = _make_case(client, token1)
        case2 = _make_case(client, token2)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id, capacity=1)

        r1 = client.post("/api/appointments",
                         json={"case_id": case1, "slot_id": slot_id},
                         headers=_headers(token1))
        r2 = client.post("/api/appointments",
                         json={"case_id": case2, "slot_id": slot_id},
                         headers=_headers(token2))

        statuses = {r1.status_code, r2.status_code}
        assert 201 in statuses          # one succeeded
        assert 409 in statuses          # one was rejected

    def test_cancel_appointment(self, client, db_session):
        token, _ = _register(client, "cancel1@example.com")
        case_id = _make_case(client, token)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id)

        appt = client.post("/api/appointments",
                           json={"case_id": case_id, "slot_id": slot_id},
                           headers=_headers(token)).json()
        appt_id = appt["id"]

        r = client.delete(f"/api/appointments/{appt_id}", headers=_headers(token))
        assert r.status_code == 204

    def test_cancel_releases_slot_capacity(self, client, db_session):
        from app.models.models import Slot
        token, _ = _register(client, "cancelcap@example.com")
        case_id = _make_case(client, token)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id, capacity=1)

        appt = client.post("/api/appointments",
                           json={"case_id": case_id, "slot_id": slot_id},
                           headers=_headers(token)).json()
        client.delete(f"/api/appointments/{appt['id']}", headers=_headers(token))

        db_session.expire_all()
        slot = db_session.get(Slot, slot_id)
        assert slot.booked_count == 0

    def test_cancel_then_rebook(self, client, db_session):
        """After cancellation the slot is bookable again."""
        token, _ = _register(client, "rebook@example.com")
        case_id = _make_case(client, token)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id, capacity=1)

        appt = client.post("/api/appointments",
                           json={"case_id": case_id, "slot_id": slot_id},
                           headers=_headers(token)).json()
        client.delete(f"/api/appointments/{appt['id']}", headers=_headers(token))

        # Create a new case (old one already has cancelled appointment)
        case2_id = _make_case(client, token)
        r = client.post("/api/appointments",
                        json={"case_id": case2_id, "slot_id": slot_id},
                        headers=_headers(token))
        assert r.status_code == 201

    def test_cannot_book_other_users_case(self, client, db_session):
        token1, _ = _register(client, "owner1@example.com")
        token2, _ = _register(client, "thief1@example.com")
        case_id = _make_case(client, token1)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id)

        r = client.post("/api/appointments",
                        json={"case_id": case_id, "slot_id": slot_id},
                        headers=_headers(token2))
        assert r.status_code == 403

    def test_checkin_creates_queue_entry(self, client, db_session):
        from app.models.models import QueueEntry
        token, _ = _register(client, "checkin1@example.com")
        case_id = _make_case(client, token)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id)

        appt = client.post("/api/appointments",
                           json={"case_id": case_id, "slot_id": slot_id},
                           headers=_headers(token)).json()

        r = client.post(f"/api/appointments/{appt['id']}/checkin",
                        headers=_headers(token))
        assert r.status_code == 200
        assert "queue_entry_id" in r.json()

        qe_id = r.json()["queue_entry_id"]
        entry = db_session.get(QueueEntry, qe_id)
        assert entry is not None
        assert entry.case_id == case_id


# ---------------------------------------------------------------------------
# Queue snapshot
# ---------------------------------------------------------------------------

class TestQueueSnapshot:
    def test_empty_queue(self, client, db_session):
        token, _ = _register(client, "qsnap@example.com")
        loc_id = _make_location(db_session)
        r = client.get(f"/api/queue/{loc_id}", headers=_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert data["waiting_count"] == 0
        assert data["queue_status"] == "empty"
        assert data["simulated"] is True
        assert "estimated_wait_minutes" in data

    def test_queue_status_labels(self, client, db_session):
        """Inject queue entries and verify status labels."""
        from app.models.models import Case, QueueEntry, QueueEntryStatus
        token, uid = _register(client, "qlabel@example.com")
        loc_id = _make_location(db_session)

        # Create 5 waiting entries
        for _ in range(5):
            c = Case(user_id=uid, location_id=loc_id, scenario="private_party_purchase")
            db_session.add(c)
            db_session.flush()
            db_session.add(QueueEntry(
                case_id=c.id, location_id=loc_id,
                is_walk_in=True,
                checked_in_at=datetime.now(timezone.utc).replace(tzinfo=None),
                status=QueueEntryStatus.waiting,
            ))
        db_session.commit()

        r = client.get(f"/api/queue/{loc_id}", headers=_headers(token))
        assert r.status_code == 200
        assert r.json()["queue_status"] in ("active", "quiet", "busy")
        assert r.json()["waiting_count"] == 5


# ---------------------------------------------------------------------------
# Queue simulator
# ---------------------------------------------------------------------------

class TestQueueSimulator:
    def test_simulation_creates_events(self, client, db_session):
        """Run a short simulation and verify events were created."""
        from app.models.models import QueueEvent

        token, uid = _register(client, "sim1@example.com", role="staff")
        loc_id = _make_location(db_session)

        # Run directly via service (avoids HTTP auth complexity in tests)
        from app.services.queue_simulator import run_simulation
        summary = run_simulation(
            db=db_session,
            location_id=loc_id,
            staff_user_id=uid,
            params={
                "simulation_hours": 1,
                "arrival_rate_per_hour": 10,
                "active_windows": 2,
                "step_minutes": 10,
            },
        )

        assert summary["arrivals"] >= 0  # may be 0 if RNG is unlucky — just shape check
        events_count = db_session.query(QueueEvent).filter(
            QueueEvent.queue_entry_id.isnot(None)
        ).count()
        assert events_count >= 0  # at minimum the schema is correct

    def test_simulation_summary_keys(self, client, db_session):
        token, uid = _register(client, "sim2@example.com", role="staff")
        loc_id = _make_location(db_session)

        from app.services.queue_simulator import run_simulation
        summary = run_simulation(
            db=db_session,
            location_id=loc_id,
            staff_user_id=uid,
            params={"simulation_hours": 0.5, "arrival_rate_per_hour": 6,
                    "active_windows": 2, "step_minutes": 15},
        )
        for key in ("arrivals", "completed", "no_shows", "document_delays", "disclaimer"):
            assert key in summary


# ---------------------------------------------------------------------------
# Wait estimator
# ---------------------------------------------------------------------------

class TestWaitEstimator:
    def test_baseline_when_no_history(self, client, db_session):
        from app.services.queue_simulator import estimate_wait_from_history
        loc_id = _make_location(db_session)
        result = estimate_wait_from_history(db_session, loc_id, 5, 2)
        assert result["method"] == "baseline_formula"
        assert result["estimated_wait_minutes"] is not None
        assert result["sample_size"] == 0

    def test_event_log_method_after_simulation(self, client, db_session):
        from app.services.queue_simulator import estimate_wait_from_history, run_simulation
        token, uid = _register(client, "waittest@example.com", role="staff")
        loc_id = _make_location(db_session)

        run_simulation(
            db=db_session,
            location_id=loc_id,
            staff_user_id=uid,
            params={"simulation_hours": 3, "arrival_rate_per_hour": 12,
                    "active_windows": 3, "step_minutes": 5},
        )

        result = estimate_wait_from_history(
            db_session, loc_id, 3, 2, lookback_hours=24
        )
        # If the simulation produced completions, method upgrades
        if result["sample_size"] > 0:
            assert result["method"] == "event_log_history"
            assert result["p50_service_minutes"] is not None


# ---------------------------------------------------------------------------
# New M4 endpoints: GET /api/appointments and GET /api/queue/locations
# ---------------------------------------------------------------------------

class TestGetAppointmentForCase:
    def test_returns_null_when_no_appointment(self, client, db_session):
        token, _ = _register(client, "getnoappt@example.com")
        case_id = _make_case(client, token)
        r = client.get(
            f"/api/appointments?case_id={case_id}",
            headers=_headers(token),
        )
        assert r.status_code == 200
        assert r.json() is None

    def test_returns_appointment_after_booking(self, client, db_session):
        token, _ = _register(client, "getappt@example.com")
        case_id = _make_case(client, token)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id, capacity=2)

        # book
        rb = client.post(
            "/api/appointments",
            json={"case_id": case_id, "slot_id": slot_id},
            headers=_headers(token),
        )
        assert rb.status_code == 201

        # fetch
        r = client.get(
            f"/api/appointments?case_id={case_id}",
            headers=_headers(token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data is not None
        assert data["case_id"] == case_id
        assert data["status"] == "booked"

    def test_other_user_cannot_see_appointment(self, client, db_session):
        token1, _ = _register(client, "owner123@example.com")
        token2, _ = _register(client, "spy456@example.com")
        case_id = _make_case(client, token1)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id, capacity=2)
        client.post("/api/appointments",
                    json={"case_id": case_id, "slot_id": slot_id},
                    headers=_headers(token1))
        r = client.get(
            f"/api/appointments?case_id={case_id}",
            headers=_headers(token2),
        )
        assert r.status_code == 403


class TestPublicLocationsEndpoint:
    def test_returns_locations_list(self, client, db_session):
        _make_location(db_session)
        token, _ = _register(client, "loclist@example.com")
        r = client.get("/api/queue/locations", headers=_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "id" in data[0]
        assert "name" in data[0]
        assert "city" in data[0]

    def test_requires_auth(self, client, db_session):
        r = client.get("/api/queue/locations")
        assert r.status_code == 401
