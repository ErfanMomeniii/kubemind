"""Dependency model (service map edges)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import UUIDPk


class Dependency(UUIDPk, Base):
    __tablename__ = "dependencies"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clusters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_service: Mapped[str] = mapped_column(Text, nullable=False)  # namespace/name
    to_service: Mapped[str] = mapped_column(Text, nullable=False)  # namespace/name or external
    to_kind: Mapped[str] = mapped_column(String(32), nullable=False)  # service|database|queue|external
    detected_via: Mapped[str] = mapped_column(String(32), nullable=False)  # env_var|dns|ingress
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<Dependency {self.from_service} → {self.to_service}>"
