"""Rule statuses `compiling` (code being written in the background) and `blocked` (needs
data the process does not have; every instance escalates).

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _status_check(values: str) -> None:
    op.drop_constraint(op.f("ck_rules_status"), "rules", type_="check")
    op.create_check_constraint(op.f("ck_rules_status"), "rules", f"status in ({values})")


def upgrade() -> None:
    _status_check("'compiling', 'draft', 'active', 'blocked', 'retired'")


def downgrade() -> None:
    op.execute("UPDATE rules SET status = 'draft' WHERE status IN ('compiling', 'blocked')")
    _status_check("'draft', 'active', 'retired'")
