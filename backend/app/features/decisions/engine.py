"""The decision engine: every active rule runs, nobody chooses which (P7).

Pure function. No database, no LLM, no clock, no network: the same inputs always give the
same verdict, so a past decision can be replayed from its stored symbols.
"""

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from app.features.rules.model import Rule

# The sandbox: runs `evaluate(instance, sources, others)` from `code` and returns
# {"fires": bool, "reason": str}. Raises on any error, timeout or malformed result.
Run = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class RuleResult:
    """What one rule answered. `fires` is None when the rule could not be evaluated."""

    rule_id: int
    hash: str | None
    fires: bool | None
    reason: str


@dataclass(frozen=True)
class Verdict:
    decision: str
    reason: str
    results: list[RuleResult]
    rules_hash: str


def hash_rules(rules: Sequence[Rule]) -> str:
    """Identifies the rule set a decision was taken with."""
    parts = sorted(f"{r.id}:{r.hash}" for r in rules)
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()


def decide(
    rules: Sequence[Rule],
    priorities: dict[str, int],
    default: str,
    escalate: str,
    instance: dict[str, Any],
    sources: dict[str, list[dict[str, Any]]],
    others: list[dict[str, Any]],
    run: Run,
) -> Verdict:
    """Apply every rule in `rules` to one instance.

    No rule fires -> `default`. Several fire -> the outcome with the highest priority.
    A rule that fails, or a tie between two different outcomes, is sent to a person as
    `escalate`: the engine never decides without a rule it could not evaluate.
    """
    results: list[RuleResult] = []
    failures: list[str] = []
    fired: list[Rule] = []

    for rule in rules:
        try:
            answer = run(rule.code_a, instance, sources, others)
            fires, reason = bool(answer["fires"]), str(answer.get("reason", ""))
        except Exception as error:  # noqa: BLE001 - any failure is the same to the engine
            failure = f"RULE_ERROR {rule.id}: {type(error).__name__}: {error}"
            results.append(RuleResult(rule.id, rule.hash, None, failure))
            failures.append(failure)
            continue

        results.append(RuleResult(rule.id, rule.hash, fires, reason))
        if fires:
            fired.append(rule)

    rules_hash = hash_rules(rules)

    def verdict(decision: str, reason: str) -> Verdict:
        return Verdict(decision, reason, results, rules_hash)

    if failures:
        return verdict(escalate, " | ".join(failures))

    unknown = [r.decision for r in fired if r.decision not in priorities]
    if unknown:
        return verdict(escalate, f"UNKNOWN_DECISION: {', '.join(sorted(unknown))}")

    if not fired:
        return verdict(default, "")

    highest = max(priorities[r.decision] for r in fired)
    winners = [r for r in fired if priorities[r.decision] == highest]
    decisions = {r.decision for r in winners}
    if len(decisions) > 1:
        return verdict(
            escalate, f"RULE_CONFLICT: {', '.join(sorted(decisions))} with the same priority"
        )

    return verdict(winners[0].decision, " | ".join(r.text for r in winners))
