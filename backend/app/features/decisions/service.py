import asyncio
import json
import logging
from collections import Counter
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.core import events
from app.core.events import Event
from app.features.agents import sandbox
from app.features.decisions.engine import Outcomes, Verdict, decide
from app.features.decisions.model import ENGINE, Decision, Finding
from app.features.decisions.schemas import (
    DecisionOut,
    EventOut,
    FindingOut,
    InstanceDetail,
    InstanceOut,
    ProcessSummary,
    ResolveIn,
    RuleSummary,
    RunSummary,
    SourceSummary,
)
from app.features.ingestion.model import Instance
from app.features.ingestion.symbols import flatten_symbols
from app.features.processes.model import DecisionType, Symbol
from app.features.processes.service import get as get_process
from app.features.rules.model import ENFORCED, Rule
from app.features.sources import service as sources
from app.features.users.model import User

log = logging.getLogger(__name__)


async def _instance(session: AsyncSession, instance_id: int) -> Instance:
    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise NotFoundError(f"Instance {instance_id} does not exist")
    return instance


async def outcomes(session: AsyncSession, process_id: int) -> Outcomes:
    """The loader guarantees one default and at least one type that requires a human; the
    highest-priority one of those is where the engine sends what it cannot decide, including
    an instance missing a required symbol."""
    types = list(
        await session.scalars(select(DecisionType).where(DecisionType.process_id == process_id))
    )
    required = await session.scalars(
        select(Symbol.name)
        .where(Symbol.process_id == process_id, Symbol.required)
        .order_by(Symbol.name)
    )
    default = next(t.name for t in types if t.is_default)
    escalate = max((t for t in types if t.requires_human), key=lambda t: t.priority).name
    return Outcomes({t.name: t.priority for t in types}, default, escalate, tuple(required))


async def human_types(session: AsyncSession, process_id: int) -> list[str]:
    types = await session.scalars(
        select(DecisionType.name).where(
            DecisionType.process_id == process_id, DecisionType.requires_human
        )
    )
    return list(types)


async def current_sources(session: AsyncSession, process_id: int) -> dict[str, list[dict]]:
    """The latest load of each source of truth. Every load is kept; only the last one is used."""
    return {load.name: load.rows for load in await sources.current_loads(session, process_id)}


async def instances_of(session: AsyncSession, process_id: int) -> list[Instance]:
    return list(
        await session.scalars(
            select(Instance).where(Instance.process_id == process_id).order_by(Instance.id)
        )
    )


async def latest_decisions(session: AsyncSession, instances: list[Instance]) -> dict[int, Decision]:
    """An instance's current decision is its latest row (the history only ever grows)."""
    if not instances:
        return {}
    rows = await session.scalars(
        select(Decision)
        .where(Decision.instance_id.in_([i.id for i in instances]))
        .order_by(Decision.id)
    )
    return {row.instance_id: row for row in rows}


async def active_rules(session: AsyncSession, process_id: int) -> list[Rule]:
    return list(
        await session.scalars(
            select(Rule)
            .where(Rule.process_id == process_id, Rule.status.in_(ENFORCED))
            .order_by(Rule.id)
        )
    )


async def decide_all(
    session: AsyncSession, process_id: int, rules: list[Rule], selected: list[Instance]
) -> list[Verdict]:
    """`selected` instances under `rules`, with the current sources and the whole population
    of the process as `others`. Each population entry carries `_instance`, its name, so a
    rule can name the duplicate it found; the sandbox leaves an instance out of its own
    `others`. Rule code gets symbols as plain values (ADR 0008)."""
    out = await outcomes(session, process_id)
    sources = await current_sources(session, process_id)
    population = [
        (i.id, {**flatten_symbols(i.symbols), "_instance": i.name})
        for i in await instances_of(session, process_id)
        if i.symbols is not None
    ]
    dataset = [(i.id, flatten_symbols(i.symbols)) for i in selected]
    # One subprocess per rule, off the event loop.
    return await asyncio.to_thread(
        decide, rules, out, dataset, sources, population, sandbox.run_dataset
    )


def _out(instance: Instance, decision: Decision | None) -> InstanceOut:
    return InstanceOut(
        id=instance.id,
        name=instance.name,
        status=instance.status,
        decision=decision.decision if decision else None,
        author=decision.author if decision else None,
        reason=decision.reason if decision else None,
        decided_at=decision.created_at if decision else None,
    )


async def run(session: AsyncSession, process_id: int) -> RunSummary:
    """Decide every PENDING instance that already has its symbols.

    Runs against the rules active now and the latest load of each source. A rule never
    reads the clock: anything like a cut-off date is a row in a source of truth. An
    instance without symbols is not run and stays PENDING until extraction fills them.
    """
    await get_process(session, process_id)
    rules = await active_rules(session, process_id)
    pending = [
        i
        for i in await session.scalars(
            select(Instance)
            .where(
                Instance.process_id == process_id,
                Instance.status == "PENDING",
            )
            .order_by(Instance.id)
            .with_for_update()
        )
        if i.symbols is not None
    ]
    verdicts = await decide_all(session, process_id, rules, pending)

    count: Counter[str] = Counter()
    for instance, verdict in zip(pending, verdicts, strict=True):
        session.add(
            Decision(
                instance_id=instance.id,
                decision=verdict.decision,
                results=[asdict(r) for r in verdict.results],
                rules_hash=verdict.rules_hash,
                author=ENGINE,
                reason=verdict.reason or None,
            )
        )
        instance.status = "DECIDED"
        events.record(
            session,
            "decision",
            process_id=process_id,
            instance_id=instance.id,
            data={"decision": verdict.decision, "rules_hash": verdict.rules_hash},
        )
        count[verdict.decision] += 1

    await session.commit()
    return RunSummary(decided=sum(count.values()), by_decision=dict(count))


async def list_instances(
    session: AsyncSession,
    process_id: int,
    status: str | None = None,
    decision: str | None = None,
    q: str | None = None,
) -> list[InstanceOut]:
    """Every instance, oldest first. `decision` filters on the latest decision; `q` is a
    case-insensitive match on the name."""
    await get_process(session, process_id)
    instances = await instances_of(session, process_id)
    latest = await latest_decisions(session, instances)
    rows = [_out(i, latest.get(i.id)) for i in instances]
    if status is not None:
        rows = [r for r in rows if r.status == status]
    if decision is not None:
        rows = [r for r in rows if r.decision == decision]
    if q:
        rows = [r for r in rows if q.casefold() in r.name.casefold()]
    return rows


async def summary(session: AsyncSession, process_id: int) -> ProcessSummary:
    """The numbers of a process page. Counts come from each instance's latest decision;
    a rule's `fires` from the latest engine decision only, since a person's carries no
    rule results."""
    process = await get_process(session, process_id)
    instances = await instances_of(session, process_id)
    latest = await latest_decisions(session, instances)
    human = set(await human_types(session, process_id))

    by_status = Counter(i.status for i in instances)
    by_decision = Counter(d.decision for d in latest.values())
    queue = sum(1 for d in latest.values() if d.decision in human)
    resolved = sum(1 for d in latest.values() if d.author != ENGINE)

    # The rule results live in the engine's latest row per instance.
    engine_rows: dict[int, Decision] = {}
    if instances:
        rows = await session.scalars(
            select(Decision)
            .where(Decision.instance_id.in_([i.id for i in instances]), Decision.author == ENGINE)
            .order_by(Decision.id)
        )
        engine_rows = {row.instance_id: row for row in rows}
    fires: Counter[int] = Counter()
    for row in engine_rows.values():
        fires.update(r["rule_id"] for r in row.results if r.get("fires"))
    rules = await session.scalars(
        select(Rule).where(Rule.process_id == process_id).order_by(Rule.id)
    )
    last_run = max((row.created_at for row in engine_rows.values()), default=None)

    return ProcessSummary(
        id=process.id,
        name=process.name,
        instances=len(instances),
        by_status=dict(by_status),
        by_decision=dict(by_decision),
        queue=queue,
        resolved=resolved,
        rules=[
            RuleSummary(
                id=r.id,
                text=r.text,
                type=r.type,
                decision=r.decision,
                status=r.status,
                fires=fires[r.id],
            )
            for r in rules
        ],
        sources=[
            SourceSummary(
                id=load.id,
                name=load.name,
                origin=load.origin,
                rows=len(load.rows),
                loaded_at=load.loaded_at,
            )
            for load in await sources.current_loads(session, process_id)
        ],
        last_run_at=last_run,
    )


async def list_events(
    session: AsyncSession,
    process_id: int,
    step: str | None = None,
    instance_id: int | None = None,
    limit: int = 200,
) -> list[EventOut]:
    """The trace of a process, newest first: runs, resolutions, compilations, syncs, uploads."""
    await get_process(session, process_id)
    query = select(Event).where(Event.process_id == process_id)
    if step is not None:
        query = query.where(Event.step == step)
    if instance_id is not None:
        query = query.where(Event.instance_id == instance_id)
    rows = await session.scalars(query.order_by(Event.id.desc()).limit(limit))
    return [EventOut.model_validate(e, from_attributes=True) for e in rows]


async def queue(session: AsyncSession, process_id: int, type: str | None) -> list[InstanceOut]:
    """Everything waiting for a person: by default, every outcome marked `requires_human`."""
    await get_process(session, process_id)
    wanted = {type} if type else set(await human_types(session, process_id))
    instances = await instances_of(session, process_id)
    latest = await latest_decisions(session, instances)
    return [
        _out(i, latest[i.id])
        for i in instances
        if i.id in latest and latest[i.id].decision in wanted
    ]


async def get_instance(session: AsyncSession, instance_id: int) -> InstanceDetail:
    instance = await _instance(session, instance_id)
    decisions = list(
        await session.scalars(
            select(Decision).where(Decision.instance_id == instance_id).order_by(Decision.id)
        )
    )
    rows = await session.scalars(
        select(Event).where(Event.instance_id == instance_id).order_by(Event.id)
    )
    return InstanceDetail(
        **_out(instance, decisions[-1] if decisions else None).model_dump(),
        file_hash=instance.file_hash,
        symbols=instance.symbols,
        decisions=[DecisionOut.model_validate(d, from_attributes=True) for d in decisions],
        events=[EventOut.model_validate(e, from_attributes=True) for e in rows],
    )


async def resolve(
    session: AsyncSession, instance_id: int, data: ResolveIn, user: User
) -> InstanceDetail:
    """A person's decision is a new row, never an edit of the engine's (ADR 0008)."""
    instance = await _instance(session, instance_id)
    out = await outcomes(session, instance.process_id)
    if data.decision not in out.priorities:
        raise ConflictError(f"{data.decision!r} is not a decision type of this process")

    previous = (await latest_decisions(session, [instance])).get(instance.id)
    session.add(
        Decision(
            instance_id=instance.id,
            decision=data.decision,
            results=[],  # a person decides on the evidence, not by running the rules
            rules_hash=previous.rules_hash if previous else "",
            author=user.name,
            reason=data.reason,
        )
    )
    instance.status = "DECIDED"
    events.record(
        session,
        "resolution",
        process_id=instance.process_id,
        instance_id=instance.id,
        data={"decision": data.decision, "author": user.name},
    )
    await session.commit()
    return await get_instance(session, instance_id)


async def export(session: AsyncSession, process_id: int) -> tuple[str, list[str]]:
    """`outcomes.jsonl` for the challenge: one line per instance name, nothing else.

    Returns the body and the names shared by several instances. `file_id` is the filename
    exactly as it was supplied, accents included. What is exported is the process output:
    the engine's latest decision (ADR 0009). A person's resolution never changes it; it is
    exported only for an instance the engine never decided.
    """
    await get_process(session, process_id)
    # Two files can share a name: only the most recent instance of each name is exported.
    by_name: dict[str, Instance] = {}
    times: Counter[str] = Counter()
    for instance in await instances_of(session, process_id):  # ordered by id
        by_name[instance.name] = instance
        times[instance.name] += 1
    duplicates = [name for name, n in times.items() if n > 1]
    if duplicates:
        log.warning("Process %s: duplicate names on export: %s", process_id, duplicates)
    instances = list(by_name.values())

    pending = [i.name for i in instances if i.status == "PENDING"]
    if pending:
        raise ConflictError(f"{len(pending)} instances pending: {', '.join(pending[:5])}")

    engine: dict[int, Decision] = {}
    human: dict[int, Decision] = {}
    if instances:
        rows = await session.scalars(
            select(Decision)
            .where(Decision.instance_id.in_([i.id for i in instances]))
            .order_by(Decision.id)
        )
        for row in rows:
            (engine if row.author == ENGINE else human)[row.instance_id] = row
    exported = {**human, **engine}

    undecided = [i.name for i in instances if i.id not in exported]
    if undecided:
        raise ConflictError(f"{len(undecided)} undecided instances: {', '.join(undecided[:5])}")
    body = "\n".join(
        json.dumps({"file_id": i.name, "result": exported[i.id].decision}, ensure_ascii=False)
        for i in instances
    )
    return body, duplicates


async def list_findings(session: AsyncSession, process_id: int) -> list[FindingOut]:
    """Past decisions a later rule says were wrong. A notice, never a correction."""
    await get_process(session, process_id)
    rows = await session.scalars(
        select(Finding)
        .join(Decision, Finding.decision_id == Decision.id)
        .join(Instance, Decision.instance_id == Instance.id)
        .where(Instance.process_id == process_id)
        .order_by(Finding.id)
    )
    return [FindingOut.model_validate(r, from_attributes=True) for r in rows]
