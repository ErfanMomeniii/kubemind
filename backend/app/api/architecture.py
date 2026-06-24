"""Architecture routes: services, dependencies graph, blast radius."""

from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from app.api.auth_deps import CurrentUser, DbSession
from app.core.exceptions import NotFound, PermissionDenied
from app.models import Cluster, Dependency, Service
from app.schemas.architecture import (
    ArchitectureGraphResponse,
    BlastRadiusResponse,
    DependencyResponse,
    ServiceResponse,
)
from app.services import architecture_service

router = APIRouter(prefix="/clusters", tags=["architecture"])


@router.post("/{cluster_id}/architecture/sync")
async def sync_architecture(
    cluster_id: UUID, user: CurrentUser, session: DbSession
) -> dict[str, int]:
    if user.org_id is None:
        raise PermissionDenied("user has no organization")
    cluster = await _load_cluster(cluster_id, user.org_id, session)
    return await architecture_service.sync_architecture(cluster, session)


@router.get("/{cluster_id}/services", response_model=list[ServiceResponse])
async def list_services(
    cluster_id: UUID, user: CurrentUser, session: DbSession
) -> list[ServiceResponse]:
    if user.org_id is None:
        raise PermissionDenied("user has no organization")
    await _load_cluster(cluster_id, user.org_id, session)
    result = await session.scalars(
        select(Service)
        .where(Service.cluster_id == cluster_id)
        .order_by(Service.namespace, Service.name)
    )
    return [ServiceResponse.model_validate(s) for s in result]


@router.get("/{cluster_id}/dependencies", response_model=ArchitectureGraphResponse)
async def get_dependency_graph(
    cluster_id: UUID, user: CurrentUser, session: DbSession
) -> ArchitectureGraphResponse:
    if user.org_id is None:
        raise PermissionDenied("user has no organization")
    await _load_cluster(cluster_id, user.org_id, session)

    services = await session.scalars(
        select(Service).where(Service.cluster_id == cluster_id)
    )
    deps = await session.scalars(
        select(Dependency).where(Dependency.cluster_id == cluster_id)
    )
    return ArchitectureGraphResponse(
        services=[ServiceResponse.model_validate(s) for s in services],
        dependencies=[DependencyResponse.model_validate(d) for d in deps],
    )


@router.get(
    "/{cluster_id}/services/{service_name}/blast-radius",
    response_model=BlastRadiusResponse,
)
async def get_blast_radius(
    cluster_id: UUID,
    service_name: str,
    user: CurrentUser,
    session: DbSession,
) -> BlastRadiusResponse:
    if user.org_id is None:
        raise PermissionDenied("user has no organization")
    await _load_cluster(cluster_id, user.org_id, session)
    result = await architecture_service.compute_blast_radius(
        cluster_id, service_name, session
    )
    return BlastRadiusResponse(**result)


async def _load_cluster(cluster_id: UUID, org_id, session) -> Cluster:
    cluster = await session.scalar(
        select(Cluster).where(
            Cluster.id == cluster_id,
            Cluster.org_id == org_id,
            Cluster.deleted_at.is_(None),
        )
    )
    if cluster is None:
        raise NotFound("cluster not found", {"cluster_id": str(cluster_id)})
    return cluster
