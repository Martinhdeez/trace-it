import json
import logging
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.features.agents import sandbox
from app.features.decisions.engine import decide
from app.features.decisions.model import ENGINE, Decision, Finding
from app.features.decisions.schemas import (
    DecisionOut,
    EventOut,
    FindingOut,
    InstanceDetail,
    InstanceOut,
    ResolveIn,
    RunSummary,
)
from app.features.ingestion.model import Instance
from app.features.processes.model import DecisionType
from app.features.processes.service import get as get_process
from app.features.rules.model import Rule
from app.features.sources.model import Source
from app.features.traces import service as traces
from app.features.traces.model import Event
from app.features.users.model import User

log = logging.getLogger(__name__)


async def _instance(session: AsyncSession, instance_id: int) -> Instance:
    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise NotFoundError(f"Instance {instance_id} does not exist")
    return instance


@dataclass(frozen=True)
class Outcomes:
    """What a process can conclude: the priorities, the outcome when no rule fires, and the
    outcomes that send the case to a person."""

    priorities: dict[str, int]
    default: str
    human: list[str]

    @property
    def escalate(self) -> str:
        """Where the engine puts a case it could not decide: the highest-priority outcome
        that needs a person."""
        return max(self.human, key=lambda name: self.priorities[name])


async def _outcomes(session: AsyncSession, process_id: int) -> Outcomes:
    types = list(
        await session.scalars(select(DecisionType).where(DecisionType.process_id == process_id))
    )
    if not types:
        raise ConflictError("The process has no decision types")
    default = next((t.name for t in types if t.is_default), None)
    if default is None:
        raise ConflictError("The process has no default decision type")
    human = [t.name for t in types if t.requires_human]
    if not human:
        raise ConflictError(
            "The process has no decision type with `requires_human`: "
            "the engine would have nowhere to put a case it cannot decide"
        )
    return Outcomes({t.name: t.priority for t in types}, default, human)


async def _current_sources(
    session: AsyncSession, process_id: int
) -> dict[str, list[dict[str, Any]]]:
    """The latest load of each source of truth. Every load is kept; only the last one is used."""
    loads = await session.scalars(
        select(Source).where(Source.process_id == process_id).order_by(Source.id)
    )
    return {load.name: load.rows for load in loads}


async def _instances(session: AsyncSession, process_id: int) -> list[Instance]:
    return list(
        await session.scalars(
            select(Instance).where(Instance.process_id == process_id).order_by(Instance.id)
        )
    )


async def _latest_decisions(
    session: AsyncSession, instances: list[Instance]
) -> dict[int, Decision]:
    """An instance's current decision is its latest row (the history only ever grows)."""
    if not instances:
        return {}
    rows = await session.scalars(
        select(Decision)
        .where(Decision.instance_id.in_([i.id for i in instances]))
        .order_by(Decision.id)
    )
    return {row.instance_id: row for row in rows}


def _out(instance: Instance, decision: Decision | None) -> InstanceOut:
    return InstanceOut(
        id=instance.id,
        name=instance.name,
        status=instance.status,
        decision=decision.decision if decision else None,
    )


async def run(session: AsyncSession, process_id: int) -> RunSummary:
    """Decide every PENDING instance that already has its symbols.

    Runs against the rules active now and the latest load of each source. A rule never
    reads the clock: anything like a cut-off date is a row in a source of truth.
    """
    await get_process(session, process_id)
    outcomes = await _outcomes(session, process_id)
    rules = list(
        await session.scalars(
            select(Rule)
            .where(Rule.process_id == process_id, Rule.status == "active")
            .order_by(Rule.id)
        )
    )
    sources = await _current_sources(session, process_id)
    instances = await _instances(session, process_id)
    # Each entry of `others` carries `_instance` so a rule can name the duplicate it found.
    symbols = {i.id: {**i.symbols, "_instance": i.name} for i in instances if i.symbols is not None}

    count: Counter[str] = Counter()
    for instance in instances:
        if instance.status != "PENDING" or instance.symbols is None:
            continue
        others = [s for iid, s in symbols.items() if iid != instance.id]
        verdict = decide(
            rules,
            outcomes.priorities,
            outcomes.default,
            outcomes.escalate,
            instance.symbols,
            sources,
            others,
            sandbox.run,
        )
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
        traces.record(
            session,
            "decision",
            instance_id=instance.id,
            data={"decision": verdict.decision, "rules_hash": verdict.rules_hash},
        )
        count[verdict.decision] += 1

    await session.commit()
    return RunSummary(decided=sum(count.values()), by_decision=dict(count))


async def list_instances(
    session: AsyncSession, process_id: int, status: str | None
) -> list[InstanceOut]:
    await get_process(session, process_id)
    instances = await _instances(session, process_id)
    latest = await _latest_decisions(session, instances)
    return [_out(i, latest.get(i.id)) for i in instances if status is None or i.status == status]


async def queue(session: AsyncSession, process_id: int, type: str | None) -> list[InstanceOut]:
    """Everything waiting for a person: by default, every outcome marked `requires_human`."""
    await get_process(session, process_id)
    outcomes = await _outcomes(session, process_id)
    wanted = {type} if type else set(outcomes.human)
    instances = await _instances(session, process_id)
    latest = await _latest_decisions(session, instances)
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
    events = await session.scalars(
        select(Event).where(Event.instance_id == instance_id).order_by(Event.id)
    )
    return InstanceDetail(
        **_out(instance, decisions[-1] if decisions else None).model_dump(),
        file_hash=instance.file_hash,
        symbols=instance.symbols,
        decisions=[DecisionOut.model_validate(d, from_attributes=True) for d in decisions],
        events=[EventOut.model_validate(e, from_attributes=True) for e in events],
    )


async def resolve(
    session: AsyncSession, instance_id: int, data: ResolveIn, user: User
) -> InstanceDetail:
    """A person's decision is a new row, never an edit of the engine's (P14)."""
    instance = await _instance(session, instance_id)
    outcomes = await _outcomes(session, instance.process_id)
    if data.decision not in outcomes.priorities:
        raise ConflictError(f"{data.decision!r} is not a decision type of this process")

    latest = await _latest_decisions(session, [instance])
    previous = latest.get(instance.id)
    session.add(
        Decision(
            instance_id=instance.id,
            decision=data.decision,
            results=[],  # a person decides on the evidence, not by running the rules
            rules_hash=previous.rules_hash if previous else "",
            author=user.name,
            human_kind="review_correction" if instance.status == "REVIEW" else "resolution",
            reason=data.reason,
        )
    )
    instance.status = "DECIDED"
    traces.record(
        session,
        "resolution",
        instance_id=instance.id,
        data={"decision": data.decision, "author": user.name},
    )
    await session.commit()
    return await get_instance(session, instance_id)


async def export(session: AsyncSession, process_id: int) -> tuple[str, list[str]]:
    """`outcomes.jsonl` for the challenge: one line per instance name, nothing else.

    Returns the body and the names shared by several instances. `file_id` is the filename
    exactly as it was supplied, accents included. What is exported is the process output:
    the engine's latest decision or, when the engine has none, a person's correction of an
    instance that was in REVIEW. A person's `resolution` never changes it (P4).
    """
    await get_process(session, process_id)
    # Two files can share a name: only the most recent instance of each name is exported.
    by_name: dict[str, Instance] = {}
    times: Counter[str] = Counter()
    for instance in await _instances(session, process_id):  # ordered by id
        by_name[instance.name] = instance
        times[instance.name] += 1
    duplicates = [name for name, n in times.items() if n > 1]
    if duplicates:
        log.warning("Process %s: duplicate names on export: %s", process_id, duplicates)
    instances = list(by_name.values())

    open_ = [i.name for i in instances if i.status in ("PENDING", "REVIEW")]
    if open_:
        raise ConflictError(f"{len(open_)} instances pending or in review: {', '.join(open_[:5])}")

    engine: dict[int, Decision] = {}
    corrections: dict[int, Decision] = {}
    if instances:
        rows = await session.scalars(
            select(Decision)
            .where(Decision.instance_id.in_([i.id for i in instances]))
            .order_by(Decision.id)
        )
        for row in rows:
            if row.author == ENGINE:
                engine[row.instance_id] = row
            elif row.human_kind == "review_correction":
                corrections[row.instance_id] = row
    exported = {**corrections, **engine}

    undecided = [i.name for i in instances if i.id not in exported]
    if undecided:
        raise ConflictError(f"{len(undecided)} undecided instances: {', '.join(undecided[:5])}")
    body = "\n".join(
        json.dumps({"file_id": i.name, "result": exported[i.id].decision}, ensure_ascii=False)
        for i in instances
    )
    return body, duplicates


async def list_findings(session: AsyncSession, process_id: int) -> list[FindingOut]:
    """Past decisions a later rule says were wrong. A notice, never a correction (P14)."""
    await get_process(session, process_id)
    rows = await session.scalars(
        select(Finding)
        .join(Decision, Finding.decision_id == Decision.id)
        .join(Instance, Decision.instance_id == Instance.id)
        .where(Instance.process_id == process_id)
        .order_by(Finding.id)
    )
    return [FindingOut.model_validate(r, from_attributes=True) for r in rows]
