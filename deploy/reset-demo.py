"""Offline, backed-up demo reset. Never used by the application or request handlers."""

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import uuid
from copy import deepcopy
from pathlib import Path

import psycopg
from filelock import FileLock
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

# Configuration, sources, users and mailbox cursor are retained; rules return to their baseline.
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


def capture_baselines(db, invoice_pack, norm_workbook):
    """Capture reviewed initial rules, excluding later rules even from the first invoice version."""
    from openpyxl import load_workbook

    pack = json.loads(invoice_pack.read_text())
    manifest = json.loads(invoice_pack.with_name("manifest.json").read_text())
    workbook = load_workbook(norm_workbook, read_only=True, data_only=True)
    try:
        original_norms = [
            re.sub(r"^\d+\.\s*", "", str(row[0]))
            for row in workbook["Norma_Pagos_v3"].values
            if row[0] and re.match(r"^\d+\.", str(row[0]))
        ]
    finally:
        workbook.close()
    if original_norms != [n["text"] for n in manifest["norm_rules"]]:
        raise ValueError("Frozen norms do not match the official workbook")
    if len(pack["rules"]) != len(manifest["rules"]):
        raise ValueError("Incomplete frozen rule manifest")
    baselines = []
    for process in db.execute("SELECT id,name FROM processes ORDER BY id").fetchall():
        first = db.execute(
            "SELECT snapshot FROM process_versions WHERE process_id=%s ORDER BY number LIMIT 1",
            (process["id"],),
        ).fetchone()
        if not first:
            raise ValueError("Every demo process needs an approved initial version")
        snapshot = first["snapshot"]
        if process["name"] == pack["use_case"]:
            rules = []
            for item, artifact in zip(pack["rules"], manifest["rules"], strict=True):
                code = (invoice_pack.parent / item["code"]).read_text()
                if (
                    item["text"] != artifact["text"]
                    or hashlib.sha256(f"{item['text']}\0{code}".encode()).hexdigest()
                    != artifact["hash"]
                ):
                    raise ValueError("Frozen rule checksum mismatch")
                rules.append(
                    {
                        "text": item["text"],
                        "summary": item.get("summary"),
                        "type": item["type"],
                        "decision": item["decision"],
                        "code": code,
                        "hash": hashlib.sha256(
                            f"{item['text']}\0{code}".encode()
                        ).hexdigest(),
                        "tests": artifact["test_rows"],
                        "report": artifact["report"],
                        "status": "active",
                        "norm_rule_id": artifact["norm_rule"],
                    }
                )
            norms = [{"id": n["number"], **n} for n in manifest["norm_rules"]]
            guidance = {
                f"norm:{n['number']}": " ".join(n["policies"])
                for n in norms
                if n["policies"]
            }
        else:
            rules = deepcopy(snapshot["rules"])
            norm_ids = [r["norm_rule_id"] for r in rules if r.get("norm_rule_id")]
            norms = db.execute(
                "SELECT id,number,text,policies FROM norm_rules WHERE id=ANY(%s)",
                (norm_ids,),
            ).fetchall()
            guidance = deepcopy(snapshot.get("guidance", {}))
        baselines.append(
            {
                "process_id": process["id"],
                "process_name": process["name"],
                "rules": rules,
                "norm_rules": norms,
                "guidance": guidance,
            }
        )
    return baselines


def restore_rules(db, baselines):
    """Rebuild authoring tables AND runtime snapshots; clearing only rules is insufficient."""
    counts = {}
    for baseline in baselines:
        pid = baseline["process_id"]
        row = db.execute(
            """SELECT p.name,v.snapshot FROM processes p
               JOIN process_versions v ON v.id=p.active_version_id WHERE p.id=%s""",
            (pid,),
        ).fetchone()
        if not row or row["name"] != baseline["process_name"]:
            raise ValueError("Rule baseline does not match the installed process")
        snapshot = deepcopy(row["snapshot"])
        db.execute("DELETE FROM process_drafts WHERE process_id=%s", (pid,))
        db.execute("UPDATE processes SET active_version_id=NULL WHERE id=%s", (pid,))
        db.execute("DELETE FROM process_versions WHERE process_id=%s", (pid,))
        db.execute("DELETE FROM rules WHERE process_id=%s", (pid,))
        db.execute("DELETE FROM norm_rules WHERE process_id=%s", (pid,))
        norms = {}
        for norm in baseline["norm_rules"]:
            norms[norm["id"]] = db.execute(
                """INSERT INTO norm_rules (process_id,number,text,policies)
                   VALUES (%s,%s,%s,%s) RETURNING id""",
                (pid, norm["number"], norm["text"], Jsonb(norm["policies"])),
            ).fetchone()["id"]
        snapshot["rules"] = []
        snapshot["guidance"] = deepcopy(baseline["guidance"])
        snapshot["process"].pop("active_version_id", None)
        for original in baseline["rules"]:
            rule = {
                key: deepcopy(original.get(key))
                for key in (
                    "norm_rule_id",
                    "text",
                    "type",
                    "decision",
                    "code",
                    "tests",
                    "hash",
                    "report",
                    "status",
                )
            }
            rule["norm_rule_id"] = norms.get(rule["norm_rule_id"])
            ident = db.execute(
                """INSERT INTO rules (process_id,norm_rule_id,text,summary,type,decision,
                   code,tests,hash,report,status,activated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now()) RETURNING id""",
                (
                    pid,
                    rule["norm_rule_id"],
                    rule["text"],
                    original.get("summary"),
                    rule["type"],
                    rule["decision"],
                    rule["code"],
                    Jsonb(rule["tests"]),
                    rule["hash"],
                    Jsonb(rule["report"]),
                    rule["status"],
                ),
            ).fetchone()["id"]
            snapshot["rules"].append({"id": ident, **rule})
        digest = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, default=str).encode()
        ).hexdigest()
        version = db.execute(
            """INSERT INTO process_versions (process_id,number,snapshot,validation,
               content_hash,author,reason) VALUES (%s,1,%s,%s,%s,'demo-reset',
               'Restore reviewed initial demo rules') RETURNING id""",
            (
                pid,
                Jsonb(snapshot),
                Jsonb({"valid": True, "source": "reviewed_demo_baseline"}),
                digest,
            ),
        ).fetchone()["id"]
        db.execute(
            "UPDATE processes SET active_version_id=%s WHERE id=%s", (version, pid)
        )
        counts[baseline["process_name"]] = len(snapshot["rules"])
    return counts


def export_seed(db, ids, invoice_pack, norm_workbook):
    rows = db.execute(
        """SELECT i.process_id, p.name AS process_name, i.name, i.symbols,
                  f.hash, f.content, f.text, reading.data AS evidence
           FROM instances i JOIN files f ON f.hash=i.file_hash
           JOIN processes p ON p.id=i.process_id
           LEFT JOIN LATERAL (
               SELECT data FROM events WHERE instance_id=i.id
               AND step IN ('ingest_document','extract_document')
               AND (step='extract_document' OR COALESCE((data->>'created')::boolean,true))
               ORDER BY id DESC LIMIT 1
           ) reading ON true
           WHERE i.id=ANY(%s) ORDER BY i.id""",
        (ids,),
    ).fetchall()
    if len(rows) != len(set(ids)):
        raise ValueError("Some selected examples are missing")
    for row in rows:
        row["content"] = base64.b64encode(row["content"]).decode()
    seed = {
        "version": 3,
        "examples": rows,
        "rule_baselines": capture_baselines(db, invoice_pack, norm_workbook),
    }
    validate_seed(seed)
    return seed


def validate_seed(seed):
    if seed.get("version") != 3 or not seed.get("examples"):
        raise ValueError("A versioned, nonempty example fixture is required")
    baselines = seed.get("rule_baselines", [])
    if not baselines or len({b["process_id"] for b in baselines}) != len(baselines):
        raise ValueError("Unique reviewed rule baselines are required")
    for baseline in baselines:
        if not baseline["rules"]:
            raise ValueError("Empty initial rule set")
        norms = {n["id"] for n in baseline["norm_rules"]}
        for rule in baseline["rules"]:
            if (
                rule.get("norm_rule_id") is not None
                and rule["norm_rule_id"] not in norms
            ):
                raise ValueError("Initial rule refers to a missing norm")
            if (
                rule.get("code")
                and hashlib.sha256(
                    f"{rule['text']}\0{rule['code']}".encode()
                ).hexdigest()
                != rule["hash"]
            ):
                raise ValueError("Initial rule checksum mismatch")
    counts, seen = {}, set()
    for item in seed["examples"]:
        content = base64.b64decode(item["content"], validate=True)
        if hashlib.sha256(content).hexdigest() != item["hash"]:
            raise ValueError("Example PDF checksum mismatch")
        if not content.startswith(b"%PDF-") or not item["symbols"]:
            raise ValueError("Examples must be extracted PDFs")
        if not isinstance(item.get("evidence", {}).get("extraction"), dict):
            raise TypeError("Examples require their original extraction evidence")
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
                    "rules",
                    "norm_rules",
                    "process_versions",
                    "process_drafts",
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
                rule_counts = restore_rules(db, seed["rule_baselines"])
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
                    instance = db.execute(
                        """INSERT INTO instances (process_id,file_hash,name,status,symbols)
                           VALUES (%s,%s,%s,'PENDING',%s) RETURNING id""",
                        (
                            item["process_id"],
                            item["hash"],
                            item["name"],
                            Jsonb(item["symbols"]),
                        ),
                    ).fetchone()["id"]
                    # Reuse the sample's persisted reading, explicitly identified as a seed.
                    # It is not a new OCR/provider call; runtime traces from tests are gone.
                    evidence = {**item["evidence"], "created": True, "demo_seed": True}
                    db.execute(
                        """INSERT INTO events (trace_id,span_id,step,status,started_at,
                           duration_ms,data,instance_id,process_id)
                           VALUES (%s,%s,'ingest_document','ok',now(),0,%s,%s,%s)""",
                        (
                            uuid.uuid4().hex,
                            uuid.uuid4().hex[:16],
                            Jsonb(evidence),
                            instance,
                            item["process_id"],
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
        "initial_rules": rule_counts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["export", "baseline", "reset"])
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument(
        "--invoice-pack",
        type=Path,
        default=Path(
            "/processes/invoice-payment/frozen/2026-09-19/invoice-payment.json"
        ),
    )
    parser.add_argument("--norm-workbook", type=Path)
    parser.add_argument("--instance-ids", type=int, nargs="+")
    parser.add_argument("--data-dir", type=Path, default=Path("/srv/.data"))
    parser.add_argument("--confirm-demo-reset", action="store_true")
    args = parser.parse_args()
    if args.action in {"export", "baseline"} and not args.norm_workbook:
        parser.error("Capturing rules requires the official --norm-workbook")
    with connect() as db:
        if args.action == "export":
            if not args.instance_ids:
                parser.error("Export requires explicit example IDs")
            # Exclusive creation: never silently replace the reviewed examples.
            with args.seed.open("x") as output:
                json.dump(
                    export_seed(
                        db, args.instance_ids, args.invoice_pack, args.norm_workbook
                    ),
                    output,
                )
        elif args.action == "baseline":
            seed = json.loads(args.seed.read_text())
            if "rule_baselines" in seed:
                parser.error(
                    "Reviewed baselines already exist; refusing to overwrite them"
                )
            seed.update(
                version=3,
                rule_baselines=capture_baselines(
                    db, args.invoice_pack, args.norm_workbook
                ),
            )
            validate_seed(seed)
            staged = args.seed.with_suffix(".json.next")
            staged.write_text(json.dumps(seed))
            staged.chmod(args.seed.stat().st_mode & 0o777)
            staged.replace(args.seed)
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
