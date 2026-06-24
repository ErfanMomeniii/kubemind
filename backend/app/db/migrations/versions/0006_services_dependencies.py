"""add services and dependencies tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("namespace", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("criticality_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("cluster_id", "namespace", "name", name="uq_services_cluster_ns_name"),
    )
    op.create_index("ix_services_org_id", "services", ["org_id"])
    op.create_index("ix_services_cluster_id", "services", ["cluster_id"])

    op.create_table(
        "dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_service", sa.Text(), nullable=False),
        sa.Column("to_service", sa.Text(), nullable=False),
        sa.Column("to_kind", sa.String(32), nullable=False),
        sa.Column("detected_via", sa.String(32), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "cluster_id", "from_service", "to_service", "to_kind",
            name="uq_dependencies_cluster_edge",
        ),
    )
    op.create_index("ix_dependencies_org_id", "dependencies", ["org_id"])
    op.create_index("ix_dependencies_cluster_id", "dependencies", ["cluster_id"])
    op.create_index("ix_dependencies_from", "dependencies", ["cluster_id", "from_service"])
    op.create_index("ix_dependencies_to", "dependencies", ["cluster_id", "to_service"])


def downgrade() -> None:
    op.drop_index("ix_dependencies_to", table_name="dependencies")
    op.drop_index("ix_dependencies_from", table_name="dependencies")
    op.drop_index("ix_dependencies_cluster_id", table_name="dependencies")
    op.drop_index("ix_dependencies_org_id", table_name="dependencies")
    op.drop_table("dependencies")
    op.drop_index("ix_services_cluster_id", table_name="services")
    op.drop_index("ix_services_org_id", table_name="services")
    op.drop_table("services")
