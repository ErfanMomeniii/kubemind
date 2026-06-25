"""Architecture discovery: sync services + dependencies, compute blast radius.

Services discovered from k8s deployments. Dependencies detected from env vars
that reference other services (URLs, hostnames). Post-MVP: service mesh data
(Istio/Envoy) for richer detection. See docs/architecture.md.
"""

import re
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import IntegrationError
from app.core.logging import get_logger
from app.models import Cluster, Dependency, Service
from integrations.factory import make_k8s_client
from integrations.k8s import KubernetesClient

log = get_logger()

# Heuristics for env-var-based dependency detection
URL_VAR_PATTERN = re.compile(r"^(.+?)(_URL|_HOST|_ENDPOINT|_ADDR|_ADDRESS)$", re.IGNORECASE)


async def sync_architecture(
    cluster: Cluster, session: AsyncSession
) -> dict[str, int]:
    """Discover services + dependencies from k8s. Replaces previous snapshot."""
    k8s = make_k8s_client(cluster)
    now = datetime.now(timezone.utc)

    try:
        deployments = await k8s.get_deployments()
    except IntegrationError as exc:
        log.warning("arch_sync_failed", error=str(exc))
        return {"services": 0, "dependencies": 0}

    services = _extract_services(cluster, deployments, now)
    dependencies = _detect_dependencies(cluster, deployments, services, now)

    await _replace_snapshot(cluster, session, services, dependencies)
    await session.commit()

    log.info(
        "arch_sync_complete",
        cluster_id=str(cluster.id),
        services=len(services),
        dependencies=len(dependencies),
    )
    return {"services": len(services), "dependencies": len(dependencies)}


def _extract_services(
    cluster: Cluster, deployments: list[dict], now: datetime
) -> list[Service]:
    seen: set[tuple[str, str]] = set()
    services: list[Service] = []
    for d in deployments:
        ns = d.get("namespace", "")
        name = d.get("name", "")
        if not name or (ns, name) in seen:
            continue
        seen.add((ns, name))
        services.append(
            Service(
                org_id=cluster.org_id,
                cluster_id=cluster.id,
                namespace=ns,
                name=name,
                kind="Deployment",
                criticality_score=None,
                synced_at=now,
            )
        )
    return services


def _detect_dependencies(
    cluster: Cluster,
    deployments: list[dict],
    services: list[Service],
    now: datetime,
) -> list[Dependency]:
    service_names = {s.name for s in services}
    deps: list[Dependency] = []
    seen_edges: set[tuple[str, str, str]] = set()

    for d in deployments:
        from_name = d.get("name", "")
        from_ns = d.get("namespace", "")
        from_full = f"{from_ns}/{from_name}"
        env_vars = d.get("env_vars", {}) or {}

        for var_name, value in env_vars.items():
            target = _extract_service_target(var_name, value, service_names)
            if target is None:
                continue
            to_service, to_kind = target
            edge = (from_full, to_service, to_kind)
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            deps.append(
                Dependency(
                    org_id=cluster.org_id,
                    cluster_id=cluster.id,
                    from_service=from_full,
                    to_service=to_service,
                    to_kind=to_kind,
                    detected_via="env_var",
                    synced_at=now,
                )
            )

    return deps


def _extract_service_target(
    var_name: str, value: str, known_services: set[str]
) -> tuple[str, str] | None:
    """Return (target_name, target_kind) or None if not a service dependency."""
    if not value:
        return None

    host = _extract_host(value)
    if host is None:
        return None

    # Matches a known in-cluster service name (e.g. "payment-api")
    if host in known_services:
        return (host, "service")

    # External datastore heuristics
    lower = host.lower()
    if any(k in lower for k in ("postgres", "pg", "mysql", "db", "database")):
        return (host, "database")
    if any(k in lower for k in ("redis", "cache", "memcached")):
        return (host, "database")
    if any(k in lower for k in ("kafka", "rabbitmq", "nats", "sqs", "queue")):
        return (host, "queue")

    # URL-shaped var referencing something service-like
    if URL_VAR_PATTERN.match(var_name) and "." not in host.split(".")[0]:
        return (host, "external")

    return None


def _extract_host(value: str) -> str | None:
    """Pull a hostname from a URL or bare host:port string."""
    v = value.strip()
    if "://" in v:
        parsed = urlparse(v)
        host = parsed.hostname
        if host:
            return host.lower()
    # bare host[:port]
    if re.fullmatch(r"[a-zA-Z0-9._-]+(:\d+)?", v):
        return v.split(":")[0].lower()
    return None


async def _replace_snapshot(
    cluster: Cluster,
    session: AsyncSession,
    services: list[Service],
    dependencies: list[Dependency],
) -> None:
    await session.execute(
        delete(Dependency).where(Dependency.cluster_id == cluster.id)
    )
    await session.execute(
        delete(Service).where(Service.cluster_id == cluster.id)
    )
    for s in services:
        session.add(s)
    for d in dependencies:
        session.add(d)


async def compute_blast_radius(
    cluster_id, service_name: str, session: AsyncSession
) -> dict:
    """If service X goes down, what fails? Walks the dependency graph.

    Returns: {direct_downstream, total_downstream, upstream, affected_services}
    """
    result = await session.scalars(
        select(Dependency).where(Dependency.cluster_id == cluster_id)
    )
    all_deps = list(result)

    downstream = _walk_downstream(service_name, all_deps)
    upstream = _walk_upstream(service_name, all_deps)

    return {
        "service": service_name,
        "direct_downstream": downstream["direct"],
        "total_downstream": downstream["all"],
        "upstream": upstream,
        "affected_count": len(downstream["all"]) + len(upstream) + 1,
    }


def _walk_downstream(
    service: str, deps: list[Dependency]
) -> dict[str, list[str]]:
    """Services that depend on `service` (directly + transitively)."""
    # from_service depends on to_service. So downstream of X = services whose to_service matches X.
    adj: dict[str, list[str]] = defaultdict(list)
    for d in deps:
        adj[d.to_service].append(d.from_service)

    direct = adj.get(service, [])
    visited: set[str] = set()
    queue = list(direct)
    while queue:
        current = queue.pop()
        if current in visited:
            continue
        visited.add(current)
        for nxt in adj.get(current, []):
            if nxt not in visited:
                queue.append(nxt)
    return {"direct": direct, "all": sorted(visited)}


def _walk_upstream(service: str, deps: list[Dependency]) -> list[str]:
    """Services that `service` depends on (directly)."""
    full = service if "/" in service else f"*/{service}"
    direct: list[str] = []
    for d in deps:
        if d.from_service == service or d.from_service.endswith(f"/{service}"):
            direct.append(d.to_service)
    return sorted(set(direct))
