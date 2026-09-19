"""Norm normalizer: turns a norm in natural language into rules (ADR 0017).

A non-technical person pastes the norm (any language). Each sentence stays one norm rule,
kept exactly as written: the unit the client owns. The normalizer splits it into atomic
checks, in English, each with the decision the norm implies and how it was read; each check
is an ordinary `Rule` (one code, one decision) linked to its norm rule. Nobody reviews it:
the checks are saved like any other rule and compile in the background (ADR 0004), and
every interpretation is kept in the check's `report["norm"]`.

A check's decision is the one the norm names for that failure (`decision_source:
"explicit"`, with the words that name it). When the norm does not name it ("pay only if X"
says nothing about what happens when X fails), the use case's `failed_check_decision`
decides, in code, whatever the model proposed (`"policy"`).
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry, RunContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.core import events
from app.features.agents import compiler, llm
from app.features.processes.model import DecisionType, Process, Symbol
from app.features.rules import service as rules
from app.features.rules.model import NormRule, Rule
from app.features.rules.schemas import RuleIn

MAX_REPAIRS = 2


class Check(BaseModel):
    """One checkable condition of a norm sentence: becomes one `Rule`."""

    text: str  # English, precise, naming symbols and source columns
    type: Literal["requirement", "prohibition"]
    decision: str
    # explicit: the norm names the outcome of this failure (`quote` holds those words);
    # policy: it does not, and the use case's `failed_check_decision` decides.
    decision_source: Literal["explicit", "policy"]
    quote: str = ""
    interpretation: str  # what was decided and why


class Sentence(BaseModel):
    """One sentence of the norm and what the normalizer made of it."""

    number: int
    text: str  # exactly as the client wrote it
    checks: list[Check] = []
    policies: list[str] = []  # statements that are not checkable conditions
    covered: list[int] = []  # ids of active rules that already implement part of it


class Normalization(BaseModel):
    norm_rules: list[Sentence]


class NormIn(BaseModel):
    text: str


class CreatedCheck(Check):
    rule_id: int


class CreatedNormRule(Sentence):
    id: int
    checks: list[CreatedCheck]


class NormOut(BaseModel):
    norm_rules: list[CreatedNormRule]


@dataclass(frozen=True)
class Deps:
    decisions: set[str]
    default: str
    rules: dict[int, str]  # existing active rules: id -> text
    policy: str | None = None  # failed_check_decision: decides every `policy` check


normalizer = Agent(
    None, output_type=Normalization, deps_type=Deps, name="normalizer", retries=MAX_REPAIRS
)


@normalizer.output_validator
def _consistent(ctx: RunContext[Deps], output: Normalization) -> Normalization:
    problems = []
    for s in output.norm_rules:
        for c in s.checks:
            if c.decision_source == "policy" and ctx.deps.policy:
                c.decision = ctx.deps.policy
            elif c.decision_source == "explicit" and not _quoted(c.quote, s.text):
                problems.append(
                    f"check {c.text!r} is `explicit` but its `quote` {c.quote!r} is not words "
                    "of its sentence naming the outcome; quote them, or mark it `policy`"
                )
    checks = [c for s in output.norm_rules for c in s.checks]
    for c in checks:
        if c.decision not in ctx.deps.decisions:
            known = sorted(ctx.deps.decisions)
            problems.append(f"{c.decision!r} is not a decision type ({known})")
        elif c.decision == ctx.deps.default:
            problems.append(
                f"check {c.text!r} decides the default {c.decision!r}: a rule fires to "
                "prevent the default, choose another decision"
            )
    texts = [c.text.strip() for c in checks]
    if len(set(texts)) < len(texts):
        problems.append("check texts must be unique")
    if repeated := set(texts) & {t.strip() for t in ctx.deps.rules.values()}:
        problems.append(f"already active rules, list their ids in `covered`: {sorted(repeated)}")
    if unknown := {i for s in output.norm_rules for i in s.covered} - set(ctx.deps.rules):
        problems.append(f"`covered` names rules that do not exist: {sorted(unknown)}")
    if empty := [s.number for s in output.norm_rules if not (s.checks or s.policies or s.covered)]:
        problems.append(f"norm rules {empty} have no check, policy or covered rule")
    if problems:
        raise ModelRetry("Fix your answer: " + "; ".join(problems))
    return output


def _quoted(quote: str, sentence: str) -> bool:
    def words(text: str) -> str:
        return " ".join(text.casefold().split())

    return bool(quote.strip()) and words(quote) in words(sentence)


def check_policy(policy: str | None, types: Sequence[DecisionType]) -> None:
    """A `failed_check_decision` must be a decision type of the process and never the
    default: a failed check must not pay."""
    if policy is None:
        return
    found = next((t for t in types if t.name == policy), None)
    if found is None:
        known = sorted(t.name for t in types)
        raise ConflictError(f"failed_check_decision {policy!r} is not a decision type ({known})")
    if found.is_default:
        raise ConflictError(
            f"failed_check_decision {policy!r} is the default decision: a failed check "
            "would change nothing"
        )


def context(
    norm: str,
    description: str,
    types: Sequence[DecisionType],
    symbols: Sequence[Symbol],
    sources: compiler.Sources,
    active: Sequence[Rule],
    policy: str | None = None,
) -> str:
    """What the normalizer sees: the norm and everything a rule may use or already says."""
    lines = [
        "Norm:",
        norm.strip(),
        "",
        "Use case description (conventions shared by all its rules):",
        description or "(no description)",
        "",
        "Decision types (name, priority, is_default, requires_human):",
        *(f"- {t.name}, {t.priority}, {t.is_default}, {t.requires_human}" for t in types),
        "",
        "Symbols of each instance (name, type, description):",
        *(f"- {s.name} ({s.type}): {s.description}" for s in symbols),
        "",
        "Sources of truth (columns and 3 sample rows):",
    ]
    for name, rows in sources.items():
        columns = list(dict.fromkeys(c for r in rows for c in r))
        lines.append(f"- {name}: columns {columns}")
        lines += [f"    {json.dumps(r, ensure_ascii=False, default=str)}" for r in rows[:3]]
    if not sources:
        lines.append("- (none)")
    lines += ["", "Active rules (id: text):"]
    lines += [f"- {r.id}: {r.text}" for r in active] or ["- (none)"]
    lines += ["", "Decision of a check whose failure the norm does not name (`policy`):"]
    lines.append(f"- {policy}" if policy else "- (not set: follow the fallbacks)")
    return "\n".join(lines)


async def normalize(
    norm: str,
    description: str,
    types: Sequence[DecisionType],
    symbols: Sequence[Symbol],
    sources: compiler.Sources,
    active: Sequence[Rule],
    setup: llm.Setup | None = None,
) -> tuple[Normalization, llm.Trace]:
    """The normalizer on one norm, without the database."""
    policy = setup.settings.failed_check_decision if setup else None
    check_policy(policy, types)
    deps = Deps(
        decisions={t.name for t in types},
        default=next(t.name for t in types if t.is_default),
        rules={r.id: r.text for r in active},
        policy=policy,
    )
    prompt = context(norm, description, types, symbols, sources, active, policy)
    return await llm.run(
        normalizer,
        "normalizer",
        prompt,
        instructions=llm.prompt("normalizer"),
        setup=setup,
        deps=deps,
    )


async def normalize_norm(session: AsyncSession, process_id: int, norm: str) -> NormOut:
    """Normalize a norm: one norm rule per sentence, each check a `Rule` linked to it,
    with the normalizer's reading in `report["norm"]`."""
    if await session.get(Process, process_id) is None:
        raise NotFoundError(f"Process {process_id} does not exist")
    description, sources, setups = await compiler.read_process(session, process_id)
    types = list(
        await session.scalars(select(DecisionType).where(DecisionType.process_id == process_id))
    )
    symbols = list(await session.scalars(select(Symbol).where(Symbol.process_id == process_id)))
    active = list(
        await session.scalars(
            select(Rule)
            .where(Rule.process_id == process_id, Rule.status == "active")
            .order_by(Rule.id)
        )
    )
    output, trace = await normalize(
        norm, description, types, symbols, sources, active, setups.get("normalizer")
    )
    events.record(
        session,
        "normalize_norm",
        process_id=process_id,
        data={"process_id": process_id, "output": output.model_dump(), **trace.as_data()},
        latency_ms=trace.latency_ms,
        cost=trace.cost,
    )
    created = []
    for sentence in output.norm_rules:
        norm_rule = NormRule(
            process_id=process_id,
            number=sentence.number,
            text=sentence.text,
            policies=sentence.policies,
        )
        session.add(norm_rule)
        await session.flush()
        checks = []
        for check in sentence.checks:
            data = RuleIn(text=check.text, type=check.type, decision=check.decision)
            rule = await session.get(Rule, (await rules.create(session, process_id, data)).id)
            rule.norm_rule_id = norm_rule.id
            reading = {
                "norm_rule": sentence.text,
                "interpretation": check.interpretation,
                "decision_source": check.decision_source,
                "quote": check.quote,
                "policies": sentence.policies,
                "covered": sentence.covered,
            }
            rule.report = {**(rule.report or {}), "norm": reading}
            checks.append(CreatedCheck(**check.model_dump(), rule_id=rule.id))
        created.append(
            CreatedNormRule(
                **sentence.model_dump(exclude={"checks"}), id=norm_rule.id, checks=checks
            )
        )
    await session.commit()
    return NormOut(norm_rules=created)
