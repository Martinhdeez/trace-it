"""Events become spans: trace and parent ids, start, duration, status and links (ADR 0018).

The foreign keys go: an audit row must never block, or be blocked by, the transaction it
describes (spans are written on their own connection). Existing rows become one-span
traces. Historical `cost` is retained exactly in `data.legacy_cost_usd` before the
numeric column is removed; token counts alone cannot reconstruct a historical price.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LINKS = ("rule_id", "norm_rule_id")  # process_id arrived in 0005


def upgrade() -> None:
    op.drop_constraint(op.f("fk_events_instance_id"), "events", type_="foreignkey")
    op.drop_constraint(op.f("fk_events_process_id"), "events", type_="foreignkey")
    op.alter_column("events", "latency_ms", new_column_name="duration_ms")
    # Never replace an existing audit key. The marker also lets downgrade distinguish
    # migrated rows from spans written after this migration.
    op.execute(
        "DO $$ BEGIN IF EXISTS ("
        " SELECT 1 FROM events WHERE cost IS NOT NULL AND data IS NOT NULL AND ("
        " jsonb_typeof(data) <> 'object' OR data ? 'legacy_cost_usd'"
        " OR data ? 'legacy_cost_migrated_0008' OR data ? 'legacy_cost_data_was_null_0008'"
        ")) THEN RAISE EXCEPTION 'Event audit data conflicts with legacy cost migration';"
        " END IF; END $$"
    )
    op.execute(
        "UPDATE events SET data = COALESCE(data, '{}'::jsonb)"
        " || jsonb_build_object('legacy_cost_usd', cost, 'legacy_cost_migrated_0008', true)"
        " || CASE WHEN data IS NULL THEN"
        " jsonb_build_object('legacy_cost_data_was_null_0008', true) ELSE '{}'::jsonb END"
        " WHERE cost IS NOT NULL"
    )
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
    op.execute(
        "UPDATE events SET cost = (data->>'legacy_cost_usd')::numeric,"
        " data = CASE WHEN data->>'legacy_cost_data_was_null_0008' = 'true'"
        " THEN NULL ELSE data - 'legacy_cost_usd' - 'legacy_cost_migrated_0008'"
        " - 'legacy_cost_data_was_null_0008' END"
        " WHERE data->>'legacy_cost_migrated_0008' = 'true'"
    )
    op.alter_column("events", "duration_ms", new_column_name="latency_ms")
    op.execute("DELETE FROM events WHERE instance_id NOT IN (SELECT id FROM instances)")
    op.execute("DELETE FROM events WHERE process_id NOT IN (SELECT id FROM processes)")
    op.create_foreign_key(
        op.f("fk_events_instance_id"), "events", "instances", ["instance_id"], ["id"]
    )
    op.create_foreign_key(
        op.f("fk_events_process_id"), "events", "processes", ["process_id"], ["id"]
    )
