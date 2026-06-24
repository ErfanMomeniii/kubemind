"""Sync route: trigger cluster sync."""

from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from app.api.auth_deps import CurrentUser, DbSession
from app.core.exceptions import NotFound, PermissionDenied
from app.models import Cluster
from app.services import sync_service

router = APIRouter(prefix="/clusters", tags=["sync"])


@router.post("/{cluster_id}/sync")
async def sync_cluster(
    cluster_id: UUID, user: CurrentUser, session: DbSession
) -> dict[str, int]:
    if user.org_id is None:
        raise PermissionDenied("user has no organization")

    cluster = await session.scalar(
        select(Cluster).where(
            Cluster.id == cluster_id,
            Cluster.org_id == user.org_id,
            Cluster.deleted_at.is_(None),
        )
    )
    if cluster is None:
        raise NotFound("cluster not found", {"cluster_id": str(cluster_id)})

    return await sync_service.sync_cluster(cluster, session)
