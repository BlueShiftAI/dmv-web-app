"""
Tests for registration cases, submit flow, and staff status transitions.
"""


def _register_and_token(client, email="case.user@example.com", role="customer"):
    resp = client.post("/api/auth/register", json={
        "email": email,
        "full_name": "Case User",
        "password": "TestPass1!",
        "role": role,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _create_case(client, token):
    resp = client.post(
        "/api/cases",
        json={"scenario": "private_party_purchase"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_case(client):
    token = _register_and_token(client)
    resp = client.post(
        "/api/cases",
        json={"scenario": "private_party_purchase"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["scenario"] == "private_party_purchase"
    assert data["status"] == "draft"


def test_create_case_unsupported_scenario(client):
    token = _register_and_token(client, "unsupported@example.com")
    resp = client.post(
        "/api/cases",
        json={"scenario": "commercial_vehicle"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_get_case_requires_auth(client):
    resp = client.get("/api/cases/nonexistent")
    assert resp.status_code == 401


def test_get_case_not_found(client):
    token = _register_and_token(client, "notfound@example.com")
    resp = client.get(
        "/api/cases/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Submit and lifecycle tests
# ---------------------------------------------------------------------------

def test_submit_case(client):
    token = _register_and_token(client, "submit1@example.com")
    case_id = _create_case(client, token)
    resp = client.post(
        f"/api/cases/{case_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"


def test_submit_case_not_owner(client):
    token = _register_and_token(client, "submit_owner@example.com")
    other = _register_and_token(client, "submit_other@example.com")
    case_id = _create_case(client, token)
    resp = client.post(
        f"/api/cases/{case_id}/submit",
        headers={"Authorization": f"Bearer {other}"},
    )
    assert resp.status_code == 403


def test_submit_case_already_submitted(client):
    token = _register_and_token(client, "submit_dup@example.com")
    case_id = _create_case(client, token)
    client.post(f"/api/cases/{case_id}/submit", headers={"Authorization": f"Bearer {token}"})
    resp = client.post(
        f"/api/cases/{case_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_staff_status_transition(client):
    customer = _register_and_token(client, "lifecycle_cust@example.com")
    staff = _register_and_token(client, "lifecycle_staff@example.com", role="staff")
    case_id = _create_case(client, customer)

    # submit
    r = client.post(f"/api/cases/{case_id}/submit", headers={"Authorization": f"Bearer {customer}"})
    assert r.json()["status"] == "submitted"

    # start review
    r = client.patch(
        f"/api/cases/{case_id}/status",
        json={"status": "in_review"},
        headers={"Authorization": f"Bearer {staff}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_review"

    # approve
    r = client.patch(
        f"/api/cases/{case_id}/status",
        json={"status": "approved", "staff_notes": "Looks good"},
        headers={"Authorization": f"Bearer {staff}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_staff_invalid_transition(client):
    customer = _register_and_token(client, "invalid_trans@example.com")
    staff = _register_and_token(client, "invalid_trans_staff@example.com", role="staff")
    case_id = _create_case(client, customer)

    # try to approve a draft (not allowed)
    r = client.patch(
        f"/api/cases/{case_id}/status",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {staff}"},
    )
    assert r.status_code == 400


def test_staff_status_requires_staff_role(client):
    customer = _register_and_token(client, "no_staff_perm@example.com")
    case_id = _create_case(client, customer)
    client.post(f"/api/cases/{case_id}/submit", headers={"Authorization": f"Bearer {customer}"})
    r = client.patch(
        f"/api/cases/{case_id}/status",
        json={"status": "in_review"},
        headers={"Authorization": f"Bearer {customer}"},
    )
    assert r.status_code == 403


def test_list_pending_cases_staff_only(client):
    customer = _register_and_token(client, "pending_cust@example.com")
    staff = _register_and_token(client, "pending_staff@example.com", role="staff")

    # customer cannot access
    r = client.get("/api/cases/pending", headers={"Authorization": f"Bearer {customer}"})
    assert r.status_code == 403

    # staff can
    r = client.get("/api/cases/pending", headers={"Authorization": f"Bearer {staff}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
