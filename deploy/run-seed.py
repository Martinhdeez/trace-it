"""Replay cached seed evidence with the real deterministic engine, without provider calls."""

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

from seed_cache import fingerprint
from seed_cache import verify as verify_cache


async def run(seed):
    from app.core import events
    from app.core.database import engine, session_factory
    from app.features.decisions import service
    from app.features.decisions.model import Decision
    from app.features.ingestion.model import Instance
    from app.features.processes.model import Process
    from app.features.versions import execution
    from app.features.versions import service as versions
    from app.features.versions.model import Execution
    from sqlalchemy import select

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
                with events.span(
                    "run_process",
                    process_id=process.id,
                    cached_seed=True,
                    provider_calls=0,
                    author="demo-seed",
                ) as span:
                    await versions.lock(session, process.id)
                    version = await versions.active(session, process.id)
                    instances = list(
                        await session.scalars(
                            select(Instance).where(Instance.process_id == process.id)
                        )
                    )
                    if len(instances) != len(expected) or {
                        i.name for i in instances
                    } != set(expected):
                        raise ValueError(f"Seed population mismatch: {name}")
                    for item in instances:
                        if (
                            item.status != "PENDING"
                            or item.file_hash != expected[item.name]["hash"]
                            or item.symbols != expected[item.name]["symbols"]
                        ):
                            raise ValueError(
                                f"Seed reading changed or already decided: {item.name}"
                            )
                    # Deliberately bypass live source sync and the optional LLM reviewer.
                    # capture/evaluate/_append are the same routines used by normal decisions.
                    inputs = await execution.capture(session, process.id)
                    captured = Execution(
                        process_id=process.id, version_id=version.id, inputs=inputs
                    )
                    session.add(captured)
                    await session.flush()
                    span.set(execution_id=captured.id)
                    verdicts = await execution.evaluate(
                        session, version.snapshot, inputs, [i.id for i in instances]
                    )
                    cases = []
                    for item in instances:
                        verdict = verdicts[item.id]
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
                    await session.commit()
                    decisions = list(
                        await session.scalars(
                            select(Decision).where(Decision.execution_id == captured.id)
                        )
                    )
                    if len(decisions) != len(expected):
                        raise ValueError("Incomplete seed decisions")
                    span.set(
                        decided=len(cases),
                        by_decision=dict(Counter(c["result"] for c in cases)),
                    )
                    output.append(
                        {
                            "process_id": process.id,
                            "name": name,
                            "count": len(cases),
                            "outcomes": dict(Counter(c["result"] for c in cases)),
                            "cases": cases,
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
