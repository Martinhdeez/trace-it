"""Read the audit trail (`events`, ADR 0018): span trees, an instance's journey, how a rule
was produced, and a process's aggregates."""

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.core.events import Event
from app.features.agents import decision_reviewer
from app.features.decisions import service as decisions
from app.features.decisions.model import ENGINE, Decision
from app.features.decisions.schemas import DecisionOut
from app.features.ingestion.model import File, Instance
from app.features.processes.service import get as get_process
from app.features.rules.model import NormRule, Rule
from app.features.traces.schemas import (
    DecisionTrace,
    FileOut,
    InstanceTrace,
    LlmStats,
    ProcessMetrics,
    ProviderStats,
    RuleResultOut,
    RuleRuntime,
    RuleTrace,
    SpanNode,
    SpanOut,
    StepStats,
)

FAILURES = ("MISSING_DATA", "RULE_ERROR", "RULE_NEEDS_DATA", "RULE_CONFLICT")
LIFECYCLE = ("save_rule", "compile_rule", "activate_rule", "retire_rule", "impact_check")


def _nodes(rows: Iterable[Event]) -> dict[str, SpanNode]:
    """Every span by id, each holding its children in start order."""
    nodes = {r.span_id: SpanNode.model_validate(r, from_attributes=True) for r in rows}
    for node in sorted(nodes.values(), key=lambda n: (n.started_at, n.id)):
        if node.parent_id in nodes:
            nodes[node.parent_id].children.append(node)
    return nodes


def _roots(nodes: dict[str, SpanNode]) -> list[SpanNode]:
    return sorted(
        (n for n in nodes.values() if n.parent_id not in nodes), key=lambda n: (n.started_at, n.id)
    )


async def list_spans(
    session: AsyncSession,
    process_id: int | None,
    step: str | None,
    status: str | None,
    limit: int,
) -> list[SpanOut]:
    query = select(Event)
    if process_id is not None:
        query = query.where(Event.process_id == process_id)
    if step is not None:
        query = query.where(Event.step == step)
    if status is not None:
        query = query.where(Event.status == status)
    rows = await session.scalars(query.order_by(Event.id.desc()).limit(limit))
    return [SpanOut.model_validate(r, from_attributes=True) for r in rows]


async def get_trace(session: AsyncSession, trace_id: str) -> list[SpanNode]:
    rows = list(await session.scalars(select(Event).where(Event.trace_id == trace_id)))
    if not rows:
        raise NotFoundError(f"Trace {trace_id} does not exist")
    return _roots(_nodes(rows))


async def instance_trace(session: AsyncSession, instance_id: int) -> InstanceTrace:
    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise NotFoundError(f"Instance {instance_id} does not exist")
    file = (
        await session.execute(
            select(File.hash, File.name, func.length(File.content), File.ingested_at).where(
                File.hash == instance.file_hash
            )
        )
    ).first()
    history = list(
        await session.scalars(
            select(Decision).where(Decision.instance_id == instance_id).order_by(Decision.id)
        )
    )
    rule_ids = {r["rule_id"] for d in history for r in d.results}
    rules = {r.id: r for r in await session.scalars(select(Rule).where(Rule.id.in_(rule_ids)))}
    # Its spans, and in the same traces the steps of no particular instance (the upload's
    # reading steps, the run and its per-rule spans), never another instance's.
    traces = select(Event.trace_id).where(Event.instance_id == instance_id)
    query = select(Event).where(
        Event.trace_id.in_(traces),
        or_(Event.instance_id == instance_id, Event.instance_id.is_(None)),
    )
    rows = list(await session.scalars(query))
    if history:
        exports = (
            select(Event)
            .where(
                Event.process_id == instance.process_id,
                Event.step == "export_outcomes",
                Event.started_at >= history[0].created_at,
            )
            .order_by(Event.id.desc())
            .limit(10)
        )
        rows += list(await session.scalars(exports))
    engine = [d for d in history if d.author == ENGINE]
    automatic = engine[-1] if engine else None
    human = next((d for d in reversed(history) if d.author != ENGINE), None)
    exported = automatic or human
    if automatic:
        review = (await decision_reviewer.for_decisions(session, [automatic])).get(automatic.id)
        if review:
            if human and human.id > automatic.id:
                exported = human
            elif review.requires_human:
                exported = None
    if instance.status == "PENDING":
        exported = None
    return InstanceTrace(
        id=instance.id,
        process_id=instance.process_id,
        name=instance.name,
        status=instance.status,
        file=FileOut(hash=file[0], name=file[1], size_bytes=file[2], ingested_at=file[3])
        if file
        else None,
        symbols=instance.symbols,
        decisions=[
            DecisionTrace(
                **DecisionOut.model_validate(d, from_attributes=True).model_dump(),
                rule_results=[
                    RuleResultOut(
                        **r,
                        rule_text=rules[r["rule_id"]].text if r["rule_id"] in rules else None,
                        norm_rule_id=rules[r["rule_id"]].norm_rule_id
                        if r["rule_id"] in rules
                        else None,
                    )
                    for r in d.results
                ],
            )
            for d in history
        ],
        exported_decision=exported.decision if exported else None,
        spans=_roots(_nodes(rows)),
    )


def _p(q: float):
    return func.percentile_cont(q).within_group(Event.duration_ms)


async def rule_trace(session: AsyncSession, rule_id: int) -> RuleTrace:
    rule = await session.get(Rule, rule_id)
    if rule is None:
        raise NotFoundError(f"Rule {rule_id} does not exist")
    norm_rule = await session.get(NormRule, rule.norm_rule_id) if rule.norm_rule_id else None
    traces = select(Event.trace_id).where(Event.rule_id == rule_id, Event.step == "compile_rule")
    nodes = _nodes(await session.scalars(select(Event).where(Event.trace_id.in_(traces))))
    compilations = sorted(
        (n for n in nodes.values() if n.step == "compile_rule" and n.rule_id == rule_id),
        key=lambda n: n.started_at,
        reverse=True,
    )
    normalizations = [n for n in nodes.values() if n.step == "normalize_norm"]
    runs = select(Event.span_id).where(
        Event.process_id == rule.process_id, Event.step == "run_process"
    )
    evaluated = (
        await session.execute(
            select(
                func.count(),
                func.sum(Event.data["instances"].as_integer()),
                func.sum(Event.data["fired"].as_integer()),
                func.sum(Event.data["errors"].as_integer()),
                _p(0.5),
                _p(0.95),
            ).where(
                Event.step == "evaluate_rule",
                Event.rule_id == rule_id,
                Event.parent_id.in_(runs),
            )
        )
    ).one()
    lifecycle = await session.scalars(
        select(Event)
        .where(Event.rule_id == rule_id, Event.step.in_(LIFECYCLE))
        .order_by(Event.started_at)
    )
    return RuleTrace(
        id=rule.id,
        process_id=rule.process_id,
        text=rule.text,
        status=rule.status,
        norm_rule_id=rule.norm_rule_id,
        norm_rule_text=norm_rule.text if norm_rule else None,
        activation=(rule.report or {}).get("activation"),
        normalization=SpanOut.model_validate(
            max(normalizations, key=lambda n: n.started_at).model_dump(exclude={"children"})
        )
        if normalizations
        else None,
        compilations=compilations,
        lifecycle=[SpanOut.model_validate(e, from_attributes=True) for e in lifecycle],
        runtime=RuleRuntime(
            runs=evaluated[0],
            instances=evaluated[1] or 0,
            fired=evaluated[2] or 0,
            errors=evaluated[3] or 0,
            p50_ms=evaluated[4],
            p95_ms=evaluated[5],
        ),
    )


async def metrics(session: AsyncSession, process_id: int, since: datetime | None) -> ProcessMetrics:
    await get_process(session, process_id)
    spans = [Event.process_id == process_id]
    if since is not None:
        spans.append(Event.started_at >= since)
    errors = func.count().filter(Event.status == "error")
    steps = await session.execute(
        select(Event.step, func.count(), errors, _p(0.5), _p(0.95))
        .where(*spans)
        .group_by(Event.step)
        .order_by(Event.step)
    )
    runs = (
        await session.execute(
            select(
                func.count(),
                func.sum(Event.data["instances"].as_integer()),
                func.sum(Event.duration_ms),
            ).where(*spans, Event.step == "run_process", Event.status == "ok")
        )
    ).one()

    def total(key: str):
        return func.coalesce(func.sum(Event.data[key].as_integer()), 0)

    model, role = Event.data["model"].astext, Event.data["role"].astext
    llm = await session.execute(
        select(
            model,
            role,
            func.count(),
            errors,
            total("retries"),
            total("input_tokens"),
            total("output_tokens"),
        )  # fmt: skip
        .where(*spans, Event.step == "llm_run")
        .group_by(model, role)
        .order_by(model, role)
    )

    provider = Event.data["provider"].astext
    provider_model = Event.data["model"].astext
    operation = Event.data["operation"].astext
    network = Event.data["network_attempted"].as_boolean().is_(True)
    replay = Event.data["outcome"].astext == "replay"
    providers = await session.execute(
        select(
            provider,
            provider_model,
            operation,
            func.count(),
            func.count().filter(network),
            func.count().filter(replay),
            errors,
            func.coalesce(func.sum(Event.data["input_tokens"].as_integer()).filter(network), 0),
            func.coalesce(func.sum(Event.data["output_tokens"].as_integer()).filter(network), 0),
        )
        .where(*spans, Event.step == "provider_call")
        .group_by(provider, provider_model, operation)
        .order_by(provider, provider_model, operation)
    )

    decided = [Instance.process_id == process_id]
    if since is not None:
        decided.append(Decision.created_at >= since)
    by_outcome = await session.execute(
        select(Decision.decision, func.count())
        .join(Instance, Decision.instance_id == Instance.id)
        .where(*decided)
        .group_by(Decision.decision)
    )
    failures = (
        await session.execute(
            select(*(func.count().filter(Decision.reason.contains(code)) for code in FAILURES))
            .join(Instance, Decision.instance_id == Instance.id)
            .where(*decided)
        )
    ).one()
    pending = await session.scalar(
        select(func.count()).where(Instance.process_id == process_id, Instance.status == "PENDING")
    )
    instances, run_ms = runs[1] or 0, runs[2] or 0
    return ProcessMetrics(
        since=since,
        runs=runs[0],
        instances_decided=instances,
        instances_per_second=round(instances / run_ms * 1000, 1) if run_ms else None,
        steps=[
            StepStats(step=s, count=c, errors=e, p50_ms=p50, p95_ms=p95)
            for s, c, e, p50, p95 in steps
        ],
        llm=[
            LlmStats(
                model=m,
                role=r,
                calls=c,
                errors=e,
                retries=retries,
                input_tokens=tokens_in,
                output_tokens=tokens_out,
            )
            for m, r, c, e, retries, tokens_in, tokens_out in llm
        ],
        providers=[
            ProviderStats(
                provider=p,
                model=m,
                operation=o,
                attempts=c,
                network_requests=n,
                replays=replays,
                errors=e,
                input_tokens=tokens_in,
                output_tokens=tokens_out,
            )
            for p, m, o, c, n, replays, e, tokens_in, tokens_out in providers
        ],
        decisions_by_outcome=dict(by_outcome.all()),
        failures=dict(zip(FAILURES, failures, strict=True)),
        escalated=len(await decisions.queue(session, process_id, None)),
        pending=pending,
    )
