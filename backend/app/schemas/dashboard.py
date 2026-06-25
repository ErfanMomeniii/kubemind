"""Dashboard response schemas (per docs/modules/executive-dashboard.md)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class HealthSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    status: Literal["Healthy", "Degraded", "Critical", "Unknown"]
    score: float
    availability: float | None


class IncidentRef(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str
    title: str
    severity: str
    service: str | None
    age_seconds: int | None


class DeploymentRef(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    service: str
    version: str | None
    namespace: str
    deployed_by: str | None
    started_at: datetime


class ConfigChangeRef(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    kind: str
    name: str
    namespace: str
    changed_by: str | None
    detected_at: datetime


class AnomalyRef(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    service: str
    type: str
    count: int


class RecentChanges(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    deployments: list[DeploymentRef]
    config_changes: list[ConfigChangeRef]
    anomalies: list[AnomalyRef]


class WarningRef(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    title: str
    service: str | None


class RiskService(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    service: str
    score: float
    trend: Literal["rising", "stable", "falling", "unknown"]
    reason: str | None


class DashboardResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    cluster_id: str
    health: HealthSummary
    incidents: dict[str, list[IncidentRef]]
    warnings: list[WarningRef]
    recent_changes: RecentChanges
    top_risk: list[RiskService]
    generated_at: datetime
    data_stale: bool
