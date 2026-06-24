"""Deployment + config change sync service.

Fetches current state from k8s, detects changes vs last sync, persists.
MVP: on-demand via POST /clusters/{id}/sync. Post-MVP: scheduled RQ job.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import IntegrationError
from app.core.logging import get_logger
from app.models import Cluster, ConfigChange, Deployment
from integrations.k8s import KubernetesClient

log = get_logger()


async def sync_cluster(
    cluster: Cluster, session: AsyncSession
) -> dict[str, int]:
    """Sync deployments + config changes. Returns counts of new records."""
    k8s = KubernetesClient(cluster.server_url, context=cluster.context)
    now = datetime.now(timezone.utc)

    deployments_added = await _sync_deployments(cluster, k8s, session, now)
    config_changes_added = await _sync_config_changes(cluster, k8s, session, now)

    cluster.last_connected_at = now
    await session.commit()

    log.info(
        "sync_complete",
        cluster_id=str(cluster.id),
        deployments=deployments_added,
        config_changes=config_changes_added,
    )
    return {"deployments": deployments_added, "config_changes": config_changes_added}


async def _sync_deployments(
    cluster: Cluster, k8s: KubernetesClient, session: AsyncSession, now: datetime
) -> int:
    try:
        current = await k8s.get_deployments()
    except IntegrationError as exc:
        log.warning("sync_deployments_failed", error=str(exc))
        return 0

    added = 0
    for d in current:
        namespace = d.get("namespace", "")
        service = d.get("name", "")
        version = d.get("image") or "unknown"
        replicas_desired = d.get("replicas_desired")
        replicas_ready = d.get("replicas_ready")
        status = "available" if d.get("available", 0) > 0 else "progressing"

        last = await session.scalar(
            select(Deployment)
            .where(
                Deployment.cluster_id == cluster.id,
                Deployment.namespace == namespace,
                Deployment.service == service,
            )
            .order_by(Deployment.started_at.desc())
            .limit(1)
        )

        if last is not None and last.version == version:
            continue

        deployment = Deployment(
            org_id=cluster.org_id,
            cluster_id=cluster.id,
            namespace=namespace,
            service=service,
            version=version,
            replicas_desired=replicas_desired,
            replicas_ready=replicas_ready,
            status=status,
            trigger=None,
            started_at=last.completed_at if last else now,
            synced_at=now,
        )
        if last is not None:
            last.completed_at = now
        session.add(deployment)
        added += 1

    return added


async def _sync_config_changes(
    cluster: Cluster, k8s: KubernetesClient, session: AsyncSession, now: datetime
) -> int:
    try:
        events = await k8s.get_events()
    except IntegrationError as exc:
        log.warning("sync_config_changes_failed", error=str(exc))
        return 0

    added = 0
    last_synced = await session.scalar(
        select(ConfigChange.detected_at)
        .where(ConfigChange.cluster_id == cluster.id)
        .order_by(ConfigChange.detected_at.desc())
        .limit(1)
    )

    for e in events:
        if not _is_config_event(e):
            continue
        detected = _parse_event_time(e)
        if detected is None:
            continue
        if last_synced is not None and detected <= last_synced:
            continue

        change = ConfigChange(
            org_id=cluster.org_id,
            cluster_id=cluster.id,
            namespace=e.get("namespace", ""),
            kind=_config_kind(e),
            name=_config_name(e),
            change_type=_change_type(e),
            diff=None,
            changed_by=None,
            detected_at=detected,
            synced_at=now,
        )
        session.add(change)
        added += 1

    return added


def _is_config_event(e: dict) -> bool:
    reason = (e.get("reason") or "").lower()
    return reason in {"created", "updated", "deleted"} and _config_kind(e) is not None


def _config_kind(e: dict) -> str | None:
    msg = e.get("message", "") or ""
    for kind in ("ConfigMap", "Secret"):
        if kind in msg:
            return kind
    return None


def _config_name(e: dict) -> str:
    msg = e.get("message", "") or ""
    parts = msg.split()
    for i, p in enumerate(parts):
        if p in ("ConfigMap", "Secret") and i + 1 < len(parts):
            return parts[i + 1].strip("'\"")
    return e.get("name", "unknown")


def _change_type(e: dict) -> str:
    reason = (e.get("reason") or "").lower()
    if reason == "created":
        return "created"
    if reason == "deleted":
        return "deleted"
    return "updated"


def _parse_event_time(e: dict) -> datetime | None:
    ts = e.get("last_timestamp")
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None
