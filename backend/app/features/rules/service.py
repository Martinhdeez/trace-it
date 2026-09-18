import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.features.agents import compiler
from app.features.decisions import audit
from app.features.processes.model import DecisionType, Symbol
from app.features.processes.service import get as get_process
from app.features.rules.model import Rule
from app.features.rules.schemas import RuleDetail, RuleIn, RuleOut


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


async def get(session: AsyncSession, rule_id: int) -> RuleDetail:
    return _detail(await _rule(session, rule_id))


async def create(session: AsyncSession, process_id: int, data: RuleIn) -> RuleDetail:
    await get_process(session, process_id)
    if not await session.get(DecisionType, (process_id, data.decision)):
        raise ConflictError(f"{data.decision!r} is not a decision type of this process")
    rule = Rule(process_id=process_id, **data.model_dump())
    session.add(rule)
    await session.commit()
    return _detail(rule)


async def compile_rule(session: AsyncSession, rule_id: int) -> RuleDetail:
    rule = await _rule(session, rule_id)
    if rule.status != "draft":
        raise ConflictError(f"Only a draft rule can be compiled (it is {rule.status})")
    symbols = list(
        await session.scalars(select(Symbol).where(Symbol.process_id == rule.process_id))
    )
    result = await compiler.compile_rule(session, rule, symbols)
    rule.code_a, rule.code_b = result.code_a, result.code_b
    rule.tests_a, rule.tests_b = result.tests_a, result.tests_b
    rule.report = result.report
    rule.hash = hashlib.sha256(
        "\0".join([rule.text, rule.code_a, rule.code_b]).encode()
    ).hexdigest()
    await session.commit()
    return _detail(rule)


async def _apply(session: AsyncSession, rule: Rule, proposed: list[Rule]) -> None:
    """Check a rule change against every decision already taken, then adopt it.

    The past is never rewritten. What the change says about it is recorded as findings for
    the manager to act on outside this system (P14). A change that would contradict a
    decision a person took is refused until they resolve it (P15).
    """
    impact = await audit.check(session, rule.process_id, proposed)
    if impact.has_conflicts:
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
        if rule.status == "active"
        else await audit.proposal_with(session, rule)
    )
    return await audit.check(session, rule.process_id, proposed)


async def activate(session: AsyncSession, rule_id: int) -> RuleDetail:
    """A rule only enters the process when its validation found no discrepancy (P21)."""
    rule = await _rule(session, rule_id)
    if rule.status != "draft":
        raise ConflictError(f"Only a draft rule can be activated (it is {rule.status})")
    if not (rule.report or {}).get("valid"):
        raise ConflictError("The rule has unresolved discrepancies or is not compiled")
    await _apply(session, rule, await audit.proposal_with(session, rule))
    rule.status = "active"
    rule.activated_at = datetime.now(UTC)
    await session.commit()
    return _detail(rule)


async def retire(session: AsyncSession, rule_id: int) -> RuleDetail:
    """Retiring a rule can change a past decision just as adding one can, so it goes
    through the same check."""
    rule = await _rule(session, rule_id)
    if rule.status != "active":
        raise ConflictError(f"Only an active rule can be retired (it is {rule.status})")
    await _apply(session, rule, await audit.proposal_without(session, rule))
    rule.status = "retired"
    await session.commit()
    return _detail(rule)
