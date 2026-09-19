"""Stale decision alerts (ADR 0026).

Revision ID: 0013
Revises: 0012
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("processes.id"), nullable=False),
        sa.Column("instance_id", sa.Integer(), sa.ForeignKey("instances.id"), nullable=False),
        sa.Column("decision_id", sa.Integer(), sa.ForeignKey("decisions.id"), nullable=False),
        sa.Column("before", sa.String(), nullable=False),
        sa.Column("after", sa.String(), nullable=False),
        sa.Column("trigger", JSONB(), nullable=False),
        sa.Column("evidence", JSONB(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("acknowledged_by", sa.String()),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("note", sa.String()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("decision_id", "after"),
    )
    op.create_index("ix_alerts_process_id", "alerts", ["process_id"])


def downgrade() -> None:
    op.drop_table("alerts")
