"""Integration test: query endpoint with FakeLLM + mocked integrations."""

from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.api.auth_deps import get_session
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import Cluster, Organization, User
from tests.unit.fake_llm import FakeLLM


async def _override_session(session):
    async def _get():
        yield session

    app.dependency_overrides[get_session] = _get


async def _seed(session):
    org = Organization(name="Acme", slug="acme-q")
    session.add(org)
    await session.flush()

    user = User(
        email="q@acme.com",
        password_hash=hash_password("securepass123"),
        name="Q",
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


async def test_submit_query_returns_answer(session):
    user, cluster = await _seed(session)
    await _override_session(session)

    token = create_access_token(str(user.id))

    fake_prom = AsyncMock()
    fake_prom.query = AsyncMock(return_value={"data": {"result": [{"value": ["0", "0.9997"]}]}})

    fake_k8s = AsyncMock()
    fake_k8s.get_events = AsyncMock(return_value=[])
    fake_k8s.get_pods = AsyncMock(return_value=[])
    fake_k8s.get_deployments = AsyncMock(return_value=[])
    fake_k8s.get_deployment = AsyncMock(return_value={})
    fake_k8s.get_logs = AsyncMock(return_value="")

    fake_llm = FakeLLM()

    with (
        patch("app.services.query_service.get_llm", return_value=fake_llm),
        patch(
            "app.services.query_service._build_tools",
            return_value=AsyncMock(
                invoke=AsyncMock(return_value={"data": "ok"})
            ),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/query",
                headers={"Authorization": f"Bearer {token}"},
                json={"cluster_id": str(cluster.id), "query": "Is production healthy?"},
            )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "complete"
    assert body["answer"]
    assert body["confidence"] == "high"
    assert body["investigationId"]

    app.dependency_overrides.clear()


async def test_submit_query_requires_auth(session):
    user, cluster = await _seed(session)
    await _override_session(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/query",
            json={"cluster_id": str(cluster.id), "query": "test"},
        )

    assert resp.status_code == 401
    app.dependency_overrides.clear()


async def test_get_query_by_id(session):
    user, cluster = await _seed(session)
    await _override_session(session)

    token = create_access_token(str(user.id))

    with (
        patch("app.services.query_service.get_llm", return_value=FakeLLM()),
        patch(
            "app.services.query_service._build_tools",
            return_value=AsyncMock(invoke=AsyncMock(return_value={"ok": True})),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create = await client.post(
                "/api/v1/query",
                headers={"Authorization": f"Bearer {token}"},
                json={"cluster_id": str(cluster.id), "query": "Is prod healthy?"},
            )
            qid = create.json()["id"]

            resp = await client.get(
                f"/api/v1/query/queries/{qid}",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 200
    assert resp.json()["id"] == qid
    app.dependency_overrides.clear()
