"""Run history (Q1): a read over the stored executions and the span each one ran in.

An `executions` row is written by every run and every non-dry reprocess; its decisions carry
`execution_id`, and its `run_process`/`reprocess` span carries `execution_id`, the author and
the engine's outcome for every instance it evaluated. Nothing here writes.
"""

from collections import Counter
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.core.events import Event
from app.features.decisions.model import ENGINE, Decision
from app.features.decisions.schemas import RunDecisionOut, RunDetail, RunOut
from app.features.ingestion.model import Instance
from app.features.processes.service import get as get_process
from app.features.versions.model import Execution, ProcessVersion

KINDS = {"run_process": "run", "reprocess": "reprocess"}


def reason_codes(reason: str | None) -> list[str]:
    """`IMPOSSIBLE_DATE 2026-02-31 | SOURCE_UNAVAILABLE: erp` -> the codes, comparable."""
    return [p.split()[0].rstrip(":") for p in (reason or "").split(" | ") if p.strip()]


def outcomes(rows: list, snapshot: dict) -> dict[str, Any]:
    """What the engine concluded for each row (verdicts or decisions): by type, how many a
    person must look at and why. Written into the run's span, so runs compare."""
    human = {t["name"] for t in snapshot["process"]["decision_types"] if t["requires_human"]}
    escalations: Counter[str] = Counter()
    for row in rows:
        if row.decision in human:
            escalations.update(reason_codes(row.reason))
    return {
        "outcomes": Counter(row.decision for row in rows),
        "escalated": sum(row.decision in human for row in rows),
        "escalations": escalations,
        "rules_hash": rows[0].rules_hash if rows else None,
    }


async def _runs(session: AsyncSession, executions: list[Execution]) -> list[RunOut]:
    ids = [e.id for e in executions]
    spans = {
        s.data["execution_id"]: s
        for s in await session.scalars(
            select(Event).where(
                Event.step.in_(KINDS), Event.data["execution_id"].as_integer().in_(ids)
            )
        )
    }
    written = Counter(
        await session.scalars(
            select(Decision.execution_id).where(
                Decision.execution_id.in_(ids), Decision.author == ENGINE
            )
        )
    )
    versions = {
        v.id: v
        for v in await session.scalars(
            select(ProcessVersion).where(ProcessVersion.id.in_({e.version_id for e in executions}))
        )
    }
    out = []
    for execution in executions:
        version = versions[execution.version_id]
        span = spans.get(execution.id)
        data = span.data if span else {}
        if "outcomes" not in data:  # stored before run history: count what it wrote
            rows = list(
                await session.scalars(
                    select(Decision).where(
                        Decision.execution_id == execution.id, Decision.author == ENGINE
                    )
                )
            )
            data = {**data, **outcomes(rows, version.snapshot), "instances": len(rows)}
        out.append(
            RunOut(
                id=execution.id,
                kind=KINDS[span.step] if span else None,
                started_at=span.started_at if span else execution.created_at,
                finished_at=(
                    span.started_at + timedelta(milliseconds=span.duration_ms)
                    if span and span.duration_ms is not None
                    else None
                ),
                author=data.get("author"),
                version_id=version.id,
                version_number=version.number,
                rules_hash=data["rules_hash"],
                instances=data.get("instances", 0),
                decided=written[execution.id],
                by_decision=data["outcomes"],
                escalated=data["escalated"],
                escalation_reasons=data["escalations"],
                down_sources=data.get("down_sources") or {},
                trace_id=span.trace_id if span else None,
            )
        )
    return out


async def list_runs(session: AsyncSession, process_id: int, limit: int) -> list[RunOut]:
    """Newest first."""
    await get_process(session, process_id)
    executions = list(
        await session.scalars(
            select(Execution)
            .where(Execution.process_id == process_id)
            .order_by(Execution.id.desc())
            .limit(limit)
        )
    )
    return await _runs(session, executions)


async def get_run(session: AsyncSession, run_id: int) -> RunDetail:
    execution = await session.get(Execution, run_id)
    if execution is None:
        raise NotFoundError(f"Run {run_id} does not exist")
    [run] = await _runs(session, [execution])
    rows = await session.execute(
        select(Decision, Instance.name)
        .join(Instance, Decision.instance_id == Instance.id)
        .where(Decision.execution_id == run_id, Decision.author == ENGINE)
        .order_by(Decision.instance_id, Decision.id)
    )
    return RunDetail(
        **run.model_dump(),
        decisions=[
            RunDecisionOut(
                decision_id=d.id,
                instance_id=d.instance_id,
                name=name,
                decision=d.decision,
                reason=d.reason,
                created_at=d.created_at,
            )
            for d, name in rows
        ],
    )
