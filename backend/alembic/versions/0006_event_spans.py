"""Events become spans: trace and parent ids, start, duration, status and links (ADR 0018).

The foreign keys go: an audit row must never block, or be blocked by, the transaction it
describes (spans are written on their own connection). Existing rows become one-span
traces. `cost` goes: cost is counted in tokens (`data.input_tokens`, `data.output_tokens`).

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LINKS = ("rule_id", "norm_rule_id")  # process_id arrived in 0005


def upgrade() -> None:
    op.drop_constraint(op.f("fk_events_instance_id"), "events", type_="foreignkey")
    op.drop_constraint(op.f("fk_events_process_id"), "events", type_="foreignkey")
    op.alter_column("events", "latency_ms", new_column_name="duration_ms")
    op.drop_column("events", "cost")
    for name, type_ in (
        ("trace_id", sa.String()),
        ("span_id", sa.String()),
        ("parent_id", sa.String()),
        ("status", sa.String()),
        ("started_at", sa.DateTime(timezone=True)),
        *((link, sa.Integer()) for link in LINKS),
    ):
        op.add_column("events", sa.Column(name, type_, nullable=True))
    op.execute(
        "UPDATE events SET trace_id = md5('trace' || id), span_id = left(md5('span' || id), 16),"
        " status = 'ok', started_at = created_at"
    )
    for name in ("trace_id", "span_id", "status", "started_at"):
        op.alter_column("events", name, nullable=False)
    for name in ("trace_id", "started_at", *LINKS):
        op.create_index(op.f(f"ix_events_{name}"), "events", [name])


def downgrade() -> None:
    for name in ("trace_id", "started_at", *LINKS):
        op.drop_index(op.f(f"ix_events_{name}"), "events")
    for name in ("trace_id", "span_id", "parent_id", "status", "started_at", *LINKS):
        op.drop_column("events", name)
    op.add_column("events", sa.Column("cost", sa.Numeric(), nullable=True))
    op.alter_column("events", "duration_ms", new_column_name="latency_ms")
    op.execute("DELETE FROM events WHERE instance_id NOT IN (SELECT id FROM instances)")
    op.execute("DELETE FROM events WHERE process_id NOT IN (SELECT id FROM processes)")
    op.create_foreign_key(
        op.f("fk_events_instance_id"), "events", "instances", ["instance_id"], ["id"]
    )
    op.create_foreign_key(
        op.f("fk_events_process_id"), "events", "processes", ["process_id"], ["id"]
    )
