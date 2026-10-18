"""
Tests for form draft endpoints and requirements endpoint.
"""
import pytest


def _auth(client, email="draft.user@example.com"):
    r = client.post("/api/auth/register", json={
        "email": email, "full_name": "Draft User", "password": "TestPass1!", "role": "customer"
    })
    return r.json()["access_token"]


def _make_case(client, token):
    r = client.post("/api/cases", json={"scenario": "private_party_purchase"},
                    headers={"Authorization": f"Bearer {token}"})
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Requirements endpoint
# ---------------------------------------------------------------------------

def test_requirements_endpoint(client):
    r = client.get("/api/requirements")
    assert r.status_code == 200
    data = r.json()
    assert "scenario" in data
    assert "documents" in data
    assert "forms" in data
    assert "steps" in data
    assert len(data["documents"]) >= 5  # at least the 5 required docs


def test_requirements_documents(client):
    r = client.get("/api/requirements/documents")
    assert r.status_code == 200
    docs = r.json()
    keys = [d["key"] for d in docs]
    assert "current_title" in keys
    assert "bill_of_sale" in keys
    assert "photo_id" in keys


# ---------------------------------------------------------------------------
# Draft endpoints
# ---------------------------------------------------------------------------

def test_get_draft_creates_empty(client):
    token = _auth(client, "getdraft@example.com")
    case_id = _make_case(client, token)
    r = client.get(f"/api/cases/{case_id}/draft",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["form_type"] == "form_400"
    assert data["data"] == {}
    assert "metadata" in data


def test_save_draft_partial(client):
    token = _auth(client, "savedraft@example.com")
    case_id = _make_case(client, token)
    payload = {
        "data": {
            "vehicle": {
                "vin": "1HGCM82633A004352",
                "year": 2003,
                "make": "Honda",
                "model": "Accord",
            }
        },
        "is_complete": False,
    }
    r = client.put(f"/api/cases/{case_id}/draft",
                   json=payload,
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["data"]["vehicle"]["make"] == "Honda"
    assert data["version"] >= 1  # new draft starts at 1; subsequent saves increment


def test_save_draft_updates_case_vin(client):
    token = _auth(client, "vinupdate@example.com")
    case_id = _make_case(client, token)
    client.put(f"/api/cases/{case_id}/draft",
               json={"data": {"vehicle": {"vin": "3VWFE21C04M000001", "year": 2004,
                                          "make": "VW", "model": "Jetta"}},
                     "is_complete": False},
               headers={"Authorization": f"Bearer {token}"})
    r = client.get(f"/api/cases/{case_id}",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.json()["vin"] == "3VWFE21C04M000001"


def test_save_draft_invalid_year(client):
    token = _auth(client, "baddraft@example.com")
    case_id = _make_case(client, token)
    r = client.put(f"/api/cases/{case_id}/draft",
                   json={"data": {"vehicle": {"vin": "XYZ", "year": 1800,
                                              "make": "Old", "model": "Car"}},
                         "is_complete": False},
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422


def test_draft_unauthorized(client):
    token1 = _auth(client, "draftowner@example.com")
    token2 = _auth(client, "draftother@example.com")
    case_id = _make_case(client, token1)
    r = client.get(f"/api/cases/{case_id}/draft",
                   headers={"Authorization": f"Bearer {token2}"})
    assert r.status_code == 403


def test_download_pdf(client):
    token = _auth(client, "pdftest@example.com")
    case_id = _make_case(client, token)
    # Put some data first
    client.put(f"/api/cases/{case_id}/draft",
               json={"data": {"vehicle": {"vin": "1HGCM82633A004352", "year": 2003,
                                          "make": "Honda", "model": "Accord"},
                              "buyer": {"full_name": "Test Buyer",
                                        "address_line1": "123 Main St",
                                        "city": "Rock Hill", "state": "SC",
                                        "zip_code": "29730"}},
                     "is_complete": False},
               headers={"Authorization": f"Bearer {token}"})
    r = client.get(f"/api/cases/{case_id}/draft/pdf",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    # Verify it starts with the PDF magic bytes
    assert r.content[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# Checklist and lookup
# ---------------------------------------------------------------------------

def test_checklist_generates_items(client):
    token = _auth(client, "checklist2@example.com")
    case_id = _make_case(client, token)
    r = client.get(f"/api/cases/{case_id}/checklist",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 5
    keys = [i["requirement_key"] for i in items]
    assert "current_title" in keys
    assert "photo_id" in keys
    # All items start as missing
    for item in items:
        assert item["status"] == "missing"


def test_lookup_tax_not_found(client):
    token = _auth(client, "taxlookup@example.com")
    r = client.get("/api/lookup/tax/UNKNOWNVIN000000",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["status"] == "not_found"
    assert r.json()["simulated"] is True


def test_lookup_ownership_not_found(client):
    token = _auth(client, "ownerlookup@example.com")
    r = client.get("/api/lookup/ownership/UNKNOWNVIN000000",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["status"] == "not_found"
    assert r.json()["simulated"] is True
