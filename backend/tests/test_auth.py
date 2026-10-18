"""
Tests for auth: register and login.
"""
import pytest


def test_register_customer(client):
    resp = client.post("/api/auth/register", json={
        "email": "test.user@example.com",
        "full_name": "Test User",
        "password": "TestPass1!",
        "role": "customer",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "customer"


def test_register_duplicate_email(client):
    payload = {
        "email": "dup@example.com",
        "full_name": "Dup User",
        "password": "TestPass1!",
    }
    client.post("/api/auth/register", json=payload)
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 400


def test_login_success(client):
    client.post("/api/auth/register", json={
        "email": "login.test@example.com",
        "full_name": "Login Test",
        "password": "TestPass1!",
    })
    resp = client.post(
        "/api/auth/login",
        data={"username": "login.test@example.com", "password": "TestPass1!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={
        "email": "badpass@example.com",
        "full_name": "Bad Pass",
        "password": "TestPass1!",
    })
    resp = client.post(
        "/api/auth/login",
        data={"username": "badpass@example.com", "password": "WrongPass!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 401
