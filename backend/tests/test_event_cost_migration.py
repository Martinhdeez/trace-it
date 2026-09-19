"""Migration 0008 retains the exact historical cost and audit payload."""

import importlib.util
import os
import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def _migration():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/0008_event_spans.py"
    spec = importlib.util.spec_from_file_location("event_spans_0008", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_event_cost_survives_upgrade_and_downgrade_in_isolated_schema():
    url = os.environ.get("TRACE_DATABASE_URL", "")
    if not url or not re.search(r"/trace_test(?:_[A-Za-z0-9_]+)?$", url):
        pytest.skip("Migration regression needs an explicitly configured private test database")
    schema = "migration_0008_" + uuid.uuid4().hex
    assert re.fullmatch(r"migration_0008_[0-9a-f]{32}", schema)
    engine = sa.create_engine(url)
    migration = _migration()
    rows = [
        (1, '{"message":"priced","cost_usd":"unrelated"}', "1.2300456789"),
        (2, '{"message":"free"}', "0"),
        (3, None, "0.000000001"),
        (4, '{"message":"unpriced"}', None),
    ]
    created_at = datetime(2025, 5, 17, 10, 30, tzinfo=UTC)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}", public')
            connection.exec_driver_sql("CREATE TABLE processes (id integer PRIMARY KEY)")
            connection.exec_driver_sql("CREATE TABLE instances (id integer PRIMARY KEY)")
            connection.exec_driver_sql(
                "CREATE TABLE events ("
                "id bigint PRIMARY KEY, instance_id integer, process_id integer,"
                "step text NOT NULL, data jsonb, latency_ms integer, cost numeric,"
                "created_at timestamptz NOT NULL,"
                "CONSTRAINT fk_events_instance_id FOREIGN KEY (instance_id)"
                " REFERENCES instances(id),"
                "CONSTRAINT fk_events_process_id FOREIGN KEY (process_id) REFERENCES processes(id)"
                ")"
            )
            connection.execute(sa.text("INSERT INTO processes (id) VALUES (7)"))
            connection.execute(sa.text("INSERT INTO instances (id) VALUES (9)"))
            for id_, data, cost in rows:
                connection.execute(
                    sa.text(
                        "INSERT INTO events "
                        "(id, instance_id, process_id, step, data, latency_ms, cost, created_at) "
                        "VALUES (:id, 9, 7, 'llm_run', CAST(:data AS jsonb), 42, "
                        "CAST(:cost AS numeric), :created_at)"
                    ),
                    {"id": id_, "data": data, "cost": cost, "created_at": created_at},
                )
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                migration.upgrade()
            upgraded = connection.execute(
                sa.text(
                    "SELECT id, data, data->>'legacy_cost_usd', duration_ms, created_at, "
                    "started_at, trace_id, span_id, status FROM events ORDER BY id"
                )
            ).all()
            assert [row[0] for row in upgraded] == [1, 2, 3, 4]
            assert [Decimal(row[2]) if row[2] is not None else None for row in upgraded] == [
                Decimal("1.2300456789"),
                Decimal("0"),
                Decimal("0.000000001"),
                None,
            ]
            assert upgraded[0][1]["cost_usd"] == "unrelated"
            assert upgraded[0][1]["message"] == "priced"
            assert upgraded[3][1] == {"message": "unpriced"}
            assert all(row[3] == 42 and row[4] == row[5] == created_at for row in upgraded)
            assert all(row[6] and row[7] and row[8] == "ok" for row in upgraded)

            with Operations.context(context):
                migration.downgrade()
            restored = connection.execute(
                sa.text("SELECT id, data, cost, latency_ms, created_at FROM events ORDER BY id")
            ).all()
            assert [row[0] for row in restored] == [1, 2, 3, 4]
            assert [row[1] for row in restored] == [
                {"message": "priced", "cost_usd": "unrelated"},
                {"message": "free"},
                None,
                {"message": "unpriced"},
            ]
            assert [row[2] for row in restored] == [
                Decimal("1.2300456789"),
                Decimal("0"),
                Decimal("0.000000001"),
                None,
            ]
            assert all(row[3] == 42 and row[4] == created_at for row in restored)
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        engine.dispose()
