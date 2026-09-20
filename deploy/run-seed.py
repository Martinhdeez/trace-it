"""Replay cached seed evidence with the real deterministic engine, without provider calls."""

import argparse
import asyncio
import json
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

from seed_cache import fingerprint
from seed_cache import verify as verify_cache


async def run(seed):
    from app.core import events
    from app.core.database import engine, session_factory
    from app.features.decisions import runs as run_history
    from app.features.decisions import service
    from app.features.decisions.model import Decision
    from app.features.ingestion.model import Instance
    from app.features.processes.model import Process
    from app.features.sources.model import Source
    from app.features.traces.breakdown import breakdown
    from app.features.versions import configuration, execution
    from app.features.versions import service as versions
    from app.features.versions.model import Execution
    from sqlalchemy import select

    async def decide(
        session, process, version, expected, names, *, initial_population=False
    ):
        instances = list(
            await session.scalars(
                select(Instance)
                .where(Instance.process_id == process.id)
                .order_by(Instance.id)
            )
        )
        selected = [item for item in instances if item.name in names]
        if len(selected) != len(names) or {item.name for item in selected} != names:
            raise ValueError(f"Seed population mismatch: {process.name}")
        for item in selected:
            reference = expected[item.name]
            if (
                item.status != "PENDING"
                or item.file_hash != reference["hash"]
                or item.symbols != reference["symbols"]
            ):
                raise ValueError(
                    f"Seed reading changed or already decided: {item.name}"
                )
        inputs = await execution.capture(session, process.id)
        if initial_population:
            selected_ids = {item.id for item in selected}
            inputs["instances"] = [
                item for item in inputs["instances"] if item["id"] in selected_ids
            ]
        captured = Execution(
            process_id=process.id, version_id=version.id, inputs=inputs
        )
        session.add(captured)
        await session.flush()
        verdicts = await execution.evaluate(
            session, version.snapshot, inputs, [item.id for item in selected]
        )
        cases = []
        for item in selected:
            verdict = verdicts[item.id]
            reference = expected[item.name]
            if reference.get("expected") and verdict.decision != reference["expected"]:
                raise ValueError(
                    f"{item.name}: got {verdict.decision}, expected {reference['expected']}"
                )
            actual_reasons = {
                part.split()[0].rstrip(":")
                for part in (verdict.reason or "").split(" | ")
                if part.strip()
            }
            expected_reasons = set(reference.get("expected_reasons", []))
            if expected_reasons and actual_reasons != expected_reasons:
                raise ValueError(
                    f"{item.name}: got reasons {sorted(actual_reasons)}, expected "
                    f"{sorted(expected_reasons)}"
                )
            service._append(
                session,
                process.id,
                item,
                verdict,
                version_id=version.id,
                execution_id=captured.id,
            )
            cases.append(
                {
                    "file_id": item.name,
                    "result": verdict.decision,
                    "reason": verdict.reason,
                }
            )
        return (
            captured,
            cases,
            run_history.outcomes(list(verdicts.values()), version.snapshot),
        )

    async def install_saturday_update(session, process, batch):
        for name, rows in batch["sources"].items():
            session.add(
                Source(
                    process_id=process.id,
                    name=name,
                    origin=(
                        f"challenge:{seed['challenge_commit']}:batch{batch['number']}:{name}"
                    ),
                    rows=rows,
                )
            )
        previous = await versions.active(session, process.id)
        version = await versions.publish_snapshot(
            session,
            process,
            deepcopy(previous.snapshot),
            "demo-seed",
            "Adopt Saturday suppliers, orders, ERP and cut-off update",
            {
                "valid": True,
                "source": "challenge_batch_2",
                "snapshot_hash": configuration.digest(previous.snapshot),
            },
        )
        await session.commit()
        return version

    async def reprocess(session, process, version, names):
        instances = list(
            await session.scalars(
                select(Instance)
                .where(Instance.process_id == process.id, Instance.name.in_(names))
                .order_by(Instance.id)
            )
        )
        decisions = list(
            await session.scalars(
                select(Decision)
                .where(Decision.instance_id.in_([i.id for i in instances]))
                .order_by(Decision.id)
            )
        )
        latest = {decision.instance_id: decision for decision in decisions}
        inputs = await execution.capture(session, process.id)
        captured = Execution(
            process_id=process.id, version_id=version.id, inputs=inputs
        )
        session.add(captured)
        await session.flush()
        verdicts = await execution.evaluate(
            session, version.snapshot, inputs, [item.id for item in instances]
        )
        changed = []
        for item in instances:
            verdict = verdicts[item.id]
            previous = latest[item.id]
            if verdict.decision == previous.decision:
                continue
            service._append(
                session,
                process.id,
                item,
                verdict,
                version_id=version.id,
                execution_id=captured.id,
                reprocess=True,
                previous=previous.id,
            )
            changed.append(item.name)
        return (
            captured,
            changed,
            run_history.outcomes(list(verdicts.values()), version.snapshot),
        )

    output = []
    try:
        for baseline in seed["rule_baselines"]:
            name = baseline["process_name"]
            expected = {
                e["name"]: e for e in seed["examples"] if e["process_name"] == name
            }
            async with session_factory() as session:
                process = await session.scalar(
                    select(Process).where(Process.name == name)
                )
                if process is None:
                    raise ValueError(f"Missing seeded process: {name}")
                await versions.lock(session, process.id)
                version = await versions.active(session, process.id)
                invoice_batches = (
                    seed.get("batches", []) if name == "Invoice payment" else []
                )
                phases = [set(expected)]
                if invoice_batches:
                    phases = [set(batch["documents"]) for batch in invoice_batches]
                all_cases = []
                with events.span(
                    "run_process",
                    process_id=process.id,
                    cached_seed=True,
                    provider_calls=0,
                    author="demo-seed",
                ) as span:
                    captured, cases, stats = await decide(
                        session,
                        process,
                        version,
                        expected,
                        phases[0],
                        initial_population=bool(invoice_batches),
                    )
                    await session.commit()
                    span.set(
                        execution_id=captured.id,
                        instances=len(cases),
                        decided=len(cases),
                        **stats,
                    )
                    all_cases.extend(cases)
                if invoice_batches:
                    version = await install_saturday_update(
                        session, process, invoice_batches[1]
                    )
                    with events.span(
                        "run_process",
                        process_id=process.id,
                        cached_seed=True,
                        provider_calls=0,
                        author="demo-seed",
                    ) as span:
                        captured, cases, stats = await decide(
                            session, process, version, expected, phases[1]
                        )
                        await session.commit()
                        span.set(
                            execution_id=captured.id,
                            instances=len(cases),
                            decided=len(cases),
                            **stats,
                        )
                        all_cases.extend(cases)
                    with events.span(
                        "reprocess",
                        process_id=process.id,
                        cached_seed=True,
                        provider_calls=0,
                        author="demo-seed",
                    ) as span:
                        captured, changed, stats = await reprocess(
                            session, process, version, phases[0]
                        )
                        await session.commit()
                        span.set(
                            execution_id=captured.id,
                            instances=len(phases[0]),
                            changed=len(changed),
                            unchanged=len(phases[0]) - len(changed),
                            **stats,
                        )
                # Read the same audit aggregates as the console after actual evaluation.
                # Restored OCR history retains its original timestamps and cost snapshots.
                measured = await breakdown(session, process.id)
                output.append(
                    {
                        "process_id": process.id,
                        "name": name,
                        "count": len(all_cases),
                        "metrics": {
                            "source": "persisted_audit_traces",
                            "scope": "all_history",
                            "planes": [
                                group.model_dump(mode="json")
                                for group in measured.groups
                            ],
                        },
                        "outcomes": dict(Counter(c["result"] for c in all_cases)),
                        "cases": all_cases,
                    }
                )
        return {"provider_calls": 0, "cached_extraction": True, "processes": output}
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["fingerprint", "verify-cache", "run"])
    parser.add_argument("--seed", type=Path)
    parser.add_argument("--app-root", type=Path, default=Path("/srv/app"))
    args = parser.parse_args()
    sys.path.insert(0, str(args.app_root.parent))
    if args.action == "fingerprint":
        print(fingerprint(args.app_root))
        return
    seed = json.loads(args.seed.read_text())
    # Validate before changing data and again before evaluating it.
    import os

    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(
        os.environ["TRACE_DATABASE_URL"].replace(
            "postgresql+psycopg://", "postgresql://"
        ),
        row_factory=dict_row,
    ) as db:
        snapshots = {
            r["name"]: r["snapshot"]
            for r in db.execute(
                "SELECT p.name,v.snapshot FROM processes p JOIN process_versions v ON v.id=p.active_version_id"
            ).fetchall()
        }
    verify_cache(seed, args.app_root, snapshots)
    if args.action == "run":
        print(json.dumps(asyncio.run(run(seed)), ensure_ascii=False))
    else:
        print(json.dumps({"cache_valid": True, "provider_calls": 0}))


if __name__ == "__main__":
    main()
