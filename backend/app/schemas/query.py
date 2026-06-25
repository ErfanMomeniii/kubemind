"""Query request/response schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class QueryRequest(BaseModel):
    cluster_id: UUID
    query: str = Field(min_length=1, max_length=2000)


class QueryResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    cluster_id: UUID
    text: str
    status: str
    answer: str | None
    confidence: Literal["high", "medium", "low"] | None
    investigation_id: UUID | None
    created_at: datetime
    completed_at: datetime | None


class InvestigationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    query_id: UUID
    cluster_id: UUID
    status: str
    root_cause: str | None
    confidence: Literal["high", "medium", "low"] | None
    evidence: list[dict]
    steps: list[dict]
    proposed_action: dict | None = None
    created_at: datetime
    completed_at: datetime | None


class QueryListResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    items: list[QueryResponse]
    next_cursor: str | None = None
    has_more: bool = False
