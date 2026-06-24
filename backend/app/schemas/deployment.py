"""Deployment + config change response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeploymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cluster_id: UUID
    namespace: str
    service: str
    version: str
    replicas_desired: int | None
    replicas_ready: int | None
    status: str
    trigger: str | None
    deployed_by: str | None
    started_at: datetime
    completed_at: datetime | None
    synced_at: datetime


class DeploymentListResponse(BaseModel):
    items: list[DeploymentResponse]
    next_cursor: str | None = None
    has_more: bool = False


class ConfigChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cluster_id: UUID
    namespace: str
    kind: str
    name: str
    change_type: str
    changed_by: str | None
    detected_at: datetime
    synced_at: datetime


class ConfigChangeListResponse(BaseModel):
    items: list[ConfigChangeResponse]
    next_cursor: str | None = None
    has_more: bool = False
