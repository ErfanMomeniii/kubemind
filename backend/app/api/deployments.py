"""Deployment + config change routes."""

from base64 import b64decode, b64encode
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.auth_deps import CurrentUser, DbSession
from app.core.exceptions import PermissionDenied
from app.models import ConfigChange, Deployment
from app.schemas.deployment import (
    ConfigChangeListResponse,
    ConfigChangeResponse,
    DeploymentListResponse,
    DeploymentResponse,
)

router = APIRouter(prefix="/clusters", tags=["deployments"])


@router.get("/{cluster_id}/deployments", response_model=DeploymentListResponse)
async def list_deployments(
    cluster_id: UUID,
    user: CurrentUser,
    session: DbSession,
    namespace: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
) -> DeploymentListResponse:
    if user.org_id is None:
        raise PermissionDenied("user has no organization")

    query = (
        select(Deployment)
        .where(Deployment.org_id == user.org_id, Deployment.cluster_id == cluster_id)
        .order_by(Deployment.started_at.desc(), Deployment.id.desc())
        .limit(limit + 1)
    )
    if namespace:
        query = query.where(Deployment.namespace == namespace)
    if cursor:
        try:
            decoded = b64decode(cursor).decode()
            started_str, last_id = decoded.split("|", 1)
            last_started = datetime.fromisoformat(started_str)
            query = query.where(
                (Deployment.started_at < last_started)
                | (
                    (Deployment.started_at == last_started)
                    & (Deployment.id < UUID(last_id))
                )
            )
        except Exception:
            pass

    result = await session.scalars(query)
    deployments = list(result)
    has_more = len(deployments) > limit
    if has_more:
        deployments = deployments[:limit]

    items = [DeploymentResponse.model_validate(d) for d in deployments]
    next_cursor = None
    if has_more and deployments:
        last = deployments[-1]
        next_cursor = b64encode(
            f"{last.started_at.isoformat()}|{last.id}".encode()
        ).decode()

    return DeploymentListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.get("/{cluster_id}/config-changes", response_model=ConfigChangeListResponse)
async def list_config_changes(
    cluster_id: UUID,
    user: CurrentUser,
    session: DbSession,
    namespace: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
) -> ConfigChangeListResponse:
    if user.org_id is None:
        raise PermissionDenied("user has no organization")

    query = (
        select(ConfigChange)
        .where(ConfigChange.org_id == user.org_id, ConfigChange.cluster_id == cluster_id)
        .order_by(ConfigChange.detected_at.desc(), ConfigChange.id.desc())
        .limit(limit + 1)
    )
    if namespace:
        query = query.where(ConfigChange.namespace == namespace)
    if cursor:
        try:
            decoded = b64decode(cursor).decode()
            detected_str, last_id = decoded.split("|", 1)
            last_detected = datetime.fromisoformat(detected_str)
            query = query.where(
                (ConfigChange.detected_at < last_detected)
                | (
                    (ConfigChange.detected_at == last_detected)
                    & (ConfigChange.id < UUID(last_id))
                )
            )
        except Exception:
            pass

    result = await session.scalars(query)
    changes = list(result)
    has_more = len(changes) > limit
    if has_more:
        changes = changes[:limit]

    items = [ConfigChangeResponse.model_validate(c) for c in changes]
    next_cursor = None
    if has_more and changes:
        last = changes[-1]
        next_cursor = b64encode(
            f"{last.detected_at.isoformat()}|{last.id}".encode()
        ).decode()

    return ConfigChangeListResponse(items=items, next_cursor=next_cursor, has_more=has_more)
