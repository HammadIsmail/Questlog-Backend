"""
Integration tests for the activity ingestion endpoints (Phase 7).
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta

pytestmark = pytest.mark.asyncio


def _make_activity(offset_seconds: int = 0, productive: bool = True) -> dict:
    now = datetime.now(timezone.utc)
    start = now - timedelta(seconds=offset_seconds + 60)
    end = now - timedelta(seconds=offset_seconds)
    return {
        "source": "desktop",
        "application": "devenv" if productive else "spotify",
        "window_title": "Visual Studio" if productive else "Music",
        "category": "Development" if productive else "Entertainment",
        "started_at": start.isoformat(),
        "ended_at": end.isoformat(),
        "duration_seconds": 60,
        "is_productive": productive,
    }


async def test_batch_ingest_accepted(client: AsyncClient, auth_headers: dict):
    """POST /activities/batch with valid data should return 201."""
    resp = await client.post(
        "/api/v1/activities/batch",
        json={"activities": [_make_activity(0), _make_activity(60)]},
        headers=auth_headers,
    )
    assert resp.status_code == 201


async def test_batch_ingest_empty_rejected(client: AsyncClient, auth_headers: dict):
    """An empty activities list should be rejected (400 or 422)."""
    resp = await client.post(
        "/api/v1/activities/batch",
        json={"activities": []},
        headers=auth_headers,
    )
    assert resp.status_code in (400, 422)


async def test_today_activities_returns_list(client: AsyncClient, auth_headers: dict):
    """GET /activities/today should return a list after ingesting."""
    await client.post(
        "/api/v1/activities/batch",
        json={"activities": [_make_activity()]},
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/activities/today", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_batch_requires_auth(client: AsyncClient):
    """Unauthenticated batch ingest should return 401 or 403."""
    resp = await client.post(
        "/api/v1/activities/batch",
        json={"activities": [_make_activity()]},
    )
    assert resp.status_code in (401, 403)
