"""What a change to the rules would do to the decisions already taken.

Runs the proposed rule set over the symbols already stored, never re-reading a PDF or the
ERP: the check is fast, free and always gives the same answer. It never changes a past
decision (ADR 0008). Adding a rule and retiring one are the same question, asked of a
different proposed set.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.decisions import service
from app.features.decisions.model import ENGINE, Decision, Finding
from app.features.rules.model import Rule


@dataclass(frozen=True)
class Change:
    instance_id: int
    name: str
    before: str
    after: str
    previous_author: str
    reason: str
    decision_id: int


@dataclass(frozen=True)
class Impact:
    """Two groups, because they need two different answers from the manager."""

    unchanged: int
    changes: list[Change]  # the engine decided it, and would now decide otherwise
    # a person decided it, and the rules would now decide otherwise than the engine did
    # and than that person; one that now agrees with the person is neither (R01)
    conflicts: list[Change]


async def proposal_with(session: AsyncSession, rule: Rule) -> list[Rule]:
    """The rule set as it would be if `rule` were activated."""
    active = await service.active_rules(session, rule.process_id)
    return sorted([*active, rule], key=lambda r: r.id)


async def proposal_without(session: AsyncSession, rule: Rule) -> list[Rule]:
    """The rule set as it would be if `rule` were retired. Retiring a rule can change a
    past decision exactly as adding one can, so it is checked the same way."""
    active = await service.active_rules(session, rule.process_id)
    return [r for r in active if r.id != rule.id]


async def check(session: AsyncSession, process_id: int, proposed: list[Rule]) -> Impact:
    """Decide every already-decided instance again under `proposed` and compare."""
    instances = await service.instances_of(session, process_id)
    latest = await service.latest_decisions(session, instances)
    # nothing decided yet, or nothing to decide it with, is skipped
    decided = [i for i in instances if latest.get(i.id) is not None and i.symbols is not None]
    verdicts = await service.decide_all(session, process_id, proposed, decided)

    engine = await _engine_decisions(session, decided)

    unchanged = 0
    changes: list[Change] = []
    conflicts: list[Change] = []
    for instance, verdict in zip(decided, verdicts, strict=True):
        # R01: the baseline is the engine's last word, not a person's resolution.
        last = latest[instance.id]
        previous = engine.get(instance.id, last)
        if verdict.decision == previous.decision:
            unchanged += 1
            continue
        if last.author != ENGINE:
            if verdict.decision == last.decision:  # the rules now agree with the person
                unchanged += 1
                continue
            previous = last
        change = Change(
            instance_id=instance.id,
            name=instance.name,
            before=previous.decision,
            after=verdict.decision,
            previous_author=previous.author,
            reason=verdict.reason,
            decision_id=previous.id,
        )
        # A person's decision is not overruled by a rule, and a rule is not silently
        # dropped because a person disagreed: the manager resolves it.
        (conflicts if previous.author != ENGINE else changes).append(change)

    return Impact(unchanged=unchanged, changes=changes, conflicts=conflicts)


async def _engine_decisions(session: AsyncSession, instances) -> dict[int, Decision]:
    rows = await session.scalars(
        select(Decision)
        .where(Decision.instance_id.in_([i.id for i in instances]), Decision.author == ENGINE)
        .order_by(Decision.id)
    )
    return {row.instance_id: row for row in rows}


async def record_findings(
    session: AsyncSession, process_id: int, impact: Impact, rule: Rule
) -> list[Finding]:
    """Record the past decisions the adopted change says were wrong.

    Only for outcomes nobody was asked to look at: an instance that sat in the human queue
    harmed nothing, whereas one the engine concluded by itself was acted on. The finding is
    a notice, never a correction: the past is not edited, and what to do about it (claim
    the money back, pay what is owed) happens outside this system (ADR 0008).
    """
    human = await service.human_types(session, process_id)
    findings = [
        Finding(
            decision_id=change.decision_id,
            rule_id=rule.id,
            type="different_decision",
            detail=f"{change.before} -> {change.after}: {change.reason}",
        )
        for change in impact.changes
        if change.before not in human
    ]
    session.add_all(findings)
    return findings
