"""Cluster routes: list, create, get, update, delete."""

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.auth_deps import CurrentUser, DbSession
from app.core.exceptions import PermissionDenied
from app.schemas.cluster import (
    ClusterCreate,
    ClusterListResponse,
    ClusterResponse,
    ClusterUpdate,
)
from app.services import cluster_service

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("", response_model=ClusterListResponse)
async def list_clusters(
    user: CurrentUser,
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
) -> ClusterListResponse:
    if user.org_id is None:
        raise PermissionDenied("user has no organization")
    items, next_cursor, has_more = await cluster_service.list_clusters(
        user.org_id, session, limit=limit, cursor=cursor
    )
    return ClusterListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.post("", response_model=ClusterResponse, status_code=201)
async def create_cluster(
    input: ClusterCreate, user: CurrentUser, session: DbSession
) -> ClusterResponse:
    if user.org_id is None:
        raise PermissionDenied("user has no organization")
    return await cluster_service.create_cluster(user.org_id, input, session)


@router.get("/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(cluster_id: UUID, user: CurrentUser, session: DbSession) -> ClusterResponse:
    if user.org_id is None:
        raise PermissionDenied("user has no organization")
    return await cluster_service.get_cluster(user.org_id, cluster_id, session)


@router.patch("/{cluster_id}", response_model=ClusterResponse)
async def update_cluster(
    cluster_id: UUID, input: ClusterUpdate, user: CurrentUser, session: DbSession
) -> ClusterResponse:
    if user.org_id is None:
        raise PermissionDenied("user has no organization")
    return await cluster_service.update_cluster(user.org_id, cluster_id, input, session)


@router.delete("/{cluster_id}", status_code=204)
async def delete_cluster(cluster_id: UUID, user: CurrentUser, session: DbSession) -> None:
    if user.org_id is None:
        raise PermissionDenied("user has no organization")
    await cluster_service.delete_cluster(user.org_id, cluster_id, session)
