"""On-demand norm proposals, isolated validations and manager adoptions."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def identity():
    return [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "learning_analyses",
        *identity(),
        sa.Column("process_id", sa.Integer(), sa.ForeignKey("processes.id"), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("snapshot", JSONB(), nullable=False),
        sa.Column("reasoning", sa.String(), nullable=False),
    )
    op.create_index("ix_learning_analyses_process_id", "learning_analyses", ["process_id"])
    op.create_table(
        "norm_proposals",
        *identity(),
        sa.Column(
            "analysis_id", sa.Integer(), sa.ForeignKey("learning_analyses.id"), nullable=False
        ),
        *[
            sa.Column(name, sa.String(), nullable=False)
            for name in ("kind", "text", "reasoning", "limitations")
        ],
        sa.Column("evidence", JSONB(), nullable=False),
        sa.Column("counterexamples", JSONB(), nullable=False),
    )
    op.create_index("ix_norm_proposals_analysis_id", "norm_proposals", ["analysis_id"])
    op.create_table(
        "norm_validations",
        *identity(),
        sa.Column("proposal_id", sa.Integer(), sa.ForeignKey("norm_proposals.id"), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("baseline", sa.String(), nullable=False),
        sa.Column("snapshot", JSONB(), nullable=False),
        sa.Column("report", JSONB(), nullable=False),
    )
    op.create_index("ix_norm_validations_proposal_id", "norm_validations", ["proposal_id"])
    op.create_table(
        "norm_adoptions",
        *identity(),
        sa.Column(
            "proposal_id",
            sa.Integer(),
            sa.ForeignKey("norm_proposals.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("validation_id", sa.Integer(), sa.ForeignKey("norm_validations.id")),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("snapshot", JSONB(), nullable=False),
    )


def downgrade() -> None:
    for name in ("norm_adoptions", "norm_validations", "norm_proposals", "learning_analyses"):
        op.drop_table(name)
