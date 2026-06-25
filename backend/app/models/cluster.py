"""Cluster model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import SoftDelete, Timestamps, UUIDPk


class Cluster(UUIDPk, Timestamps, SoftDelete, Base):
    __tablename__ = "clusters"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(String(255), nullable=True)
    server_url: Mapped[str] = mapped_column(Text, nullable=False)
    prometheus_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    argocd_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    last_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Cluster {self.name}>"
