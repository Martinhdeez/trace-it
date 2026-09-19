"""Run and verify the examples installed by the production demo reset."""

import argparse
import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select

from app.core.database import engine, session_factory
from app.core.events import Event
from app.features.decisions import runs, service
from app.features.decisions.model import Decision
from app.features.ingestion.model import Instance
from app.features.processes.model import Process

EXPECTED_CASES = 12
EXPECTED_PROCESSES = 2
EXPECTED_PER_PROCESS = 6
DEFAULT_REFERENCES = (
    Path("/reference/invoice-expected.jsonl"),
    Path("/processes/hiring-screening/data/expected.jsonl"),
)


@dataclass(frozen=True)
class Reference:
    decision: str
    reasons: frozenset[str] | None
    source: str


def load_references(paths: list[Path]) -> dict[str, Reference]:
    references: dict[str, Reference] = {}
    for path in paths:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            name = row["file_id"]
            why = row.get("why")
            reasons = (
                frozenset(str(item).split(":", 1)[0].split()[0] for item in why)
                if isinstance(why, list)
                else None
            )
            reference = Reference(row["expected"], reasons, f"{path}:{number}")
            if name in references:
                raise ValueError(f"Duplicate outcome reference for {name}")
            references[name] = reference
    return references


async def seeded_cases() -> dict[int, list[tuple[int, str]]]:
    async with session_factory() as session:
        rows = await session.execute(
            select(Process.id, Instance.id, Instance.name)
            .join(Instance, Instance.process_id == Process.id)
            .where(Instance.status == "PENDING")
            .order_by(Process.id, Instance.id)
        )
        grouped: dict[int, list[tuple[int, str]]] = defaultdict(list)
        for process_id, instance_id, name in rows:
            grouped[process_id].append((instance_id, name))
    counts = sorted(len(items) for items in grouped.values())
    if len(grouped) != EXPECTED_PROCESSES or counts != [EXPECTED_PER_PROCESS] * 2:
        raise ValueError(
            f"Demo reset must create two groups of six pending examples; found {counts}"
        )
    return dict(grouped)


async def verify(
    grouped: dict[int, list[tuple[int, str]]], references: dict[str, Reference]
) -> dict:
    expected = {
        instance_id: references[name] for cases in grouped.values() for instance_id, name in cases
    }
    ids = list(expected)
    async with session_factory() as session:
        rows = list(
            await session.execute(
                select(
                    Instance.id,
                    Instance.name,
                    Instance.status,
                    Decision.decision,
                    Decision.reason,
                )
                .join(Decision, Decision.instance_id == Instance.id)
                .where(Instance.id.in_(ids))
                .order_by(Instance.id, Decision.id)
            )
        )
        decision_events = dict(
            await session.execute(
                select(Event.instance_id, func.count())
                .where(Event.instance_id.in_(ids), Event.step == "decision")
                .group_by(Event.instance_id)
            )
        )
        run_traces = dict(
            await session.execute(
                select(Event.process_id, func.count())
                .where(Event.process_id.in_(grouped), Event.step == "run_process")
                .group_by(Event.process_id)
            )
        )
        rule_traces = dict(
            await session.execute(
                select(Event.process_id, func.count())
                .where(Event.process_id.in_(grouped), Event.step == "evaluate_rule")
                .group_by(Event.process_id)
            )
        )

    problems = []
    if len(rows) != EXPECTED_CASES:
        problems.append(f"expected {EXPECTED_CASES} decisions, found {len(rows)}")
    outcomes = defaultdict(int)
    cases = []
    for instance_id, name, status, decision, reason in rows:
        reference = expected[instance_id]
        outcomes[decision] += 1
        cases.append({"file_id": name, "result": decision, "reason": reason})
        if status != "DECIDED":
            problems.append(f"{name}: status is {status}, expected DECIDED")
        if decision != reference.decision:
            problems.append(
                f"{name}: engine returned {decision}, reference expects {reference.decision} "
                f"({reference.source})"
            )
        if reference.reasons is not None:
            actual = frozenset(runs.reason_codes(reason))
            if actual != reference.reasons:
                problems.append(
                    f"{name}: reason codes {sorted(actual)} differ from "
                    f"{sorted(reference.reasons)} ({reference.source})"
                )
        if decision_events.get(instance_id) != 1:
            problems.append(f"{name}: expected one decision trace")
    for process_id in grouped:
        if run_traces.get(process_id) != 1:
            problems.append(f"process {process_id}: expected one run_process trace")
        if not rule_traces.get(process_id):
            problems.append(f"process {process_id}: no evaluate_rule traces")
    if problems:
        raise ValueError("Demo outcome verification failed:\n- " + "\n- ".join(problems))
    return {
        "examples": len(rows),
        "processes": len(grouped),
        "outcomes": dict(sorted(outcomes.items())),
        "cases": cases,
        "decision_traces": sum(decision_events.values()),
        "run_traces": sum(run_traces.values()),
        "rule_traces": sum(rule_traces.values()),
    }


async def run(reference_paths: list[Path]) -> dict:
    references = load_references(reference_paths)
    grouped = await seeded_cases()
    missing = sorted(
        name for cases in grouped.values() for _, name in cases if name not in references
    )
    if missing:
        raise ValueError(f"No outcome reference for seeded examples: {', '.join(missing)}")
    for process_id, cases in grouped.items():
        async with session_factory() as session:
            await service.run(
                session,
                process_id,
                author="demo-reset",
                instance_ids=[instance_id for instance_id, _ in cases],
            )
    return await verify(grouped, references)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", action="append", type=Path)
    args = parser.parse_args()

    async def command() -> dict:
        try:
            return await run(args.reference or list(DEFAULT_REFERENCES))
        finally:
            await engine.dispose()

    print(json.dumps(asyncio.run(command()), sort_keys=True))


if __name__ == "__main__":
    main()
