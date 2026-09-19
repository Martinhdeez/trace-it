import asyncio
import hashlib
import logging
from datetime import UTC, datetime
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
from app.features.decisions.model import Decision
from app.features.processes.model import DecisionType, Process, Symbol
from app.features.processes.service import get as get_process
from app.features.rules.model import ENFORCED, NormRule, Rule
from app.features.rules.schemas import CheckOut, NormRuleOut, RuleDetail, RuleIn, RuleOut
from app.features.use_cases import service as use_cases

logger = logging.getLogger(__name__)


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
    await get_process(session, process_id)
    if not await session.get(DecisionType, (process_id, data.decision)):
        raise ConflictError(f"{data.decision!r} is not a decision type of this process")
    rule = Rule(process_id=process_id, status="compiling", **data.model_dump())
    session.add(rule)
    await session.commit()
    return _detail(rule)


async def compile_rule(session: AsyncSession, rule_id: int) -> RuleDetail:
    """Compile (or recompile) a draft or blocked rule and wait for the result."""
    rule = await _rule(session, rule_id)
    if rule.status not in ("draft", "blocked"):
        raise ConflictError(f"Only a draft or blocked rule can be compiled (it is {rule.status})")
    return await _compile(session, rule)


def _kept(rule: Rule, report: dict[str, Any]) -> dict[str, Any]:
    """A new report for `rule` that keeps how the normalizer read it (ADR 0017)."""
    norm = (rule.report or {}).get("norm")
    return {**report, "norm": norm} if norm else report


async def _compile(session: AsyncSession, rule: Rule) -> RuleDetail:
    links = {"rule_id": rule.id, "process_id": rule.process_id, "norm_rule_id": rule.norm_rule_id}
    with events.span("compile_rule", **links) as span:
        detail = await _compile_traced(session, rule)
        span.set(rule_status=detail.status, valid=bool((detail.report or {}).get("valid")))
        return detail


async def _compile_traced(session: AsyncSession, rule: Rule) -> RuleDetail:
    symbols = list(
        await session.scalars(select(Symbol).where(Symbol.process_id == rule.process_id))
    )
    result = await compiler.compile_rule(session, rule, symbols)
    rule.code, rule.tests = result.code, result.tests
    rule.hash = rule_hash(rule.text, rule.code) if rule.code else None
    if "needs_data" in result.report:
        # Fail closed: a rule the process cannot evaluate escalates every instance, whatever
        # its impact. It has no verdict on the past, so it records no audit findings.
        why = "needs data the process does not have: every instance escalates"
        rule.report = _kept(rule, {**result.report, "activation": {"auto": True, "why": why}})
        rule.status = "blocked"
        rule.activated_at = datetime.now(UTC)
        await session.commit()
        return _detail(rule)
    was_blocked = rule.status == "blocked"
    rule.status, rule.activated_at = "draft", None
    activation = await _auto_activation(session, rule, result, was_blocked)
    rule.report = _kept(rule, {**result.report, "activation": activation})
    await session.commit()
    if rule.report["activation"]["auto"]:
        return await activate(session, rule.id)
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


async def _own_escalations(session: AsyncSession, rule: Rule, impact: audit.Impact) -> set[int]:
    """The changed decisions this rule itself escalated while blocked. Undoing them is the
    point of recompiling it, not an effect on history to weigh."""
    ids = [c.decision_id for c in impact.changes]
    own = f"RULE_NEEDS_DATA {rule.id}:"
    query = select(Decision.id).where(Decision.id.in_(ids), Decision.reason.contains(own))
    return set(await session.scalars(query)) if ids else set()


async def _auto_activation(
    session: AsyncSession, rule: Rule, result: compiler.Compilation, was_blocked: bool = False
) -> dict[str, Any]:
    """Whether a freshly compiled rule may enter the process without a person: its code
    passed the tester's tests, it contradicts no decision a person took and it changes at
    most `auto_activate_max_change` of the decisions already taken (ADR 0004)."""
    if not result.report["valid"]:
        return {"auto": False, "why": "not valid"}
    with events.span("impact_check") as span:
        activation = await _impact_gate(session, rule, was_blocked)
        span.set(**activation)
        return activation


async def _impact_gate(session: AsyncSession, rule: Rule, was_blocked: bool) -> dict[str, Any]:
    impact = await audit.check(session, rule.process_id, await audit.proposal_with(session, rule))
    unblocked = await _own_escalations(session, rule, impact) if was_blocked else set()
    changed = len(impact.changes) - len(unblocked) + len(impact.conflicts)
    total = impact.unchanged + changed
    share = changed / total if total else 0.0
    process = await session.get(Process, rule.process_id)
    compiler_setup = (await use_cases.setups(session, process.use_case_id)).get("compiler")
    default = settings.auto_activate_max_change
    limit = compiler_setup.limit("auto_activate_max_change", default) if compiler_setup else default
    why = (
        f"{len(impact.conflicts)} decisions taken by a person would change"
        if impact.conflicts
        else f"changes {changed}/{total} past decisions (limit {limit:.0%})"
    )
    return {
        "auto": not impact.conflicts and share <= limit,
        "why": why,
        "changed": changed,
        "decided": total,
        **({"unblocked": len(unblocked)} if was_blocked else {}),
    }


async def _apply(session: AsyncSession, rule: Rule, proposed: list[Rule]) -> None:
    """Check a rule change against every decision already taken, then adopt it.

    The past is never rewritten. What the change says about it is recorded as findings for
    the manager to act on outside this system. A change that would contradict a decision a
    person took is refused until they resolve it (ADR 0008).
    """
    impact = await audit.check(session, rule.process_id, proposed)
    if impact.conflicts:
        contradicted = ", ".join(c.name for c in impact.conflicts[:5])
        raise ConflictError(
            f"{len(impact.conflicts)} decisions taken by a person would change: "
            f"{contradicted}. Resolve them before applying this rule"
        )
    await audit.record_findings(session, rule.process_id, impact, rule)


async def impact(session: AsyncSession, rule_id: int) -> audit.Impact:
    """What activating (or retiring) this rule would do, without doing it."""
    rule = await _rule(session, rule_id)
    proposed = (
        await audit.proposal_without(session, rule)
        if rule.status in ENFORCED
        else await audit.proposal_with(session, rule)
    )
    return await audit.check(session, rule.process_id, proposed)


async def activate(session: AsyncSession, rule_id: int) -> RuleDetail:
    """A rule only enters the process when its validation found no discrepancy."""
    rule = await _rule(session, rule_id)
    if rule.status != "draft":
        raise ConflictError(f"Only a draft rule can be activated (it is {rule.status})")
    if not (rule.report or {}).get("valid"):
        raise ConflictError("The rule has unresolved discrepancies or is not compiled")
    with events.span("activate_rule", rule_id=rule.id, process_id=rule.process_id):
        await _apply(session, rule, await audit.proposal_with(session, rule))
        rule.status = "active"
        rule.activated_at = datetime.now(UTC)
        await session.commit()
    return _detail(rule)


async def retire(session: AsyncSession, rule_id: int) -> RuleDetail:
    """Retiring a rule can change a past decision just as adding one can, so it goes
    through the same check."""
    rule = await _rule(session, rule_id)
    if rule.status not in ENFORCED:
        raise ConflictError(f"Only an active or blocked rule can be retired (it is {rule.status})")
    await _apply(session, rule, await audit.proposal_without(session, rule))
    rule.status = "retired"
    await session.commit()
    return _detail(rule)
