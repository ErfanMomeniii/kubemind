"""Dashboard service: aggregate cluster health + recent changes + risk.

Per docs/modules/executive-dashboard.md. Health score computed from
Prometheus (availability, error rate, firing alerts) + DB (active incidents).
Recent deployments fetched from k8s. Warnings from Prometheus alerts.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import IntegrationError
from app.core.logging import get_logger
from app.models import Cluster, Incident
from app.schemas.dashboard import (
    AnomalyRef,
    ConfigChangeRef,
    DashboardResponse,
    DeploymentRef,
    HealthSummary,
    IncidentRef,
    RecentChanges,
    RiskService,
    WarningRef,
)
from integrations.k8s import KubernetesClient
from integrations.prometheus import PrometheusClient

log = get_logger()

HEALTHY_THRESHOLD = 95.0
DEGRADED_THRESHOLD = 70.0
CRITICAL_THRESHOLD = 40.0


async def build_dashboard(
    cluster: Cluster, session: AsyncSession
) -> DashboardResponse:
    """Aggregate dashboard payload for a cluster.

    Degrades gracefully: if Prometheus/k8s unreachable, returns partial data
    with data_stale=True and status Unknown.
    """
    prom = _prometheus_client(cluster)
    k8s = _k8s_client(cluster)

    availability, error_rate, firing_alerts, recent_deployments, anomalies = (
        await _gather_signals(prom, k8s)
    )
    active_incidents = await _active_incidents(cluster.org_id, cluster.id, session)

    health = _compute_health(availability, error_rate, firing_alerts, active_incidents)
    warnings = _warnings_from_alerts(firing_alerts)
    risk = _estimate_risk(recent_deployments, anomalies, firing_alerts)

    return DashboardResponse(
        cluster_id=str(cluster.id),
        health=health,
        incidents={
            "critical": [i for i in active_incidents if i.severity == "sev1"],
            "warnings": [],
        },
        warnings=warnings,
        recent_changes=RecentChanges(
            deployments=recent_deployments,
            config_changes=[],
            anomalies=anomalies,
        ),
        top_risk=risk,
        generated_at=datetime.now(timezone.utc),
        data_stale=availability is None,
    )


async def _gather_signals(
    prom: PrometheusClient, k8s: KubernetesClient
) -> tuple[
    float | None,
    float | None,
    list[dict],
    list[DeploymentRef],
    list[AnomalyRef],
]:
    availability: float | None = None
    error_rate: float | None = None
    firing_alerts: list[dict] = []
    recent_deployments: list[DeploymentRef] = []
    anomalies: list[AnomalyRef] = []

    try:
        availability = await prom.up_ratio(cluster=".*")
    except IntegrationError as exc:
        log.warning("prometheus_unavailable", error=str(exc))

    try:
        error_rate = await prom.error_rate()
    except IntegrationError as exc:
        log.warning("prometheus_error_rate_unavailable", error=str(exc))

    try:
        firing_alerts = await prom.firing_critical_alerts()
    except IntegrationError as exc:
        log.warning("prometheus_alerts_unavailable", error=str(exc))

    try:
        deployments = await k8s.get_deployments()
        now = datetime.now(timezone.utc)
        for d in deployments:
            started = _parse_deployment_time(d)
            if started and (now - started) < timedelta(hours=24):
                recent_deployments.append(
                    DeploymentRef(
                        service=d["name"],
                        version=d.get("image"),
                        namespace=d["namespace"],
                        deployed_by=None,
                        started_at=started,
                    )
                )
    except IntegrationError as exc:
        log.warning("k8s_deployments_unavailable", error=str(exc))

    try:
        pods = await k8s.get_pods()
        restart_counts: dict[str, int] = {}
        for p in pods:
            if p["restarts"] > 3:
                restart_counts[p["name"]] = p["restarts"]
        anomalies = [
            AnomalyRef(service=s, type="restarts", count=c)
            for s, c in restart_counts.items()
        ]
    except IntegrationError as exc:
        log.warning("k8s_pods_unavailable", error=str(exc))

    return availability, error_rate, firing_alerts, recent_deployments, anomalies


def _compute_health(
    availability: float | None,
    error_rate: float | None,
    firing_alerts: list[dict],
    incidents: list[IncidentRef],
) -> HealthSummary:
    if availability is None and error_rate is None:
        return HealthSummary(status="Unknown", score=0.0, availability=None)

    availability_score = (availability or 0.0) * 100
    error_score = max(0.0, 100.0 - (error_rate or 0.0) * 1000)
    critical_incidents = sum(1 for i in incidents if i.severity == "sev1")
    incident_score = 100.0 if critical_incidents == 0 else max(0.0, 100.0 - critical_incidents * 50)
    alert_score = max(0.0, 100.0 - len(firing_alerts) * 20)

    score = (
        availability_score * 0.4
        + error_score * 0.3
        + incident_score * 0.2
        + alert_score * 0.1
    )

    if score >= HEALTHY_THRESHOLD:
        status = "Healthy"
    elif score >= DEGRADED_THRESHOLD:
        status = "Degraded"
    elif score >= CRITICAL_THRESHOLD:
        status = "Critical"
    else:
        status = "Unknown"

    return HealthSummary(status=status, score=round(score, 1), availability=availability)


async def _active_incidents(
    org_id: UUID, cluster_id: UUID, session: AsyncSession
) -> list[IncidentRef]:
    result = await session.scalars(
        select(Incident).where(
            Incident.org_id == org_id,
            Incident.cluster_id == cluster_id,
            Incident.status.in_(["open", "investigating"]),
        )
    )
    refs: list[IncidentRef] = []
    for inc in result:
        age = None
        if inc.started_at:
            age = int((datetime.now(timezone.utc) - inc.started_at).total_seconds())
        refs.append(
            IncidentRef(
                id=str(inc.id),
                title=inc.title,
                severity=inc.severity,
                service=inc.service,
                age_seconds=age,
            )
        )
    return refs


def _warnings_from_alerts(alerts: list[dict]) -> list[WarningRef]:
    return [
        WarningRef(
            title=a.get("labels", {}).get("alertname", "unknown"),
            service=a.get("labels", {}).get("service"),
        )
        for a in alerts
        if a.get("state") == "firing"
    ]


def _estimate_risk(
    deployments: list[DeploymentRef],
    anomalies: list[AnomalyRef],
    alerts: list[dict],
) -> list[RiskService]:
    """Rough risk estimate for MVP. Real criticality comes from Architecture Discovery."""
    scores: dict[str, float] = {}
    reasons: dict[str, list[str]] = {}

    for d in deployments:
        scores[d.service] = scores.get(d.service, 0.0) + 0.3
        reasons.setdefault(d.service, []).append("recent deploy")

    for a in anomalies:
        scores[a.service] = scores.get(a.service, 0.0) + 0.4
        reasons.setdefault(a.service, []).append(f"{a.type} x{a.count}")

    for al in alerts:
        svc = al.get("labels", {}).get("service")
        if svc:
            scores[svc] = scores.get(svc, 0.0) + 0.3
            reasons.setdefault(svc, []).append("firing alert")

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:3]
    return [
        RiskService(
            service=svc,
            score=min(round(score, 2), 1.0),
            trend="unknown",
            reason=", ".join(reasons[svc]) if reasons.get(svc) else None,
        )
        for svc, score in ranked
    ]


def _parse_deployment_time(d: dict) -> datetime | None:
    # k8s deployment doesn't expose a clean "started_at"; use creation timestamp
    # in a real impl we'd track deploy events. For MVP, return None to skip.
    return None


def _prometheus_client(cluster: Cluster) -> PrometheusClient:
    from integrations.factory import make_prometheus_client

    return make_prometheus_client(cluster)


def _k8s_client(cluster: Cluster) -> KubernetesClient:
    from integrations.factory import make_k8s_client

    return make_k8s_client(cluster)
