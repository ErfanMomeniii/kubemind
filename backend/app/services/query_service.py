"""Query service: submit NL query, run agent, persist investigation + answer.

MVP: runs agent inline (synchronous within request). Post-MVP: enqueue RQ
job, return query_id, client polls. See docs/api-design.md §6.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import IntegrationError, LLMError, NotFound
from app.core.logging import get_logger
from app.models import Cluster, Investigation, Query
from app.schemas.query import QueryRequest, QueryResponse

from ai.agent import AgentState, build_agent
from ai.llm import LLM, get_llm
from ai.tools import ToolRegistry
from integrations.k8s import KubernetesClient
from integrations.prometheus import PrometheusClient

log = get_logger()


async def submit_query(
    input: QueryRequest,
    user_id: UUID,
    org_id: UUID,
    session: AsyncSession,
    llm: LLM | None = None,
) -> QueryResponse:
    """Create Query, run agent, persist Investigation, return result."""
    cluster = await _load_cluster(org_id, input.cluster_id, session)

    query = Query(
        org_id=org_id,
        user_id=user_id,
        cluster_id=cluster.id,
        text=input.query,
        status="running",
    )
    session.add(query)
    await session.flush()

    investigation = Investigation(
        org_id=org_id,
        query_id=query.id,
        cluster_id=cluster.id,
        status="running",
        evidence=[],
        steps=[],
    )
    session.add(investigation)
    await session.flush()

    query.investigation_id = investigation.id
    await session.commit()

    try:
        result = await _run_agent(query.text, str(cluster.id), cluster, llm)
    except Exception as exc:
        log.error("agent_failed", query_id=str(query.id), error=str(exc))
        investigation.status = "failed"
        query.status = "failed"
        query.answer = f"investigation failed: {exc}"
        query.confidence = "low"
        await session.commit()
        await session.refresh(query)
        return QueryResponse.model_validate(query)

    investigation.status = "complete"
    investigation.root_cause = result.get("root_cause")
    investigation.confidence = result.get("confidence")
    investigation.evidence = result.get("evidence", [])
    investigation.steps = result.get("tool_results", [])
    investigation.completed_at = datetime.now(timezone.utc)

    query.status = "complete"
    query.answer = result.get("answer")
    query.confidence = result.get("confidence")
    query.model = llm.model_name if llm else "unknown"
    query.completed_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(query)
    return QueryResponse.model_validate(query)


async def get_query(
    query_id: UUID, org_id: UUID, session: AsyncSession
) -> QueryResponse:
    query = await session.scalar(
        select(Query).where(Query.id == query_id, Query.org_id == org_id)
    )
    if query is None:
        raise NotFound("query not found", {"query_id": str(query_id)})
    return QueryResponse.model_validate(query)


async def _run_agent(
    text: str, cluster_id: str, cluster: Cluster, llm: LLM | None
) -> dict:
    if llm is None:
        llm = get_llm()
    tools = _build_tools(cluster)
    agent = build_agent(llm, tools)

    initial: AgentState = {"query": text, "cluster_id": cluster_id}
    result = await agent.ainvoke(initial)
    return dict(result)


def _build_tools(cluster: Cluster) -> ToolRegistry:
    if not cluster.prometheus_url:
        raise IntegrationError("cluster has no prometheus_url configured")
    prom = PrometheusClient(cluster.prometheus_url)
    k8s = KubernetesClient(cluster.server_url, context=cluster.context)
    return ToolRegistry(prometheus=prom, k8s=k8s)


async def _load_cluster(
    org_id: UUID, cluster_id: UUID, session: AsyncSession
) -> Cluster:
    cluster = await session.scalar(
        select(Cluster).where(
            Cluster.id == cluster_id, Cluster.org_id == org_id, Cluster.deleted_at.is_(None)
        )
    )
    if cluster is None:
        raise NotFound("cluster not found", {"cluster_id": str(cluster_id)})
    return cluster
