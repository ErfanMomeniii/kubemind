"""Cluster request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from pydantic.alias_generators import to_camel


class ClusterCredential(BaseModel):
    type: str = Field(description="service_account_token | kubeconfig | oidc")
    token: str = Field(description="credential value, stored in secret manager")
    namespace: str = Field(default="kubemind")


class ClusterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    display_name: str = Field(min_length=1, max_length=200)
    server_url: HttpUrl
    prometheus_url: HttpUrl | None = None
    argocd_url: HttpUrl | None = None
    context: str | None = None
    credential: ClusterCredential


class ClusterUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = Field(default=None, pattern=r"^(active|inactive)$")


class ClusterResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: UUID
    org_id: UUID
    name: str
    display_name: str
    server_url: str
    prometheus_url: str | None
    argocd_url: str | None
    status: str
    last_connected_at: datetime | None
    created_at: datetime


class ClusterListResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: list[ClusterResponse]
    next_cursor: str | None = None
    has_more: bool = False
