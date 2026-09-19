"""Optional decision reviews, stored separately from immutable decisions.

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("processes", sa.Column("decision_review", postgresql.JSONB(), nullable=True))
    op.create_table(
        "decision_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("decision_id", sa.Integer(), sa.ForeignKey("decisions.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("recommendation", sa.String(), nullable=True),
        sa.Column("reasoning", sa.String(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("requires_human", sa.Boolean(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("decision_id"),
    )


def downgrade() -> None:
    op.drop_table("decision_reviews")
    op.drop_column("processes", "decision_review")
