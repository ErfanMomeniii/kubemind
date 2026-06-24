"""Organization model."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.mixins import SoftDelete, Timestamps, UUIDPk
from app.db.session import Base


class Organization(UUIDPk, Timestamps, SoftDelete, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="community")
    region: Mapped[str | None] = mapped_column(String(32), nullable=True)

    users: Mapped[list["User"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="org",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Organization {self.slug}>"
