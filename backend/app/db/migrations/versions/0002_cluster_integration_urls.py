"""add integration urls to clusters

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clusters", sa.Column("prometheus_url", sa.Text(), nullable=True))
    op.add_column("clusters", sa.Column("argocd_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("clusters", "argocd_url")
    op.drop_column("clusters", "prometheus_url")
