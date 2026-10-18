"""
Tests for the /api/health endpoint and basic app startup.
"""


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "disclaimer" in data


def test_docs_available(client):
    response = client.get("/api/docs")
    assert response.status_code == 200


def test_openapi_available(client):
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "paths" in data
