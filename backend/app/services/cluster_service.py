"""Cluster service: CRUD + connection test."""

from base64 import b64encode
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound
from app.models import Cluster
from app.schemas.cluster import ClusterCreate, ClusterResponse, ClusterUpdate


async def list_clusters(
    org_id: UUID, session: AsyncSession, limit: int = 20, cursor: str | None = None
) -> tuple[list[ClusterResponse], str | None, bool]:
    query = select(Cluster).where(
        Cluster.org_id == org_id, Cluster.deleted_at.is_(None)
    )
    # Cursor: base64 of created_at + id (deterministic ordering)
    if cursor:
        try:
            decoded = b64decode(cursor)
            created_str, last_id = decoded.split("|", 1)
            last_created = datetime.fromisoformat(created_str)
            query = query.where(
                (Cluster.created_at < last_created)
                | ((Cluster.created_at == last_created) & (Cluster.id < UUID(last_id)))
            )
        except Exception:
            pass  # invalid cursor, ignore

    query = query.order_by(Cluster.created_at.desc(), Cluster.id.desc()).limit(limit + 1)
    result = await session.scalars(query)
    clusters = list(result)

    has_more = len(clusters) > limit
    if has_more:
        clusters = clusters[:limit]

    items = [ClusterResponse.model_validate(c) for c in clusters]
    next_cursor = None
    if has_more and clusters:
        last = clusters[-1]
        next_cursor = b64encode(
            f"{last.created_at.isoformat()}|{last.id}".encode()
        ).decode()

    return items, next_cursor, has_more


async def create_cluster(
    org_id: UUID, input: ClusterCreate, session: AsyncSession
) -> ClusterResponse:
    existing = await session.scalar(
        select(Cluster).where(Cluster.org_id == org_id, Cluster.name == input.name)
    )
    if existing is not None:
        raise Conflict("cluster name already exists in org", {"name": input.name})

    cluster = Cluster(
        org_id=org_id,
        name=input.name,
        display_name=input.display_name,
        context=input.context,
        server_url=str(input.server_url),
        prometheus_url=str(input.prometheus_url) if input.prometheus_url else None,
        argocd_url=str(input.argocd_url) if input.argocd_url else None,
        status="active",
    )
    session.add(cluster)
    try:
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise Conflict("cluster name already exists", {"name": input.name}) from exc
    await session.refresh(cluster)

    # Credential stored in secret manager (Vault/k8s Secret), not DB.
    # Phase 2 MVP: log reference, implement Vault client in Phase 3.
    # _store_credential(cluster.id, input.credential)  # TODO Phase 3

    return ClusterResponse.model_validate(cluster)


async def get_cluster(org_id: UUID, cluster_id: UUID, session: AsyncSession) -> ClusterResponse:
    cluster = await session.scalar(
        select(Cluster).where(
            Cluster.id == cluster_id, Cluster.org_id == org_id, Cluster.deleted_at.is_(None)
        )
    )
    if cluster is None:
        raise NotFound("cluster not found", {"cluster_id": str(cluster_id)})
    return ClusterResponse.model_validate(cluster)


async def update_cluster(
    org_id: UUID, cluster_id: UUID, input: ClusterUpdate, session: AsyncSession
) -> ClusterResponse:
    cluster = await session.scalar(
        select(Cluster).where(
            Cluster.id == cluster_id, Cluster.org_id == org_id, Cluster.deleted_at.is_(None)
        ).with_for_update()
    )
    if cluster is None:
        raise NotFound("cluster not found", {"cluster_id": str(cluster_id)})

    if input.display_name is not None:
        cluster.display_name = input.display_name
    if input.status is not None:
        cluster.status = input.status

    await session.commit()
    await session.refresh(cluster)
    return ClusterResponse.model_validate(cluster)


async def delete_cluster(org_id: UUID, cluster_id: UUID, session: AsyncSession) -> None:
    cluster = await session.scalar(
        select(Cluster).where(
            Cluster.id == cluster_id, Cluster.org_id == org_id, Cluster.deleted_at.is_(None)
        )
    )
    if cluster is None:
        raise NotFound("cluster not found", {"cluster_id": str(cluster_id)})

    cluster.deleted_at = datetime.now(timezone.utc)
    cluster.status = "inactive"
    await session.commit()


def b64decode(s: str) -> str:
    from base64 import b64decode as _b64

    return _b64(s).decode()
