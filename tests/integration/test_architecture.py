"""Integration test: architecture sync + graph + blast radius endpoints."""

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
    org = Organization(name="Acme", slug="acme-arch")
    session.add(org)
    await session.flush()

    user = User(
        email="arch@acme.com",
        password_hash=hash_password("securepass123"),
        name="Arch",
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


async def test_arch_sync_then_graph_and_blast_radius(session):
    user, cluster = await _seed(session)
    await _override_session(session)
    token = create_access_token(str(user.id))

    fake_k8s = AsyncMock()
    fake_k8s.get_deployments = AsyncMock(
        return_value=[
            {
                "name": "frontend",
                "namespace": "prod",
                "replicas_desired": 2,
                "replicas_ready": 2,
                "available": 2,
                "image": "frontend-v1",
                "env_vars": {"PAYMENT_URL": "http://payment-api:8080"},
            },
            {
                "name": "payment-api",
                "namespace": "prod",
                "replicas_desired": 3,
                "replicas_ready": 3,
                "available": 3,
                "image": "payment-v2",
                "env_vars": {"DATABASE_URL": "postgres://db:5432"},
            },
        ]
    )

    with patch("app.services.architecture_service.KubernetesClient", return_value=fake_k8s):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            sync = await client.post(
                f"/api/v1/clusters/{cluster.id}/architecture/sync",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert sync.status_code == 200, sync.text
            counts = sync.json()
            assert counts["services"] == 2
            assert counts["dependencies"] == 2

            graph = await client.get(
                f"/api/v1/clusters/{cluster.id}/dependencies",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert graph.status_code == 200
            body = graph.json()
            assert len(body["services"]) == 2
            assert len(body["dependencies"]) == 2

            blast = await client.get(
                f"/api/v1/clusters/{cluster.id}/services/payment-api/blast-radius",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert blast.status_code == 200, blast.text
            br = blast.json()
            assert br["service"] == "payment-api"
            assert "prod/frontend" in br["directDownstream"]
            assert "db" in br["upstream"]
            assert br["affectedCount"] >= 2

    app.dependency_overrides.clear()


async def test_architecture_requires_auth(session):
    user, cluster = await _seed(session)
    await _override_session(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/api/v1/clusters/{cluster.id}/architecture/sync")
    assert resp.status_code == 401
    app.dependency_overrides.clear()
