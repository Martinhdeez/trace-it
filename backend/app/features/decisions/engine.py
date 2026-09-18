"""The decision engine: every active rule runs, nobody chooses which (P7).

Pure function. No database, no LLM, no clock, no network: the same inputs always give the
same verdict, so a past decision can be replayed from its stored symbols.

Fail closed (ADR 0004, 0009, 0014): when any rule result cannot be trusted, the verdict has
no decision and the instance goes to REVIEW with the reason. Our doubt is never mapped to a
decision type, and the default type is never produced while a rule is unevaluated.
"""

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from app.features.rules.model import Rule

Case = tuple[dict[str, Any], dict[str, list[dict[str, Any]]], list[dict[str, Any]]]
# The sandbox's `run_batch`: runs `evaluate(instance, sources, others)` from `code` on every
# case in one subprocess. Returns, per case, {"fires": bool, "reason": str} or the exception
# for that case; raises when the whole batch fails.
RunBatch = Callable[[str, list[Case]], list[Any]]


@dataclass(frozen=True)
class RuleResult:
    """What one rule answered. `fires` is None when the rule could not be trusted: it failed,
    or its two codes disagree. `reason` is code A's; `reason_b` is code B's."""

    rule_id: int
    hash: str | None
    fires: bool | None
    reason: str
    reason_b: str | None = None


@dataclass(frozen=True)
class Verdict:
    """`decision` is None when the instance must go to REVIEW; `reason` then says why."""

    decision: str | None
    reason: str
    results: list[RuleResult]
    rules_hash: str


def hash_rules(rules: Sequence[Rule]) -> str:
    """Identifies the rule set a decision was taken with."""
    parts = sorted(f"{r.id}:{r.hash}" for r in rules)
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()


def _read(answer: Any) -> tuple[bool, str]:
    """A case's answer, or raise if it is an error or malformed."""
    if isinstance(answer, BaseException):
        raise answer
    fires = answer["fires"]
    if type(fires) is not bool:
        raise TypeError(f"fires is not a bool: {fires!r}")
    return fires, str(answer.get("reason", ""))


def _run_code(code: str | None, cases: list[Case], run_batch: RunBatch) -> list[Any]:
    """One code over every case. A whole-batch failure becomes that error for every case."""
    try:
        if not code:
            raise ValueError("rule is active without both codes")
        answers = run_batch(code, cases)
        if len(answers) != len(cases):
            raise ValueError(f"{len(answers)} results for {len(cases)} cases")
        return answers
    except Exception as error:  # noqa: BLE001 - any failure is the same to the engine
        return [error] * len(cases)


def _compare(rule: Rule, answers_a: list[Any], answers_b: list[Any]) -> list[RuleResult]:
    """Codes A and B of one rule, compared case by case."""
    results: list[RuleResult] = []
    for a, b in zip(answers_a, answers_b, strict=True):
        try:
            fires_a, reason_a = _read(a)
            fires_b, reason_b = _read(b)
        except Exception as error:  # noqa: BLE001
            failure = f"RULE_ERROR {rule.id}: {type(error).__name__}: {error}"
            results.append(RuleResult(rule.id, rule.hash, None, failure))
            continue
        if fires_a != fires_b:
            failure = f"CODES_DISAGREE {rule.id}: A fires={fires_a}, B fires={fires_b}"
            results.append(RuleResult(rule.id, rule.hash, None, failure, reason_b))
            continue
        results.append(RuleResult(rule.id, rule.hash, fires_a, reason_a, reason_b))
    return results


def _combine(
    rules: Sequence[Rule],
    results: list[RuleResult],
    priorities: dict[str, int],
    default: str,
    rules_hash: str,
) -> Verdict:
    """No rule fires -> `default`. Several fire -> the type with the highest priority."""

    def verdict(decision: str | None, reason: str) -> Verdict:
        return Verdict(decision, reason, results, rules_hash)

    failures = [r.reason for r in results if r.fires is None]
    if failures:
        return verdict(None, " | ".join(failures))

    fired = [rule for rule, r in zip(rules, results, strict=True) if r.fires]
    unknown = sorted({r.decision for r in fired if r.decision not in priorities})
    if unknown:
        return verdict(None, f"UNKNOWN_DECISION: {', '.join(unknown)}")

    if not fired:
        return verdict(default, "")

    highest = max(priorities[r.decision] for r in fired)
    winners = [r for r in fired if priorities[r.decision] == highest]
    decisions = sorted({r.decision for r in winners})
    if len(decisions) > 1:
        return verdict(None, f"RULE_CONFLICT: {', '.join(decisions)} share priority {highest}")

    return verdict(decisions[0], " | ".join(r.text for r in winners))


def decide_batch(
    rules: Sequence[Rule],
    priorities: dict[str, int],
    default: str,
    cases: list[Case],
    run_batch: RunBatch,
) -> list[Verdict]:
    """Apply every rule in `rules` to every case. Each code of each rule runs once, over all
    the cases together; a case's error only affects that case, a whole-batch failure every
    case of that batch."""
    if not cases:
        return []
    by_rule = [
        _compare(
            rule, _run_code(rule.code_a, cases, run_batch), _run_code(rule.code_b, cases, run_batch)
        )
        for rule in rules
    ]
    rules_hash = hash_rules(rules)
    return [
        _combine(rules, [r[k] for r in by_rule], priorities, default, rules_hash)
        for k in range(len(cases))
    ]


def decide(
    rules: Sequence[Rule],
    priorities: dict[str, int],
    default: str,
    instance: dict[str, Any],
    sources: dict[str, list[dict[str, Any]]],
    others: list[dict[str, Any]],
    run_batch: RunBatch,
) -> Verdict:
    """`decide_batch` for a single instance."""
    [verdict] = decide_batch(rules, priorities, default, [(instance, sources, others)], run_batch)
    return verdict
