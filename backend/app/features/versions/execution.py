"""Capture a batch once; replay only its saved inputs and published rule code."""

import asyncio
from dataclasses import asdict

from sqlalchemy import select

from app.common.exceptions import ConflictError, NotFoundError
from app.core import events
from app.features.agents import compiler, sandbox
from app.features.decisions.engine import decide
from app.features.decisions.model import ENGINE, Decision, DecisionReview
from app.features.ingestion.model import Instance
from app.features.ingestion.symbols import flatten_symbols, scan
from app.features.sources import service as sources
from app.features.sources.model import Source
from app.features.versions import configuration as config
from app.features.versions.model import Execution, ProcessVersion


async def capture(session, process_id: int) -> dict:
    instances = list(
        await session.scalars(
            select(Instance)
            .where(Instance.process_id == process_id)
            .order_by(Instance.id)
            .execution_options(populate_existing=True)
        )
    )
    decisions = list(
        await session.scalars(
            select(Decision)
            .join(Instance)
            .where(Instance.process_id == process_id)
            .order_by(Decision.id)
        )
    )
    latest = {d.instance_id: d for d in decisions}
    engine = {d.instance_id: d for d in decisions if d.author == ENGINE}
    pending = set(
        await session.scalars(
            select(DecisionReview.decision_id).where(
                DecisionReview.decision_id.in_(
                    [d.id for d in [*latest.values(), *engine.values()]]
                ),
                DecisionReview.requires_human,
            )
        )
    )

    def row(d):
        return {
            "id": d.id,
            "decision": d.decision,
            "author": d.author,
            "pending_review": d.id in pending,
        }

    return {
        "instances": [
            {
                "id": i.id,
                "name": i.name,
                "file_hash": i.file_hash,
                "symbols": i.symbols,
                "decision": row(latest[i.id]) if i.id in latest else None,
                "engine_decision": row(engine[i.id]) if i.id in engine else None,
            }
            for i in instances
        ],
        "source_ids": [s.id for s in await sources.current_loads(session, process_id)],
    }


async def evaluate(
    session,
    snapshot: dict,
    inputs: dict,
    selected_ids: list[int],
    *,
    tables: dict | None = None,
    validation_missing: dict[int, list[str]] | None = None,
):
    if tables is None:
        source_rows = list(
            await session.scalars(select(Source).where(Source.id.in_(inputs["source_ids"])))
        )
        if len(source_rows) != len(inputs["source_ids"]):
            raise ConflictError("An execution source snapshot is missing")
        tables = {s.name: s.rows for s in source_rows}
    selected = set(selected_ids)
    population = [
        (i["id"], {**flatten_symbols(i["symbols"]), "_instance": i["name"]})
        for i in inputs["instances"]
        if i["symbols"] is not None
    ]
    dataset = [
        (i["id"], flatten_symbols(i["symbols"]))
        for i in inputs["instances"]
        if i["id"] in selected and i["symbols"] is not None
    ]
    by_code = {r["code"]: r["id"] for r in snapshot["rules"]}
    rules = config.rules(snapshot)
    # ADR 0028: sources whose pre-run sync failed; a rule reading one does not run.
    unavailable = set(inputs.get("down") or {})
    down = {}
    for rule in rules:
        reads = set(compiler.source_reads(rule.code))
        if hit := sorted(unavailable if compiler.ANY_SOURCE in reads else reads & unavailable):
            down[rule.id] = hit

    def run_dataset(code, dataset, sources, population):
        with events.span("evaluate_rule", rule_id=by_code[code], instances=len(dataset)) as span:
            results = (
                sandbox.run_dataset(
                    code, dataset, sources, population, validation_missing=validation_missing
                )
                if validation_missing
                else sandbox.run_dataset(code, dataset, sources, population)
            )
            span.set(
                fired=sum(isinstance(r, dict) and r.get("fires") is True for r in results),
                errors=sum(
                    isinstance(r, BaseException)
                    and not isinstance(r, sandbox.MissingValidationSymbol)
                    for r in results
                ),
                **(
                    {
                        "not_evaluable": sum(
                            isinstance(r, sandbox.MissingValidationSymbol) for r in results
                        )
                    }
                    if validation_missing
                    else {}
                ),
            )
            return results

    verdicts = await asyncio.to_thread(
        decide,
        rules,
        config.outcomes(snapshot),
        dataset,
        tables,
        population,
        run_dataset,
        {
            i["id"]: unconfirmed
            for i in inputs["instances"]
            if i["id"] in selected and (unconfirmed := scan(i["symbols"])) is not None
        },
        down,
    )
    return dict(zip((key for key, _ in dataset), verdicts, strict=True))


async def replay(session, decision_id: int) -> dict:
    decision = await session.get(Decision, decision_id)
    if decision is None:
        raise NotFoundError("Decision does not exist")
    if decision.author != "engine" or decision.execution_id is None:
        raise ConflictError("Only engine decisions with captured execution inputs can be replayed")
    run = await session.get(Execution, decision.execution_id)
    version = await session.get(ProcessVersion, run.version_id)
    verdict = (await evaluate(session, version.snapshot, run.inputs, [decision.instance_id]))[
        decision.instance_id
    ]
    results = [asdict(r) for r in verdict.results]
    return {
        "decision_id": decision.id,
        "version_id": version.id,
        "execution_id": run.id,
        "matches": verdict.decision == decision.decision
        and results == decision.results
        and verdict.rules_hash == decision.rules_hash
        and (verdict.reason or None) == decision.reason,
        "decision": verdict.decision,
        "reason": verdict.reason,
        "results": results,
    }
