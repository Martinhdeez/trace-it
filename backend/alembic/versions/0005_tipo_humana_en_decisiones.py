"""tipo humana en decisiones

A person's decision says what kind it is: `resolucion` (settles a case whose type requires a
person; never changes the export, P4) or `correccion_revision` (settles an instance that was
in REVISION). Engine decisions keep it NULL. Earlier person decisions are marked
`resolucion`, the kind that never touches the export.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("decisiones", sa.Column("tipo_humana", sa.String(), nullable=True))
    op.create_check_constraint(
        op.f("ck_decisiones_tipo_humana"),
        "decisiones",
        "tipo_humana in ('resolucion', 'correccion_revision')",
    )
    op.execute("UPDATE decisiones SET tipo_humana = 'resolucion' WHERE autor <> 'motor'")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_decisiones_tipo_humana"), "decisiones", type_="check")
    op.drop_column("decisiones", "tipo_humana")
