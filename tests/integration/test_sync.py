"""Integration test: sync + list endpoints with fake k8s."""

from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.api.auth_deps import get_session
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import Cluster, Organization, User


async def _override_session(session):
    async def _get():
        yield session

    app.dependency_overrides[get_session] = _get


async def _seed(session):
    org = Organization(name="Acme", slug="acme-sync")
    session.add(org)
    await session.flush()

    user = User(
        email="sync@acme.com",
        password_hash=hash_password("securepass123"),
        name="Sync",
        org_id=org.id,
    )
    session.add(user)
    await session.flush()

    cluster = Cluster(
        org_id=org.id,
        name="prod",
        display_name="Production",
        server_url="https://k8s.prod.acme.com",
        prometheus_url="http://prom:9090",
        status="active",
    )
    session.add(cluster)
    await session.commit()
    await session.refresh(user)
    await session.refresh(cluster)
    return user, cluster


async def test_sync_then_list_deployments(session):
    user, cluster = await _seed(session)
    await _override_session(session)
    token = create_access_token(str(user.id))

    fake_k8s = AsyncMock()
    fake_k8s.get_deployments = AsyncMock(
        return_value=[
            {
                "name": "payment-api",
                "namespace": "prod",
                "replicas_desired": 3,
                "replicas_ready": 3,
                "available": 3,
                "image": "v2.1.4",
            },
        ]
    )
    fake_k8s.get_events = AsyncMock(
        return_value=[
            {
                "reason": "Updated",
                "message": "ConfigMap my-config updated",
                "namespace": "prod",
                "last_timestamp": "2026-06-24T12:00:00+00:00",
                "name": "ev-1",
            },
        ]
    )

    with patch("app.services.sync_service.KubernetesClient", return_value=fake_k8s):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            sync_resp = await client.post(
                f"/api/v1/clusters/{cluster.id}/sync",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert sync_resp.status_code == 200, sync_resp.text
            counts = sync_resp.json()
            assert counts["deployments"] == 1
            assert counts["config_changes"] == 1

            dep_resp = await client.get(
                f"/api/v1/clusters/{cluster.id}/deployments",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert dep_resp.status_code == 200
            deps = dep_resp.json()
            assert len(deps["items"]) == 1
            assert deps["items"][0]["service"] == "payment-api"
            assert deps["items"][0]["version"] == "v2.1.4"

            cfg_resp = await client.get(
                f"/api/v1/clusters/{cluster.id}/config-changes",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert cfg_resp.status_code == 200
            cfgs = cfg_resp.json()
            assert len(cfgs["items"]) == 1
            assert cfgs["items"][0]["kind"] == "ConfigMap"
            assert cfgs["items"][0]["name"] == "my-config"

    app.dependency_overrides.clear()


async def test_sync_idempotent_on_unchanged_deployment(session):
    user, cluster = await _seed(session)
    await _override_session(session)
    token = create_access_token(str(user.id))

    fake_k8s = AsyncMock()
    fake_k8s.get_deployments = AsyncMock(
        return_value=[
            {
                "name": "api",
                "namespace": "prod",
                "replicas_desired": 2,
                "replicas_ready": 2,
                "available": 2,
                "image": "v1.0",
            }
        ]
    )
    fake_k8s.get_events = AsyncMock(return_value=[])

    with patch("app.services.sync_service.KubernetesClient", return_value=fake_k8s):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post(
                f"/api/v1/clusters/{cluster.id}/sync",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert first.json()["deployments"] == 1

            second = await client.post(
                f"/api/v1/clusters/{cluster.id}/sync",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert second.json()["deployments"] == 0  # unchanged

    app.dependency_overrides.clear()


async def test_sync_requires_auth(session):
    user, cluster = await _seed(session)
    await _override_session(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/clusters/{cluster.id}/sync")
    assert resp.status_code == 401
    app.dependency_overrides.clear()
