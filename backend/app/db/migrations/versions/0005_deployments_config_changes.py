"""add deployments and config_changes tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deployments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("namespace", sa.Text(), nullable=False),
        sa.Column("service", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("replicas_desired", sa.Integer(), nullable=True),
        sa.Column("replicas_ready", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("trigger", sa.String(32), nullable=True),
        sa.Column("deployed_by", sa.Text(), nullable=True),
        sa.Column("argocd_app", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deployments_org_id", "deployments", ["org_id"])
    op.create_index("ix_deployments_cluster_id", "deployments", ["cluster_id"])
    op.create_index(
        "ix_deployments_lookup",
        "deployments",
        ["cluster_id", "namespace", "service", "started_at"],
    )

    op.create_table(
        "config_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("namespace", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("change_type", sa.String(16), nullable=False),
        sa.Column("diff", sa.Text(), nullable=True),
        sa.Column("changed_by", sa.Text(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_config_changes_org_id", "config_changes", ["org_id"])
    op.create_index("ix_config_changes_cluster_id", "config_changes", ["cluster_id"])
    op.create_index(
        "ix_config_changes_detected",
        "config_changes",
        ["cluster_id", "detected_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_config_changes_detected", table_name="config_changes")
    op.drop_index("ix_config_changes_cluster_id", table_name="config_changes")
    op.drop_index("ix_config_changes_org_id", table_name="config_changes")
    op.drop_table("config_changes")
    op.drop_index("ix_deployments_lookup", table_name="deployments")
    op.drop_index("ix_deployments_cluster_id", table_name="deployments")
    op.drop_index("ix_deployments_org_id", table_name="deployments")
    op.drop_table("deployments")
