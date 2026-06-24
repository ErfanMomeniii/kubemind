"""Cluster request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ClusterCredential(BaseModel):
    """Cluster credential. Token stored in Vault/k8s Secret, not DB."""

    type: str = Field(description="service_account_token | kubeconfig | oidc")
    token: str = Field(description="credential value, stored in secret manager")
    namespace: str = Field(default="kubemind")


class ClusterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    display_name: str = Field(min_length=1, max_length=200)
    server_url: HttpUrl
    context: str | None = None
    credential: ClusterCredential


class ClusterUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = Field(default=None, pattern=r"^(active|inactive)$")


class ClusterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    name: str
    display_name: str
    server_url: str
    status: str
    last_connected_at: datetime | None
    created_at: datetime


class ClusterListResponse(BaseModel):
    items: list[ClusterResponse]
    next_cursor: str | None = None
    has_more: bool = False
