"""Norm rules: the sentences of the client's norm, each owning its atomic rules.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "norm_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("process_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("policies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["process_id"], ["processes.id"], name=op.f("fk_norm_rules_process_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_norm_rules")),
    )
    op.add_column("rules", sa.Column("norm_rule_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_rules_norm_rule_id"), "rules", "norm_rules", ["norm_rule_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_rules_norm_rule_id"), "rules", type_="foreignkey")
    op.drop_column("rules", "norm_rule_id")
    op.drop_table("norm_rules")
