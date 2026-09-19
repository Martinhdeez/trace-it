"""Proposals from the escalation assistant, the process chat and learning.

Revision ID: 0015
Revises: 0014
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("processes.id"), nullable=False),
        sa.Column("instance_id", sa.Integer(), sa.ForeignKey("instances.id")),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("rationale", sa.String(), nullable=False),
        sa.Column("evidence", JSONB(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("resolved_by", sa.String()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("outcome", JSONB()),
    )
    op.create_index("ix_proposals_process_id", "proposals", ["process_id"])


def downgrade() -> None:
    op.drop_table("proposals")
