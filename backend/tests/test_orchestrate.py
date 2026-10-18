"""
Tests for Orchestrate tool endpoints and chat proxy (mock mode).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


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
        name="Orch Test Loc", address="1 Orch St", city="Rock Hill",
        state="SC", zip_code="29730", timezone="America/New_York", is_demo=True,
    )
    db_session.add(loc)
    db_session.commit()
    db_session.refresh(loc)
    return loc.id


def _make_slot(db_session, location_id, offset_hours=24, capacity=3):
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
# Auth guard
# ---------------------------------------------------------------------------

class TestOrchestrateAuth:
    def test_chat_requires_auth(self, client):
        r = client.post("/api/orchestrate/chat",
                        json={"message": "hello"})
        assert r.status_code == 401

    def test_tools_require_auth(self, client, db_session):
        loc_id = _make_location(db_session)
        r = client.get(f"/api/orchestrate/tools/queue?location_id={loc_id}")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Chat proxy (mock mode — no Orchestrate credentials in tests)
# ---------------------------------------------------------------------------

class TestChatMock:
    def test_chat_returns_reply(self, client, db_session):
        token, _ = _register(client, "chatuser@example.com")
        r = client.post("/api/orchestrate/chat",
                        json={"message": "hello"},
                        headers=_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert "reply" in data
        assert len(data["reply"]) > 10
        assert data["orchestrate_enabled"] is False
        assert data["simulated"] is True
        assert "session_id" in data

    def test_chat_documents_keywords(self, client, db_session):
        token, _ = _register(client, "chatdocs@example.com")
        r = client.post("/api/orchestrate/chat",
                        json={"message": "what documents do I need?"},
                        headers=_headers(token))
        assert r.status_code == 200
        reply = r.json()["reply"].lower()
        assert "title" in reply or "bill of sale" in reply or "insurance" in reply

    def test_chat_appointment_keywords(self, client, db_session):
        token, _ = _register(client, "chatappt@example.com")
        r = client.post("/api/orchestrate/chat",
                        json={"message": "how do I book an appointment?"},
                        headers=_headers(token))
        assert r.status_code == 200
        assert "appointment" in r.json()["reply"].lower()

    def test_chat_session_id_preserved(self, client, db_session):
        token, _ = _register(client, "chatsess@example.com")
        sid = "test-session-abc123"
        r = client.post("/api/orchestrate/chat",
                        json={"message": "hello", "session_id": sid},
                        headers=_headers(token))
        assert r.json()["session_id"] == sid

    def test_chat_fallback_on_unknown(self, client, db_session):
        token, _ = _register(client, "chatunk@example.com")
        r = client.post("/api/orchestrate/chat",
                        json={"message": "xyzzy something unknown 12345"},
                        headers=_headers(token))
        assert r.status_code == 200
        assert len(r.json()["reply"]) > 5


# ---------------------------------------------------------------------------
# Tool: checklist
# ---------------------------------------------------------------------------

class TestToolChecklist:
    def test_empty_checklist(self, client, db_session):
        token, _ = _register(client, "toolcheck@example.com")
        case_id = _make_case(client, token)
        r = client.get(f"/api/orchestrate/tools/checklist?case_id={case_id}",
                       headers=_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert data["case_id"] == case_id
        assert "total_items" in data
        assert data["simulated"] is True

    def test_access_denied_other_user(self, client, db_session):
        t1, _ = _register(client, "toolcheck1@example.com")
        t2, _ = _register(client, "toolcheck2@example.com")
        case_id = _make_case(client, t1)
        r = client.get(f"/api/orchestrate/tools/checklist?case_id={case_id}",
                       headers=_headers(t2))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Tool: draft
# ---------------------------------------------------------------------------

class TestToolDraft:
    def test_no_draft_yet(self, client, db_session):
        token, _ = _register(client, "tooldraft@example.com")
        case_id = _make_case(client, token)
        r = client.get(f"/api/orchestrate/tools/draft?case_id={case_id}",
                       headers=_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert data["has_draft"] is False
        assert data["simulated"] is True

    def test_draft_after_save(self, client, db_session):
        token, _ = _register(client, "tooldraft2@example.com")
        case_id = _make_case(client, token)
        # Save a partial draft
        client.put(f"/api/cases/{case_id}/draft",
                   json={"data": {"vehicle": {"vin": "1HGCM82633A004352",
                                              "year": 2020, "make": "Honda", "model": "Civic"}},
                         "is_complete": False},
                   headers=_headers(token))
        r = client.get(f"/api/orchestrate/tools/draft?case_id={case_id}",
                       headers=_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert data["has_draft"] is True
        assert data["has_vin"] is True


# ---------------------------------------------------------------------------
# Tool: queue
# ---------------------------------------------------------------------------

class TestToolQueue:
    def test_queue_snapshot(self, client, db_session):
        token, _ = _register(client, "toolqueue@example.com")
        loc_id = _make_location(db_session)
        r = client.get(f"/api/orchestrate/tools/queue?location_id={loc_id}",
                       headers=_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert "waiting_count" in data
        assert "queue_status" in data
        assert data["simulated"] is True


# ---------------------------------------------------------------------------
# Tool: tax lookup
# ---------------------------------------------------------------------------

class TestToolTax:
    def test_not_found(self, client, db_session):
        token, _ = _register(client, "tooltax@example.com")
        r = client.get("/api/orchestrate/tools/tax?vin=NOTFOUND00000000X",
                       headers=_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "not_found"
        assert data["simulated"] is True

    def test_found_after_seed(self, client, db_session):
        from app.models.models import TaxRecord, TaxStatus
        token, _ = _register(client, "tooltax2@example.com")
        rec = TaxRecord(vin="1TAXTEST000000001", status=TaxStatus.paid,
                        amount_cents=45000, county="York County", tax_year=2024)
        db_session.add(rec)
        db_session.commit()

        r = client.get("/api/orchestrate/tools/tax?vin=1TAXTEST000000001",
                       headers=_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "paid"
        assert data["amount_cents"] == 45000


# ---------------------------------------------------------------------------
# Tool: ownership lookup
# ---------------------------------------------------------------------------

class TestToolOwnership:
    def test_not_found(self, client, db_session):
        token, _ = _register(client, "toolown@example.com")
        r = client.get(
            "/api/orchestrate/tools/ownership?vin=NOWNVIN0000000000&seller_name=Nobody",
            headers=_headers(token))
        assert r.status_code == 200
        assert r.json()["status"] == "not_found"

    def test_match(self, client, db_session):
        from app.models.models import OwnershipRecord
        token, _ = _register(client, "toolown2@example.com")
        rec = OwnershipRecord(vin="1OWNTEST000000001", owner_name="Jane Smith",
                              county="York County", is_demo=True)
        db_session.add(rec)
        db_session.commit()

        r = client.get(
            "/api/orchestrate/tools/ownership?vin=1OWNTEST000000001&seller_name=Jane+Smith",
            headers=_headers(token))
        assert r.status_code == 200
        assert r.json()["status"] == "match"

    def test_no_match(self, client, db_session):
        from app.models.models import OwnershipRecord
        token, _ = _register(client, "toolown3@example.com")
        rec = OwnershipRecord(vin="1OWNTEST000000002", owner_name="John Doe",
                              county="York County", is_demo=True)
        db_session.add(rec)
        db_session.commit()

        r = client.get(
            "/api/orchestrate/tools/ownership?vin=1OWNTEST000000002&seller_name=Wrong+Person",
            headers=_headers(token))
        assert r.status_code == 200
        assert r.json()["status"] == "no_match"


# ---------------------------------------------------------------------------
# Tool: slots
# ---------------------------------------------------------------------------

class TestToolSlots:
    def test_available_slots(self, client, db_session):
        token, _ = _register(client, "toolslots@example.com")
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id, offset_hours=24)
        from app.models.models import Slot
        slot = db_session.get(Slot, slot_id)
        date_str = slot.start_time.strftime("%Y-%m-%d")

        r = client.get(
            f"/api/orchestrate/tools/slots?location_id={loc_id}&date={date_str}",
            headers=_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert data["available_count"] >= 1
        assert len(data["slots"]) >= 1
        assert data["simulated"] is True


# ---------------------------------------------------------------------------
# Tool: book (confirm_token gate)
# ---------------------------------------------------------------------------

class TestToolBook:
    def test_book_requires_confirm_token(self, client, db_session):
        token, _ = _register(client, "toolbook@example.com")
        case_id = _make_case(client, token)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id)
        r = client.post("/api/orchestrate/tools/book",
                        json={"case_id": case_id, "slot_id": slot_id,
                              "confirm_token": "wrong"},
                        headers=_headers(token))
        assert r.status_code == 400

    def test_book_with_confirm(self, client, db_session):
        token, _ = _register(client, "toolbook2@example.com")
        case_id = _make_case(client, token)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id)
        r = client.post("/api/orchestrate/tools/book",
                        json={"case_id": case_id, "slot_id": slot_id,
                              "confirm_token": "CONFIRM"},
                        headers=_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert "confirmation_code" in data
        assert data["status"] == "booked"
        assert data["simulated"] is True

    def test_book_403_other_user_case(self, client, db_session):
        t1, _ = _register(client, "toolbook3a@example.com")
        t2, _ = _register(client, "toolbook3b@example.com")
        case_id = _make_case(client, t1)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id)
        r = client.post("/api/orchestrate/tools/book",
                        json={"case_id": case_id, "slot_id": slot_id,
                              "confirm_token": "CONFIRM"},
                        headers=_headers(t2))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Tool: cancel (confirm_token gate)
# ---------------------------------------------------------------------------

class TestToolCancel:
    def test_cancel_requires_confirm_token(self, client, db_session):
        token, _ = _register(client, "toolcancel@example.com")
        case_id = _make_case(client, token)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id)
        # book first
        rb = client.post("/api/orchestrate/tools/book",
                         json={"case_id": case_id, "slot_id": slot_id,
                               "confirm_token": "CONFIRM"},
                         headers=_headers(token))
        appt_id = rb.json()["appointment_id"]

        r = client.post("/api/orchestrate/tools/cancel",
                        json={"appointment_id": appt_id, "confirm_token": "nope"},
                        headers=_headers(token))
        assert r.status_code == 400

    def test_cancel_with_confirm(self, client, db_session):
        token, _ = _register(client, "toolcancel2@example.com")
        case_id = _make_case(client, token)
        loc_id = _make_location(db_session)
        slot_id = _make_slot(db_session, loc_id)
        rb = client.post("/api/orchestrate/tools/book",
                         json={"case_id": case_id, "slot_id": slot_id,
                               "confirm_token": "CONFIRM"},
                         headers=_headers(token))
        appt_id = rb.json()["appointment_id"]

        r = client.post("/api/orchestrate/tools/cancel",
                        json={"appointment_id": appt_id, "confirm_token": "CONFIRM"},
                        headers=_headers(token))
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"
