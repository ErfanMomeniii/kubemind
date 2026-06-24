"""Integration test: dashboard endpoint with mocked Prometheus + fake k8s."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.auth_deps import get_session
from app.models import Cluster, Incident, Organization, User
from app.core.security import create_access_token, hash_password


async def _override_session(session):
    async def _get():
        yield session

    app.dependency_overrides[get_session] = _get


async def _seed_org_user_cluster(session, prometheus_url="http://prom:9090"):
    org = Organization(name="Acme", slug="acme-dash")
    session.add(org)
    await session.flush()

    user = User(
        email="dash@acme.com",
        password_hash=hash_password("securepass123"),
        name="Dash",
        org_id=org.id,
    )
    session.add(user)
    await session.flush()

    cluster = Cluster(
        org_id=org.id,
        name="prod",
        display_name="Production",
        server_url="https://k8s.prod.acme.com",
        prometheus_url=prometheus_url,
        status="active",
    )
    session.add(cluster)
    await session.flush()

    incident = Incident(
        org_id=org.id,
        cluster_id=cluster.id,
        title="payment-api 5xx",
        severity="sev1",
        status="open",
        service="payment-api",
        started_at=datetime.now(timezone.utc) - timedelta(minutes=12),
    )
    session.add(incident)
    await session.commit()
    await session.refresh(user)
    await session.refresh(cluster)

    return user, cluster


async def test_dashboard_aggregates_signals(session):
    user, cluster = await _seed_org_user_cluster(session)
    await _override_session_factory_dummy(session)

    token = create_access_token(str(user.id))

    fake_prom = AsyncMock()
    fake_prom.up_ratio = AsyncMock(return_value=0.9997)
    fake_prom.error_rate = AsyncMock(return_value=0.001)
    fake_prom.firing_critical_alerts = AsyncMock(return_value=[])

    fake_k8s = AsyncMock()
    fake_k8s.get_deployments = AsyncMock(return_value=[])
    fake_k8s.get_pods = AsyncMock(return_value=[])

    with (
        patch(
            "app.services.dashboard_service._prometheus_client", return_value=fake_prom
        ),
        patch("app.services.dashboard_service._k8s_client", return_value=fake_k8s),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/clusters/{cluster.id}/dashboard",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["clusterId"] == str(cluster.id)
    assert body["health"]["status"] == "Healthy"
    assert body["health"]["availability"] == pytest.approx(0.9997, rel=1e-3)
    assert body["dataStale"] is False
    assert len(body["incidents"]["critical"]) == 1
    assert body["incidents"]["critical"][0]["title"] == "payment-api 5xx"

    app.dependency_overrides.clear()


async def test_dashboard_degrades_when_prometheus_down(session):
    from app.core.exceptions import IntegrationError

    user, cluster = await _seed_org_user_cluster(session)
    await _override_session_factory_dummy(session)

    token = create_access_token(str(user.id))

    fake_prom = AsyncMock()
    fake_prom.up_ratio = AsyncMock(side_effect=IntegrationError("prom down"))
    fake_prom.error_rate = AsyncMock(side_effect=IntegrationError("prom down"))
    fake_prom.firing_critical_alerts = AsyncMock(side_effect=IntegrationError("prom down"))

    fake_k8s = AsyncMock()
    fake_k8s.get_deployments = AsyncMock(return_value=[])
    fake_k8s.get_pods = AsyncMock(return_value=[])

    with (
        patch(
            "app.services.dashboard_service._prometheus_client", return_value=fake_prom
        ),
        patch("app.services.dashboard_service._k8s_client", return_value=fake_k8s),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/clusters/{cluster.id}/dashboard",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["health"]["status"] == "Unknown"
    assert body["dataStale"] is True

    app.dependency_overrides.clear()


async def test_dashboard_requires_auth(session):
    user, cluster = await _seed_org_user_cluster(session)
    await _override_session_factory_dummy(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/clusters/{cluster.id}/dashboard")

    assert resp.status_code == 401
    app.dependency_overrides.clear()


async def _override_session_factory_dummy(session):
    async def _get():
        yield session

    app.dependency_overrides[get_session] = _get
