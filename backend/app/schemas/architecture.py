"""Architecture response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ServiceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    cluster_id: UUID
    namespace: str
    name: str
    kind: str
    criticality_score: float | None
    synced_at: datetime


class DependencyResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    cluster_id: UUID
    from_service: str
    to_service: str
    to_kind: str
    detected_via: str
    synced_at: datetime


class ArchitectureGraphResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    services: list[ServiceResponse]
    dependencies: list[DependencyResponse]


class BlastRadiusResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    service: str
    direct_downstream: list[str]
    total_downstream: list[str]
    upstream: list[str]
    affected_count: int
