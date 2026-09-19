"""Command line: `uv run python -m app.cli load ../processes/invoice-payment.json`.

`--compile` writes the code of the draft rules with the agents; `--activate` puts into the
process every draft whose code is already validated. A rule that arrives with its code
written needs no compiler, so `--activate` alone is enough to run without any model.

A pack with `<pack>/use-case.json` loads its use case first: the domain description and
how its agents work (models, guidance, limits, examples).

`sources sync <pack.json>` downloads an HTTP source (the ERP) into a new snapshot.

`export <pack.json> --files <dir> --output <file>` writes the outcomes of the instances named
like the PDFs of a folder (one delivery batch) and checks the file; `check-outcomes <file>
--files <dir>` only checks it (`docs/runbook-batch2.md`).
"""

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select

from app.common.exceptions import ConflictError
from app.core.database import engine, session_factory
from app.features.decisions import outcomes_file
from app.features.decisions import service as decisions
from app.features.processes.definition import Definition, load_pack
from app.features.processes.model import Process
from app.features.rules import service as rules
from app.features.sources import service as sources
from app.features.use_cases import service as use_cases


async def load(file: Path, compile_: bool, activate: bool) -> None:
    try:
        Definition.model_validate_json(file.read_text(encoding="utf-8"))
    except ValidationError as e:
        sys.exit(f"{file}: invalid definition\n{e}")
    async with session_factory() as session:
        result = await load_pack(session, file)
        configs = await use_cases.active(session, result.process.use_case_id)
        print(f"Use case {result.process.use_case_id}: agents {sorted(configs)} configured")
        p = result.process
        print(
            f"Process {p.name!r} (id {p.id}): {len(p.decision_types)} decision types, "
            f"{len(p.symbols)} symbols, {result.new_rules} new rules, "
            f"{result.new_users} new users"
        )
        if compile_:
            for rule in await rules.list_all(session, p.id, "draft"):
                if (rule.report or {}).get("valid"):
                    continue
                try:
                    r = await rules.compile_rule(session, rule.id)
                    status = "valid" if r.report["valid"] else "with discrepancies"
                except Exception as e:  # one failing rule must not stop the others
                    await session.rollback()
                    status = f"error: {str(e).splitlines()[0][:150]}"
                print(f"  rule {rule.id} ({rule.decision}): {status} · {rule.text[:70]}")
        if activate:
            activated = 0
            for rule in await rules.list_all(session, p.id, "draft"):
                if not (rule.report or {}).get("valid"):
                    print(f"  rule {rule.id}: no validated code, still a draft")
                    continue
                try:
                    await rules.activate(session, rule.id)
                    activated += 1
                except Exception as e:  # a rule that contradicts a person must not stop the rest
                    await session.rollback()
                    print(f"  rule {rule.id}: {str(e).splitlines()[0][:150]}")
            active = await rules.list_all(session, p.id, "active")
            print(f"  {activated} rules activated, {len(active)} active in the process")
    await engine.dispose()


async def sync_source(file: Path, name: str) -> None:
    async with session_factory() as session:
        process = await process_of(session, file)
        config = sources.load_config(sources.pack_sources_file(file), name)
        try:
            result = await sources.sync(session, process.id, name, config)
        except sources.SourceUnavailableError as e:
            sys.exit(e.message)
        s, d = result.stats, result.diff
        print(
            f"Source {name!r} snapshot {result.source_id}: {result.rows} rows in {s['pages']} "
            f"pages, {s['duration_ms'] / 1000:.1f} s; {s['requests']} requests, "
            f"{s['retries']} retries, {s['logins']} logins, {s['rate_limited']} rate limited, "
            f"errors {s['transient_errors']}, {s['invalid_values']} unconvertible values"
        )
        print(f"  origin {result.origin}, status {s['status']}")
        print(f"  vs snapshot {d.previous_id}: {d.summary()}")
        for key, fields in d.changed.items():
            print(f"    changed {key}: {fields}")
        if d.previous_id is not None:
            for key in d.added:
                print(f"    added {key}")
            for key in d.removed:
                print(f"    removed {key}")
    await engine.dispose()


async def process_of(session, file: Path) -> Process:
    process_name = json.loads(file.read_text(encoding="utf-8"))["name"]
    process = await session.scalar(select(Process).where(Process.name == process_name))
    if process is None:
        sys.exit(f"Process {process_name!r} is not loaded: run `python -m app.cli load {file}`")
    return process


def check_outcomes(output: Path, files: Path) -> None:
    text = output.read_text(encoding="utf-8")
    batch = outcomes_file.batch_files(files)
    found = outcomes_file.problems(text, batch)
    print(f"{output}: {len(text.splitlines())} lines for {len(batch)} PDFs in {files}")
    if found:
        sys.exit("NOT deliverable:\n  " + "\n  ".join(found[:50]))
    results = Counter(json.loads(line)["result"] for line in text.splitlines())
    print(f"OK: one line per file, valid results {dict(sorted(results.items()))}")


async def export(file: Path, files: Path, output: Path) -> None:
    async with session_factory() as session:
        process = await process_of(session, file)
        try:
            body, duplicates = await decisions.export(
                session, process.id, outcomes_file.batch_files(files)
            )
        except ConflictError as e:
            sys.exit(f"export refused: {e.message}")
    await engine.dispose()
    if duplicates:
        print(f"WARNING: names shared by several instances, latest exported: {duplicates}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body + "\n" if body else "", encoding="utf-8")
    check_outcomes(output, files)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("load", help="Load a process definition (JSON)")
    command.add_argument("file", type=Path)
    command.add_argument("--compile", action="store_true", help="Compile the draft rules")
    command.add_argument(
        "--activate", action="store_true", help="Activate every draft whose code is validated"
    )
    command = commands.add_parser("sources", help="Snapshots of the sources of truth")
    actions = command.add_subparsers(dest="action", required=True)
    action = actions.add_parser("sync", help="Download an HTTP source into a new snapshot")
    action.add_argument("file", type=Path, help="The process pack, e.g. processes/x.json")
    action.add_argument("--source", default="erp")
    command = commands.add_parser("export", help="Outcomes of one batch (a folder of PDFs)")
    command.add_argument("file", type=Path, help="The process pack, e.g. processes/x.json")
    command.add_argument("--files", type=Path, required=True, help="Folder with the batch's PDFs")
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("check-outcomes", help="Check an outcomes JSONL for a batch")
    command.add_argument("output", type=Path)
    command.add_argument("--files", type=Path, required=True, help="Folder with the batch's PDFs")
    args = parser.parse_args()
    if args.command == "load":
        asyncio.run(load(args.file, args.compile, args.activate))
    elif args.command == "sources":
        asyncio.run(sync_source(args.file, args.source))
    elif args.command == "export":
        asyncio.run(export(args.file, args.files, args.output))
    else:
        check_outcomes(args.output, args.files)


if __name__ == "__main__":
    main()
