"""quitar contexto de decisiones

`contexto` duplicated what a process already expresses as data: anything a rule needs but
cannot read from the clock (a cut-off date, for instance) is a row in a source of truth,
such as `parametros.fecha_corte` in the invoice process. One mechanism, not two.

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
    op.drop_column("decisiones", "contexto")


def downgrade() -> None:
    op.add_column(
        "decisiones",
        sa.Column(
            "contexto",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
