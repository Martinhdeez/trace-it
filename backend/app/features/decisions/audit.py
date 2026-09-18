"""What a change to the rules would do to the decisions already taken.

Runs the proposed rule set over the symbols already stored, never re-reading a PDF or the
ERP: the check is fast, free and always gives the same answer. It never changes a past
decision (P14). Adding a rule and retiring one are the same question, asked of a different
proposed set.
"""

import asyncio
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.agents import sandbox
from app.features.decisions.engine import decide_batch
from app.features.decisions.model import ENGINE, Finding
from app.features.decisions.service import (
    _current_sources,
    _instances,
    _latest_decisions,
    _outcomes,
)
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
    """Three groups, because they need three different answers from the manager."""

    unchanged: int
    changes: list[Change]  # the engine decided it, and would now decide otherwise
    conflicts: list[Change]  # a person decided it and the rules disagree, or they cannot decide

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)


async def active_rules(session: AsyncSession, process_id: int) -> list[Rule]:
    return list(
        await session.scalars(
            select(Rule)
            .where(Rule.process_id == process_id, Rule.status == "active")
            .order_by(Rule.id)
        )
    )


async def proposal_with(session: AsyncSession, rule: Rule) -> list[Rule]:
    """The rule set as it would be if `rule` were activated."""
    active = await active_rules(session, rule.process_id)
    return sorted([*active, rule], key=lambda r: r.id)


async def proposal_without(session: AsyncSession, rule: Rule) -> list[Rule]:
    """The rule set as it would be if `rule` were retired. Retiring a rule can change a
    past decision exactly as adding one can, so it is checked the same way."""
    active = await active_rules(session, rule.process_id)
    return [r for r in active if r.id != rule.id]


async def check(session: AsyncSession, process_id: int, proposed: list[Rule]) -> Impact:
    """Decide every already-decided instance again under `proposed` and compare."""
    outcomes = await _outcomes(session, process_id)
    sources = await _current_sources(session, process_id)
    instances = await _instances(session, process_id)
    latest = await _latest_decisions(session, instances)
    symbols = {i.id: {**i.symbols, "_instance": i.name} for i in instances if i.symbols is not None}

    decided = [i for i in instances if latest.get(i.id) is not None and i.symbols is not None]
    cases = [
        (i.symbols, sources, [s for iid, s in symbols.items() if iid != i.id]) for i in decided
    ]  # nothing decided yet, or nothing to decide it with, is skipped
    verdicts = await asyncio.to_thread(
        decide_batch, proposed, outcomes.priorities, outcomes.default, cases, sandbox.run_batch
    )

    unchanged = 0
    changes: list[Change] = []
    conflicts: list[Change] = []
    for instance, verdict in zip(decided, verdicts, strict=True):
        previous = latest[instance.id]
        if verdict.decision == previous.decision:
            unchanged += 1
            continue
        change = Change(
            instance_id=instance.id,
            name=instance.name,
            before=previous.decision,
            after=verdict.decision or "REVIEW",
            previous_author=previous.author,
            reason=verdict.reason,
            decision_id=previous.id,
        )
        # A person's decision is not overruled by a rule, and a rule is not silently
        # dropped because a person disagreed: the manager resolves it (P15). A proposal that
        # cannot decide an instance (REVIEW) blocks activation the same way.
        blocking = previous.author != ENGINE or verdict.decision is None
        (conflicts if blocking else changes).append(change)

    return Impact(unchanged=unchanged, changes=changes, conflicts=conflicts)


async def record_findings(
    session: AsyncSession, process_id: int, impact: Impact, rule: Rule
) -> list[Finding]:
    """Record the past decisions the adopted change says were wrong.

    Only for outcomes nobody was asked to look at: an instance that sat in the human queue
    harmed nothing, whereas one the engine concluded by itself was acted on. The finding is
    a notice, never a correction — the past is not edited, and what to do about it (claim
    the money back, pay what is owed) happens outside this system (P14).
    """
    outcomes = await _outcomes(session, process_id)
    findings = [
        Finding(
            decision_id=change.decision_id,
            rule_id=rule.id,
            type="different_decision",
            detail=f"{change.before} -> {change.after}: {change.reason}",
        )
        for change in impact.changes
        if change.before not in outcomes.human
    ]
    session.add_all(findings)
    return findings
