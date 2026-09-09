"""
Tests for the backend authentication endpoints (Phase 7).
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_register_creates_user(client: AsyncClient):
    """POST /auth/register should return 200 with an access_token."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "new_user@questlog.com",
        "name": "New Adventurer",
        "password": "ValidPass99!",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_duplicate_email_rejected(client: AsyncClient):
    """Registering with the same email twice should fail."""
    payload = {
        "email": "duplicate@questlog.com",
        "name": "First",
        "password": "Pass1234!",
    }
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code in (400, 409)


async def test_login_returns_token(client: AsyncClient):
    """POST /auth/login should return a valid JWT."""
    await client.post("/api/v1/auth/register", json={
        "email": "login_test@questlog.com",
        "name": "Login Tester",
        "password": "LoginPass!1",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login_test@questlog.com",
        "password": "LoginPass!1",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password_rejected(client: AsyncClient):
    """Wrong password should return 401."""
    await client.post("/api/v1/auth/register", json={
        "email": "wrong_pass@questlog.com",
        "name": "Wrong Pass",
        "password": "CorrectPass!1",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "wrong_pass@questlog.com",
        "password": "WrongPassword",
    })
    assert resp.status_code == 401


async def test_me_returns_profile(client: AsyncClient, auth_headers: dict):
    """GET /auth/me with a valid token should return user profile."""
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "email" in data
    assert "name" in data
