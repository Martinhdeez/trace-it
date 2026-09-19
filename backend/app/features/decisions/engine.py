"""The decision engine: every active rule runs, nobody chooses which (ADR 0002, 0014).

Pure function. No database, no LLM, no clock, no network: the same inputs always give the
same verdict, so a past decision can be replayed from its stored symbols.

Every instance gets a decision. When a required symbol is missing, or a rule cannot be
trusted (its code failed, or two decision types tie), the verdict is the process's
escalation type with the reason: a person looks at it, and the default is never produced
while a rule is unevaluated. A scan escalates too when its readers did not confirm a required
symbol, or when the rules would reject it (ADR 0025). A rule that reads a source that is
down is not run; the case escalates unless the other rules already decide it (ADR 0028).
"""

import hashlib
from collections.abc import Callable, Collection, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
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
SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


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
    down: Sequence[str] = (),
) -> list[RuleResult]:
    """One rule over every instance. A whole-batch failure is that error for every one.
    `down`: the sources this rule reads that are unavailable."""
    if down:  # a source it reads could not be synced: never run it on an older snapshot
        reason = f"SOURCE_UNAVAILABLE {rule.id}: {', '.join(down)}"
        return [RuleResult(rule.id, rule.hash, None, reason)] * len(instances)
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
    scan: Collection[str] | None = None,
) -> Verdict:
    """A required symbol missing -> escalate, whatever the rules answered. No rule fires ->
    the default. Several fire -> the highest priority. A rule that could not be evaluated,
    or a tie between types -> escalate with the reason.

    `scan` is None for a document with a text layer; for a scan, the symbols its readers did
    not confirm. A required one among them -> escalate, whatever the rules answered. A scan
    the rules would reject -> escalate: a mismatch on OCR data may be a misread (ADR 0025).

    A rule that reads a down source is `SOURCE_UNAVAILABLE`, not run. Order (ADR 0028):
    MISSING_DATA, UNVERIFIED_DATA, any other rule failure, then the rules that ran if no
    unrun rule could outrank or tie their outcome (RULE_CONFLICT, SCAN_REVIEW or the
    rejection), else SOURCE_UNAVAILABLE: <sources>; last, the default."""

    def verdict(decision: str, reason: str) -> Verdict:
        return Verdict(decision, reason, results, rules_hash)

    if missing:
        return verdict(outcomes.escalate, f"MISSING_DATA: {', '.join(missing)}")

    unconfirmed = [s for s in outcomes.required if s in (scan or ())]
    if unconfirmed:
        return verdict(outcomes.escalate, f"UNVERIFIED_DATA: {', '.join(unconfirmed)}")

    failures = [r.reason for r in results if r.fires is None]
    unavailable = [
        (rule, r.reason.split(": ", 1)[1])
        for rule, r in zip(rules, results, strict=True)
        if r.fires is None and r.reason.startswith(SOURCE_UNAVAILABLE)
    ]
    if len(failures) > len(unavailable):
        return verdict(outcomes.escalate, " | ".join(failures))

    fired = [(rule, r) for rule, r in zip(rules, results, strict=True) if r.fires]
    highest = max((outcomes.priorities[rule.decision] for rule, _ in fired), default=None)
    if unavailable:
        # The rules that ran decide only when no rule that could not run could have
        # outranked their outcome, or tied it with another type (ADR 0028).
        top = {rule.decision for rule, _ in fired if outcomes.priorities[rule.decision] == highest}
        decided = highest is not None and all(
            outcomes.priorities[rule.decision] < highest
            or (outcomes.priorities[rule.decision] == highest and top == {rule.decision})
            for rule, _ in unavailable
        )
        if not decided:
            names = sorted({n for _, down in unavailable for n in down.split(", ")})
            return verdict(outcomes.escalate, f"{SOURCE_UNAVAILABLE}: {', '.join(names)}")
    if not fired:
        return verdict(outcomes.default, "")

    winners = [(rule, r) for rule, r in fired if outcomes.priorities[rule.decision] == highest]
    decisions = sorted({rule.decision for rule, _ in winners})
    if len(decisions) > 1:
        tie = f"RULE_CONFLICT: {', '.join(decisions)} share priority {highest}"
        return verdict(outcomes.escalate, tie)
    # The rule's own reason code; its text stays on the rule, joined by `rule_id`.
    reason = " | ".join(r.reason or rule.text for rule, r in winners)
    # ponytail: always the escalation type; a process setting (`scan_rejection_decision`)
    # when a process wants another outcome for rejected scans.
    if scan is not None and decisions[0] not in (outcomes.default, outcomes.escalate):
        return verdict(outcomes.escalate, f"SCAN_REVIEW: {reason}")
    return verdict(decisions[0], reason)


def decide(
    rules: Sequence[Rule],
    outcomes: Outcomes,
    instances: list[DatasetEntry],
    sources: Sources,
    population: list[DatasetEntry],
    run_dataset: RunDataset,
    scans: Mapping[int, Collection[str]] | None = None,
    down: Mapping[int, Sequence[str]] | None = None,
    rule_workers: int = 1,
) -> list[Verdict]:
    """Apply every rule to every instance. Each rule's code runs once, over all the instances
    together; the shared sources and population cross to the sandbox once per rule.
    `scans`: the instances read from a scan, not a text layer, each with the symbols its
    readers did not confirm. `down`: per rule id, the unavailable sources it reads; the
    caller finds them, the engine only honours them (ADR 0028)."""
    if not instances:
        return []
    workers = max(1, min(max(1, rule_workers), len(rules)))

    def run_rule(rule: Rule) -> list[RuleResult]:
        return _run_rule(
            rule, instances, sources, population, run_dataset, (down or {}).get(rule.id, ())
        )

    if workers == 1:
        by_rule = [run_rule(rule) for rule in rules]
    else:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="decision-rule") as pool:
            futures = [pool.submit(copy_context().run, run_rule, rule) for rule in rules]
            by_rule = [future.result() for future in futures]
    rules_hash = hash_rules(rules)
    return [
        _combine(
            rules,
            [r[k] for r in by_rule],
            outcomes,
            rules_hash,
            _missing(outcomes, values),
            (scans or {}).get(key),
        )
        for k, (key, values) in enumerate(instances)
    ]
