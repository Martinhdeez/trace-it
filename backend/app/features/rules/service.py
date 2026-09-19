import asyncio
import hashlib
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.core import events
from app.core.config import settings
from app.core.database import session_factory
from app.features.agents import compiler
from app.features.decisions import audit
from app.features.processes.model import Symbol
from app.features.rules.model import ENFORCED, NormRule, Rule
from app.features.rules.schemas import CheckOut, NormRuleOut, RuleDetail, RuleIn, RuleOut

logger = logging.getLogger(__name__)

AUTO = "auto"  # the author of what the system did by itself


def rule_hash(text: str, code: str) -> str:
    return hashlib.sha256(f"{text}\0{code}".encode()).hexdigest()


def _out(rule: Rule) -> RuleOut:
    return RuleOut.model_validate(rule, from_attributes=True)


def _detail(rule: Rule) -> RuleDetail:
    return RuleDetail.model_validate(rule, from_attributes=True)


async def _rule(session: AsyncSession, rule_id: int) -> Rule:
    rule = await session.get(Rule, rule_id)
    if rule is None:
        raise NotFoundError(f"Rule {rule_id} does not exist")
    return rule


async def list_all(session: AsyncSession, process_id: int, status: str | None) -> list[RuleOut]:
    query = select(Rule).where(Rule.process_id == process_id).order_by(Rule.id)
    if status:
        query = query.where(Rule.status == status)
    return [_out(r) for r in await session.scalars(query)]


async def list_norm_rules(session: AsyncSession, process_id: int) -> list[NormRuleOut]:
    """The sentences of the client's norm, each with its atomic rules (ADR 0017)."""
    norm_rules = await session.scalars(
        select(NormRule).where(NormRule.process_id == process_id).order_by(NormRule.id)
    )
    checks = await session.scalars(
        select(Rule)
        .where(Rule.process_id == process_id, Rule.norm_rule_id.is_not(None))
        .order_by(Rule.id)
    )
    by_norm_rule: dict[int, list[CheckOut]] = {}
    for r in checks:
        by_norm_rule.setdefault(r.norm_rule_id, []).append(
            CheckOut.model_validate(r, from_attributes=True)
        )
    return [
        NormRuleOut(
            id=n.id,
            number=n.number,
            text=n.text,
            policies=n.policies,
            created_at=n.created_at,
            rules=by_norm_rule.get(n.id, []),
        )
        for n in norm_rules
    ]


async def get(session: AsyncSession, rule_id: int) -> RuleDetail:
    return _detail(await _rule(session, rule_id))


async def create(session: AsyncSession, process_id: int, data: RuleIn) -> RuleDetail:
    from copy import deepcopy

    from app.features.versions import configuration as config
    from app.features.versions import service as versions
    from app.features.versions.model import ProcessDraft

    await versions.lock(session, process_id)
    draft = await session.get(ProcessDraft, process_id, populate_existing=True)
    version = await versions.active(session, process_id, required=False)
    snapshot = deepcopy(
        draft.snapshot
        if draft
        else version.snapshot
        if version
        else await config.workspace(session, process_id)
    )
    if data.decision not in {t["name"] for t in snapshot["process"]["decision_types"]}:
        raise ConflictError(f"{data.decision!r} is not a decision type of this draft")
    rule = Rule(process_id=process_id, status="compiling", **data.model_dump())
    session.add(rule)
    await session.flush()
    snapshot["rules"].append(config.artifact(rule))
    await versions.stage(session, process_id, snapshot, "rule author")
    await session.commit()
    return _detail(rule)


async def compile_rule(session: AsyncSession, rule_id: int, author: str = AUTO) -> RuleDetail:
    """Compile (or recompile) a draft or blocked rule and wait for the result."""
    rule = await _rule(session, rule_id)
    if rule.status not in ("draft", "blocked", "retired"):
        raise ConflictError(f"Only a draft or blocked rule can be compiled (it is {rule.status})")
    return await _compile(session, rule, author)


def _kept(rule: Rule, report: dict[str, Any]) -> dict[str, Any]:
    """A new report for `rule` that keeps how the normalizer read it (ADR 0017)."""
    norm = (rule.report or {}).get("norm")
    return {**report, "norm": norm} if norm else report


async def _compile(session: AsyncSession, rule: Rule, author: str = AUTO) -> RuleDetail:
    links = {"rule_id": rule.id, "process_id": rule.process_id, "norm_rule_id": rule.norm_rule_id}
    with events.span("compile_rule", author=author, before=rule.status, **links) as span:
        try:
            detail = await _compile_traced(session, rule)
        except Exception:
            span.set(rule_status="draft", valid=False)
            raise
        span.set(rule_status=detail.status, valid=bool((detail.report or {}).get("valid")))
        return detail


async def _compile_traced(session: AsyncSession, rule: Rule) -> RuleDetail:
    from copy import deepcopy

    from app.features.versions import configuration as version_config
    from app.features.versions import service as versions
    from app.features.versions.model import ProcessDraft

    draft = await session.get(ProcessDraft, rule.process_id, populate_existing=True)
    context_hash = (
        version_config.digest({k: draft.snapshot[k] for k in ("process", "agents")})
        if draft
        else None
    )
    symbols = list(
        await session.scalars(select(Symbol).where(Symbol.process_id == rule.process_id))
    )
    result = await compiler.compile_rule(session, rule, symbols)
    await versions.lock(session, rule.process_id)
    current = await session.get(ProcessDraft, rule.process_id, populate_existing=True)
    current_hash = (
        version_config.digest({k: current.snapshot[k] for k in ("process", "agents")})
        if current
        else None
    )
    if current_hash != context_hash:
        raise ConflictError("Draft configuration changed during compilation; compile again")
    rule.code, rule.tests = result.code, result.tests
    rule.hash = rule_hash(rule.text, rule.code) if rule.code else None
    rule.status, rule.activated_at = "draft", None
    rule.report = _kept(
        rule,
        {**result.report, "activation": {"auto": False, "why": "Manager publication required"}},
    )
    # Refresh this artifact in the one draft, invalidating any previous preview.
    draft = await session.get(ProcessDraft, rule.process_id, populate_existing=True)
    if draft and any(r["id"] == rule.id for r in draft.snapshot["rules"]):
        snapshot = deepcopy(draft.snapshot)
        snapshot["rules"] = [
            version_config.artifact(rule) if r["id"] == rule.id else r for r in snapshot["rules"]
        ]
        await versions.stage(session, rule.process_id, snapshot, "compiler")
    await session.commit()
    return _detail(rule)


async def compile_in_background(rule_id: int) -> None:
    """Compile a rule saved as `compiling`, with its own session. Whatever happens, the rule
    leaves `compiling`: a failure leaves a draft with the error in its report."""
    async with session_factory() as session:
        try:
            await _compile(session, await _rule(session, rule_id))
        except Exception as e:  # noqa: BLE001 - LLM down, malformed answers, anything
            logger.exception("Compiling rule %s failed", rule_id)
            await session.rollback()
            rule = await _rule(session, rule_id)
            if rule.status != "compiling":  # it got past compiling before failing
                return
            error = f"{type(e).__name__}: {e}"
            rule.status = "draft"
            rule.report = _kept(rule, {"valid": False, "error": error})
            await session.commit()


async def compile_all_in_background(rule_ids: list[int], parent: events.Span | None = None) -> None:
    """Compile several saved rules concurrently, at most `compile_concurrency` at once.
    One background job per request: FastAPI runs a request's background tasks one after
    another. `parent`: the span of the request that saved them, whose trace this continues."""
    # ponytail: the bound is per job; two norms saved at once may double it. A module-wide
    # semaphore if providers start refusing.
    limit = asyncio.Semaphore(settings.compile_concurrency)

    async def one(rule_id: int) -> None:
        async with limit:
            await compile_in_background(rule_id)

    with events.span("compile_rules", parent=parent, rules=len(rule_ids)):
        await asyncio.gather(*(one(i) for i in rule_ids))


_jobs: set[asyncio.Task] = set()  # references, so a running compilation is not collected


async def resume_compilations() -> list[asyncio.Task]:
    """On startup: compile again every rule a restart left in `compiling`. Best effort: with
    the database unreachable the API still starts, and those rules wait for the next start
    or a recompile."""
    try:
        async with session_factory() as session:
            ids = list(await session.scalars(select(Rule.id).where(Rule.status == "compiling")))
    except (SQLAlchemyError, OSError) as e:
        logger.warning("Rules left compiling were not resumed: %s", e)
        return []
    tasks = [asyncio.create_task(compile_all_in_background(ids))] if ids else []
    for task in tasks:
        _jobs.add(task)
        task.add_done_callback(_jobs.discard)
    return tasks


async def impact(session: AsyncSession, rule_id: int) -> audit.Impact:
    """What activating (or retiring) this rule would do, without doing it."""
    rule = await _rule(session, rule_id)
    links = {"rule_id": rule.id, "process_id": rule.process_id, "norm_rule_id": rule.norm_rule_id}
    with events.span("impact_check", preview=True, **links) as span:
        proposed = (
            await audit.proposal_without(session, rule)
            if rule.status in ENFORCED
            else await audit.proposal_with(session, rule)
        )
        result = await audit.check(session, rule.process_id, proposed)
        span.set(changed=len(result.changes), conflicts=len(result.conflicts))
        return result


async def _stage_rule(session, rule_id: int, author: str, include: bool) -> RuleDetail:
    from copy import deepcopy

    from app.features.versions import configuration as config
    from app.features.versions import service as versions
    from app.features.versions.model import ProcessDraft

    rule = await _rule(session, rule_id)
    if include and (not rule.code or not (rule.report or {}).get("valid")):
        raise ConflictError("Rule is not compiled or has unresolved discrepancies")
    await versions.lock(session, rule.process_id)
    draft = await session.get(ProcessDraft, rule.process_id, populate_existing=True)
    version = await versions.active(session, rule.process_id, required=False)
    snapshot = deepcopy(
        draft.snapshot
        if draft
        else version.snapshot
        if version
        else await config.workspace(session, rule.process_id)
    )
    snapshot["rules"] = [r for r in snapshot["rules"] if r["id"] != rule.id]
    if include:
        snapshot["rules"].append(config.artifact(rule))
        snapshot["rules"].sort(key=lambda r: r["id"])
    await versions.stage(session, rule.process_id, snapshot, author)
    await session.commit()
    return _detail(rule)


async def activate(session: AsyncSession, rule_id: int, author: str = AUTO) -> RuleDetail:
    """Include a rule in the draft; validation and publication are explicit operations."""
    with events.span(
        "activate_rule",
        process_id=(await _rule(session, rule_id)).process_id,
        rule_id=rule_id,
        author=author,
        draft_only=True,
    ):
        return await _stage_rule(session, rule_id, author, True)


async def retire(session: AsyncSession, rule_id: int, author: str) -> RuleDetail:
    """Remove a rule from the draft without changing the published configuration."""
    with events.span(
        "retire_rule",
        process_id=(await _rule(session, rule_id)).process_id,
        rule_id=rule_id,
        author=author,
        draft_only=True,
    ):
        return await _stage_rule(session, rule_id, author, False)
