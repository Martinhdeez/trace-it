"""The decision engine: every active rule runs, nobody chooses which (ADR 0002, 0014).

Pure function. No database, no LLM, no clock, no network: the same inputs always give the
same verdict, so a past decision can be replayed from its stored symbols.

Every instance gets a decision. When a required symbol is missing, or a rule cannot be
trusted (its code failed, or two decision types tie), the verdict is the process's
escalation type with the reason: a person looks at it, and the default is never produced
while a rule is unevaluated.
"""

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from app.features.rules.model import Rule

DatasetEntry = tuple[int, dict[str, Any]]  # (instance key, {symbol: value})
Sources = dict[str, list[dict[str, Any]]]
# The sandbox's `run_dataset`: runs `evaluate(instance, sources, others)` from `code` on every
# requested instance in one subprocess, deriving each one's `others` from the population.
# Returns, per instance, {"fires": bool, "reason": str} or that instance's exception; raises
# when the whole batch fails.
RunDataset = Callable[[str, list[DatasetEntry], Sources, list[DatasetEntry]], list[Any]]


@dataclass(frozen=True)
class Outcomes:
    """What a process can conclude: the priority of each decision type, the one that applies
    when no rule fires, and the one that sends the case to a person. An instance missing a
    `required` symbol always goes to that person, whatever the rules say."""

    priorities: dict[str, int]
    default: str
    escalate: str
    required: tuple[str, ...] = ()


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


def _read(answer: Any) -> tuple[bool, str]:
    """An instance's answer, or raise if it is an error or malformed."""
    if isinstance(answer, BaseException):
        raise answer
    fires = answer["fires"]
    if type(fires) is not bool:
        raise TypeError(f"fires is not a bool: {fires!r}")
    return fires, str(answer.get("reason", ""))


def _run_rule(
    rule: Rule,
    instances: list[DatasetEntry],
    sources: Sources,
    population: list[DatasetEntry],
    run_dataset: RunDataset,
) -> list[RuleResult]:
    """One rule over every instance. A whole-batch failure is that error for every one."""
    report = rule.report or {}
    needs_data = report.get("needs_data")
    if not rule.code and needs_data:
        missing = ", ".join(needs_data.get("missing") or []) or "data"
        reason = f"RULE_NEEDS_DATA {rule.id}: missing {missing}"
        return [RuleResult(rule.id, rule.hash, None, reason)] * len(instances)
    if not rule.code and report.get("error"):  # its compilation failed (ADR 0020)
        reason = f"RULE_COMPILE_FAILED {rule.id}: {report['error'][:200]}"
        return [RuleResult(rule.id, rule.hash, None, reason)] * len(instances)
    try:
        if not rule.code:
            raise ValueError("rule is active without code")
        answers = run_dataset(rule.code, instances, sources, population)
        if len(answers) != len(instances):
            raise ValueError(f"{len(answers)} results for {len(instances)} instances")
    except Exception as error:  # noqa: BLE001 - any failure is the same to the engine
        answers = [error] * len(instances)
    results = []
    for answer in answers:
        try:
            fires, reason = _read(answer)
        except Exception as error:  # noqa: BLE001
            failure = f"RULE_ERROR {rule.id}: {type(error).__name__}: {error}"
            results.append(RuleResult(rule.id, rule.hash, None, failure))
            continue
        results.append(RuleResult(rule.id, rule.hash, fires, reason))
    return results


def _missing(outcomes: Outcomes, symbols: dict[str, Any]) -> list[str]:
    """Required symbols absent, None or blank: what a rule would read as "not extracted"."""
    return [s for s in outcomes.required if (v := symbols.get(s)) is None or not str(v).strip()]


def _combine(
    rules: Sequence[Rule],
    results: list[RuleResult],
    outcomes: Outcomes,
    rules_hash: str,
    missing: list[str],
) -> Verdict:
    """A required symbol missing -> escalate, whatever the rules answered. No rule fires ->
    the default. Several fire -> the highest priority. A rule that could not be evaluated,
    or a tie between types -> escalate with the reason."""

    def verdict(decision: str, reason: str) -> Verdict:
        return Verdict(decision, reason, results, rules_hash)

    if missing:
        return verdict(outcomes.escalate, f"MISSING_DATA: {', '.join(missing)}")

    failures = [r.reason for r in results if r.fires is None]
    if failures:
        return verdict(outcomes.escalate, " | ".join(failures))

    fired = [(rule, r) for rule, r in zip(rules, results, strict=True) if r.fires]
    if not fired:
        return verdict(outcomes.default, "")

    highest = max(outcomes.priorities[rule.decision] for rule, _ in fired)
    winners = [(rule, r) for rule, r in fired if outcomes.priorities[rule.decision] == highest]
    decisions = sorted({rule.decision for rule, _ in winners})
    if len(decisions) > 1:
        tie = f"RULE_CONFLICT: {', '.join(decisions)} share priority {highest}"
        return verdict(outcomes.escalate, tie)
    # The rule's own reason code; its text stays on the rule, joined by `rule_id`.
    return verdict(decisions[0], " | ".join(r.reason or rule.text for rule, r in winners))


def decide(
    rules: Sequence[Rule],
    outcomes: Outcomes,
    instances: list[DatasetEntry],
    sources: Sources,
    population: list[DatasetEntry],
    run_dataset: RunDataset,
) -> list[Verdict]:
    """Apply every rule to every instance. Each rule's code runs once, over all the instances
    together; the shared sources and population cross to the sandbox once per rule."""
    if not instances:
        return []
    by_rule = [_run_rule(rule, instances, sources, population, run_dataset) for rule in rules]
    rules_hash = hash_rules(rules)
    return [
        _combine(rules, [r[k] for r in by_rule], outcomes, rules_hash, _missing(outcomes, values))
        for k, (_, values) in enumerate(instances)
    ]
