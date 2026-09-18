"""Command line: `uv run python -m app.cli load ../processes/invoice-payment.json`.

`--compile` writes the code of the draft rules with the agents; `--activate` puts into the
process every draft whose code is already validated. A rule that arrives with its code
written needs no compiler, so `--activate` alone is enough to run without any model.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from pydantic import ValidationError

from app.core.database import engine, session_factory
from app.features.processes.definition import Definition, load_definition
from app.features.rules import service as rules


async def load(file: Path, compile_: bool, activate: bool) -> None:
    try:
        data = Definition.model_validate_json(file.read_text(encoding="utf-8"))
    except ValidationError as e:
        sys.exit(f"{file}: invalid definition\n{e}")
    async with session_factory() as session:
        result = await load_definition(session, data, file.parent)
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


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("load", help="Load a process definition (JSON)")
    command.add_argument("file", type=Path)
    command.add_argument("--compile", action="store_true", help="Compile the draft rules")
    command.add_argument(
        "--activate", action="store_true", help="Activate every draft whose code is validated"
    )
    args = parser.parse_args()
    asyncio.run(load(args.file, args.compile, args.activate))


if __name__ == "__main__":
    main()
