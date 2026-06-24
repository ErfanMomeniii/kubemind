"""Dashboard route: aggregated cluster health + changes + risk."""

from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from app.api.auth_deps import CurrentUser, DbSession
from app.core.exceptions import NotFound, PermissionDenied
from app.models import Cluster
from app.schemas.dashboard import DashboardResponse
from app.services import dashboard_service

router = APIRouter(prefix="/clusters", tags=["dashboard"])


@router.get("/{cluster_id}/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    cluster_id: UUID, user: CurrentUser, session: DbSession
) -> DashboardResponse:
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

    return await dashboard_service.build_dashboard(cluster, session)
