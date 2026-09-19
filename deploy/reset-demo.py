"""Offline, backed-up demo reset. Never used by the application or request handlers."""

import argparse
import base64
import hashlib
import json
import os
import shutil
from pathlib import Path

import psycopg
from filelock import FileLock
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

# Configuration, published rules, sources, users and mailbox cursor are intentionally retained.
RUNTIME_TABLES = (
    "mail_activity_reads",
    "mail_activity",
    "mail_attachments",
    "mail_messages",
    "run_operations",
    "alerts",
    "proposals",
    "findings",
    "decision_reviews",
    "decisions",
    "executions",
    "norm_adoptions",
    "norm_validations",
    "norm_proposals",
    "learning_analyses",
    "events",
    "database_api_changes",
    "instances",
)


def connect():
    return psycopg.connect(
        os.environ["TRACE_DATABASE_URL"].replace(
            "postgresql+psycopg://", "postgresql://"
        ),
        row_factory=dict_row,
    )


def export_seed(db, ids):
    rows = db.execute(
        """SELECT i.process_id, p.name AS process_name, i.name, i.symbols,
                  f.hash, f.content, f.text
           FROM instances i JOIN files f ON f.hash=i.file_hash
           JOIN processes p ON p.id=i.process_id WHERE i.id=ANY(%s) ORDER BY i.id""",
        (ids,),
    ).fetchall()
    if len(rows) != len(set(ids)):
        raise ValueError("Some selected examples are missing")
    for row in rows:
        row["content"] = base64.b64encode(row["content"]).decode()
    seed = {"version": 1, "examples": rows}
    validate_seed(seed)
    return seed


def validate_seed(seed):
    if seed.get("version") != 1 or not seed.get("examples"):
        raise ValueError("A versioned, nonempty example fixture is required")
    counts, seen = {}, set()
    for item in seed["examples"]:
        content = base64.b64decode(item["content"], validate=True)
        if hashlib.sha256(content).hexdigest() != item["hash"]:
            raise ValueError("Example PDF checksum mismatch")
        if not content.startswith(b"%PDF-") or not item["symbols"]:
            raise ValueError("Examples must be extracted PDFs")
        key = (item["process_id"], item["hash"])
        if key in seen:
            raise ValueError("Duplicate example content")
        seen.add(key)
        counts[item["process_id"]] = counts.get(item["process_id"], 0) + 1
    if any(count != 6 for count in counts.values()):
        raise ValueError("Exactly six examples per configured process are required")


def reset(db, seed, data_dir):
    validate_seed(seed)
    if data_dir.is_symlink() or not data_dir.is_dir() or data_dir == Path("/"):
        raise ValueError("An existing, dedicated ingestion directory is required")
    # Quarantine permits filesystem rollback if any SQL statement fails. Existing quarantine
    # means a previous reset was interrupted: fail closed and recover from its backup first.
    trash = data_dir / ".demo-reset-trash"
    if trash.exists():
        raise ValueError(
            "Interrupted reset quarantine exists; operator recovery required"
        )
    moved = []
    with FileLock(data_dir / "server.lock", timeout=0):
        try:
            with db.transaction():
                db.execute("SET LOCAL lock_timeout='5s'")
                # A concurrent app writer is a protocol error; deployment stops all writers.
                for table in (
                    *RUNTIME_TABLES,
                    "files",
                    "mail_accounts",
                    "sources",
                    "processes",
                ):
                    db.execute(
                        sql.SQL("LOCK TABLE {} IN ACCESS EXCLUSIVE MODE NOWAIT").format(
                            sql.Identifier(table)
                        )
                    )
                for item in seed["examples"]:
                    process = db.execute(
                        "SELECT name FROM processes WHERE id=%s", (item["process_id"],)
                    ).fetchone()
                    if not process or process["name"] != item["process_name"]:
                        raise ValueError(
                            "Example fixture does not match the installed processes"
                        )
                before = db.execute("SELECT count(*) AS n FROM instances").fetchone()[
                    "n"
                ]
                for table in RUNTIME_TABLES:
                    # No CASCADE or sequence reset: unknown FKs fail safely and IDs stay monotonic.
                    db.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(table)))
                # Keep original reference workbooks and every file explicitly used by a source.
                db.execute("""DELETE FROM files WHERE hash NOT IN (SELECT origin FROM sources)
                              AND name NOT ILIKE '%%.xlsx' AND name NOT ILIKE '%%.xls'""")
                for item in seed["examples"]:
                    db.execute(
                        """INSERT INTO files (hash,name,content,text) VALUES (%s,%s,%s,%s)
                           ON CONFLICT (hash) DO NOTHING""",
                        (
                            item["hash"],
                            item["name"],
                            base64.b64decode(item["content"]),
                            item["text"],
                        ),
                    )
                    db.execute(
                        """INSERT INTO instances (process_id,file_hash,name,status,symbols)
                           VALUES (%s,%s,%s,'PENDING',%s)""",
                        (
                            item["process_id"],
                            item["hash"],
                            item["name"],
                            Jsonb(item["symbols"]),
                        ),
                    )
                # Never reset initial_uid/next_uid, account identity, credentials or halt state.
                db.execute(
                    "UPDATE mail_accounts SET heartbeat_at=NULL,worker_phase=NULL"
                )
                trash.mkdir()
                for child in data_dir.iterdir():
                    if child.name not in {"server.lock", trash.name}:
                        child.rename(trash / child.name)
                        moved.append(child.name)
        except BaseException:
            for name in reversed(moved):
                (trash / name).rename(data_dir / name)
            if trash.exists():
                trash.rmdir()
            raise
        # Originals for the examples live in PostgreSQL; extraction caches are expendable.
        shutil.rmtree(trash)
    return {
        "previous_instances": before,
        "examples": len(seed["examples"]),
        "mail_cursor_preserved": True,
        "sources_preserved": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["export", "reset"])
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--instance-ids", type=int, nargs="+")
    parser.add_argument("--data-dir", type=Path, default=Path("/srv/.data"))
    parser.add_argument("--confirm-demo-reset", action="store_true")
    args = parser.parse_args()
    with connect() as db:
        if args.action == "export":
            if not args.instance_ids:
                parser.error("Export requires explicit example IDs")
            # Exclusive creation: never silently replace the reviewed examples.
            with args.seed.open("x") as output:
                json.dump(export_seed(db, args.instance_ids), output)
        else:
            if not args.confirm_demo_reset:
                parser.error(
                    "Reset requires --confirm-demo-reset after a verified backup"
                )
            print(
                json.dumps(reset(db, json.loads(args.seed.read_text()), args.data_dir))
            )


if __name__ == "__main__":
    main()
