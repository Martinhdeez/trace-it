"""Exercise the destructive reset against an isolated restored PostgreSQL database."""

import copy
import importlib.util
import json
import os
from pathlib import Path

import psycopg
import pytest
from filelock import FileLock, Timeout
from psycopg.rows import dict_row

spec = importlib.util.spec_from_file_location(
    "reset_demo", Path(__file__).with_name("reset-demo.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_restored_database_reset_and_failure_recovery(tmp_path):
    url = os.environ.get("DEMO_RESET_TEST_DATABASE_URL")
    if not url:
        pytest.skip("requires an isolated restored demo database")
    assert url.rsplit("/", 1)[-1] == "trace_demo_reset_test"
    seed = json.loads(Path(os.environ["DEMO_RESET_TEST_SEED"]).read_text())
    data = tmp_path / "data"
    data.mkdir()
    (data / "objects").mkdir()
    (data / "objects" / "sentinel.pdf").write_bytes(b"keep-on-failure")
    (data / "tracepay.sqlite3").write_bytes(b"old extraction cache")
    with psycopg.connect(url, row_factory=dict_row, autocommit=True) as db:

        def preserved():
            return {
                table: db.execute(f'SELECT * FROM "{table}" ORDER BY 1').fetchall()
                for table in (
                    "users",
                    "sources",
                    "agent_configs",
                    "symbols",
                )
            }

        def assert_initial_rules():
            for baseline in seed["rule_baselines"]:
                pid = baseline["process_id"]
                if baseline["process_name"] == "Invoice payment":
                    assert len(baseline["norm_rules"]) == 6
                    assert len(baseline["rules"]) == 12
                    assert not any(
                        "end with the character" in r["text"] for r in baseline["rules"]
                    )
                rows = db.execute(
                    "SELECT * FROM rules WHERE process_id=%s ORDER BY id", (pid,)
                ).fetchall()
                assert len(rows) == len(baseline["rules"])
                assert [(r["text"], r["code"], r["hash"]) for r in rows] == [
                    (r["text"], r["code"], r["hash"]) for r in baseline["rules"]
                ]
                version = db.execute(
                    "SELECT v.snapshot FROM processes p JOIN process_versions v ON v.id=p.active_version_id WHERE p.id=%s",
                    (pid,),
                ).fetchone()["snapshot"]
                assert [(r["id"], r["hash"]) for r in version["rules"]] == [
                    (r["id"], r["hash"]) for r in rows
                ]
                assert version["execution"] == execution[pid]
                assert (
                    db.execute(
                        "SELECT count(*) AS n FROM process_versions WHERE process_id=%s",
                        (pid,),
                    ).fetchone()["n"]
                    == 1
                )
                assert (
                    db.execute(
                        "SELECT count(*) AS n FROM process_drafts WHERE process_id=%s",
                        (pid,),
                    ).fetchone()["n"]
                    == 0
                )

        execution = {
            r["process_id"]: r["snapshot"]["execution"]
            for r in db.execute(
                "SELECT v.process_id,v.snapshot FROM process_versions v JOIN processes p ON p.active_version_id=v.id"
            ).fetchall()
        }
        original = preserved()
        cursor = db.execute(
            "SELECT id,initial_uid,next_uid,uidvalidity,state,token_hash FROM mail_accounts"
        ).fetchall()
        original_ids = [
            r["id"] for r in db.execute("SELECT id FROM instances").fetchall()
        ]
        bad = copy.deepcopy(seed)
        bad["examples"][0]["hash"] = "0" * 64
        with pytest.raises(ValueError, match="checksum"):
            module.reset(db, bad, data)
        with FileLock(data / "server.lock"), pytest.raises(Timeout):
            module.reset(db, seed, data)
        # New schema dependencies must stop the reset without deleting data or caches.
        db.execute(
            "CREATE TABLE reset_guard (instance_id integer REFERENCES instances(id))"
        )
        db.execute("INSERT INTO reset_guard VALUES (%s)", (original_ids[0],))
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            module.reset(db, seed, data)
        db.execute("DROP TABLE reset_guard")
        assert db.execute("SELECT count(*) AS n FROM instances").fetchone()["n"] == len(
            original_ids
        )
        assert (data / "objects" / "sentinel.pdf").read_bytes() == b"keep-on-failure"
        # A filesystem failure after SQL deletes must roll back PostgreSQL as well.
        from unittest.mock import patch

        real_rename = Path.rename

        def failing_rename(path, target):
            if path.name == "tracepay.sqlite3":
                raise OSError("injected storage failure")
            return real_rename(path, target)

        with (
            patch.object(Path, "rename", failing_rename),
            pytest.raises(OSError, match="injected"),
        ):
            module.reset(db, seed, data)
        assert db.execute("SELECT count(*) AS n FROM instances").fetchone()["n"] == len(
            original_ids
        )
        assert (data / "objects" / "sentinel.pdf").exists()
        first = module.reset(db, seed, data)
        assert first["examples"] == 12
        assert_initial_rules()
        assert preserved() == original
        assert (
            db.execute(
                "SELECT id,initial_uid,next_uid,uidvalidity,state,token_hash FROM mail_accounts"
            ).fetchall()
            == cursor
        )
        assert db.execute("SELECT DISTINCT status FROM instances").fetchall() == [
            {"status": "PENDING"}
        ]
        for table in module.RUNTIME_TABLES:
            if table not in {"instances", "events"}:
                assert (
                    db.execute(f'SELECT count(*) AS n FROM "{table}"').fetchone()["n"]
                    == 0
                )
        assert (
            db.execute(
                "SELECT count(*) AS n FROM events WHERE data->>'demo_seed'='true' AND data->'extraction' IS NOT NULL"
            ).fetchone()["n"]
            == 12
        )
        assert [p.name for p in data.iterdir()] == ["server.lock"]
        assert (
            db.execute(
                "SELECT count(*) AS n FROM files WHERE name ILIKE '%.xlsx'"
            ).fetchone()["n"]
            == 2
        )
        first_ids = [r["id"] for r in db.execute("SELECT id FROM instances").fetchall()]
        assert min(first_ids) > max(original_ids)
        # User-added and edited rules, including published snapshots and drafts, must disappear.
        db.execute(
            "UPDATE rules SET text='changed in rehearsal' WHERE id=(SELECT min(id) FROM rules)"
        )
        db.execute(
            "INSERT INTO rules (process_id,text,type,decision,status) VALUES (1,'extra rule','requirement','ESCALAR','draft')"
        )
        db.execute(
            "INSERT INTO process_drafts (process_id,base_version_id,revision,snapshot,author) SELECT p.id,p.active_version_id,1,v.snapshot,'test' FROM processes p JOIN process_versions v ON v.id=p.active_version_id WHERE p.id=1"
        )
        module.reset(db, seed, data)
        assert_initial_rules()
        assert preserved() == original
        assert db.execute("SELECT min(id) AS n FROM instances").fetchone()["n"] > max(
            first_ids
        )
        assert db.execute("SELECT count(*) AS n FROM instances").fetchone()["n"] == 12
        assert (
            db.execute(
                "SELECT count(*) AS n FROM files WHERE name='2026-01-11_P007.pdf'"
            ).fetchone()["n"]
            == 0
        )
