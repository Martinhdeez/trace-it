"""A symbol can be required: an instance missing it always escalates (ADR 0016).

Revision ID: 0007
Revises: 0005 (rechain to 0006 once the observability migration lands)
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "symbols",
        sa.Column("required", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("symbols", "required")
