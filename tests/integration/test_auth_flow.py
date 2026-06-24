"""Integration test: auth flow end-to-end with real Postgres.

Flow: register → login → refresh → protected route (clusters list).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth_deps import get_session
from app.db.session import async_session_factory


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _override_session_factory(session):
    """Override FastAPI session dependency to use test session."""

    async def _get():
        yield session

    app.dependency_overrides[get_session] = _get


async def test_register_login_refresh_flow(session):
    await _override_session_factory(session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "ceo@acme.com",
                "password": "securepass123",
                "name": "CEO",
                "org_name": "Acme",
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["user"]["email"] == "ceo@acme.com"
        assert body["tokens"]["access_token"]
        assert body["tokens"]["refresh_token"]
        access_token = body["tokens"]["access_token"]
        refresh_token = body["tokens"]["refresh_token"]

        # 2. Login (same credentials)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "ceo@acme.com", "password": "securepass123"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["tokens"]["access_token"]

        # 3. Refresh
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["access_token"]

        # 4. Protected route without token → 401
        resp = await client.get("/api/v1/clusters")
        assert resp.status_code == 401

        # 5. Protected route with token → 200 (empty list)
        resp = await client.get(
            "/api/v1/clusters",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["items"] == []
        assert data["has_more"] is False

    app.dependency_overrides.clear()


async def test_register_duplicate_email_conflict(session):
    await _override_session_factory(session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "email": "dupe@acme.com",
            "password": "securepass123",
            "name": "Dupe",
            "org_name": "Acme Dupe",
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 201

        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"]["code"] == "CONFLICT"

    app.dependency_overrides.clear()


async def test_login_wrong_password(session):
    await _override_session_factory(session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrong@acme.com",
                "password": "securepass123",
                "name": "Wrong",
                "org_name": "Acme Wrong",
            },
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@acme.com", "password": "incorrectpass"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"]["code"] == "UNAUTHENTICATED"

    app.dependency_overrides.clear()
