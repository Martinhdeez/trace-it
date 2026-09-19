"""Events carry the process they belong to, so a process has one trace feed.

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
    op.add_column("events", sa.Column("process_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_events_process_id"), "events", "processes", ["process_id"], ["id"]
    )
    op.create_index(op.f("ix_events_process_id"), "events", ["process_id"], unique=False)
    # Events already recorded for an instance belong to that instance's process.
    op.execute(
        "UPDATE events SET process_id = instances.process_id "
        "FROM instances WHERE events.instance_id = instances.id"
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_events_process_id"), table_name="events")
    op.drop_constraint(op.f("fk_events_process_id"), "events", type_="foreignkey")
    op.drop_column("events", "process_id")
