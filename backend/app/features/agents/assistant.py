"""Escalation assistant: suggests a decision, its reasoning and a new rule; after a person
resolved the case, `suggest_rule` amends the escalation rule that fired (ADR 0035).

The LLM never decides anything in the pipeline (ADR 0002). This is only a suggestion shown
to a person, who then resolves the case and, if they want, adds the proposed rule (which is
compiled and validated like any other rule)."""

import json
import re
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext
from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.core import events
from app.features.agents import llm
from app.features.decisions.model import ENGINE, Decision
from app.features.ingestion.model import File, Instance
from app.features.ingestion.symbols import flatten_symbols
from app.features.processes.model import DecisionType, Process
from app.features.proposals.model import ManagerProposal
from app.features.rules.model import Rule
from app.features.use_cases import service as use_cases
from app.features.use_cases.model import UseCase

MAX_TEXT = 12_000  # chars of the file's text sent to the model
MAX_RESOLUTIONS = 10


# Hard limits: the manager reads this on a queue, so no essays. Characters are capped in
# the schema; sentences and single lines are checked by the output validators.
LINE = 180  # one line
SHORT = 320  # at most two short sentences
RULE = 600  # one rule, in English (the longest rule of the invoice pack is 423)


class Option(BaseModel):
    decision: str
    # one line in Spanish: what happens and under which rule ("Se paga si se añade la regla:
    # ...; casos como este pasarían a PAGAR", "No se paga por la regla 7: ...")
    consequence: str = Field(max_length=LINE)
    # English: the rule that justifies this decision, new or an amendment of the escalating
    # one; or "Rule <id>" for an active rule that already gives it. None only on no_rule_reason
    rule: str | None = Field(default=None, max_length=RULE)


class Suggestion(BaseModel):
    decision: str  # the proposed one of `options`
    reasoning: str = Field(max_length=SHORT)
    why: list[Annotated[str, Field(max_length=LINE)]] = Field(min_length=1, max_length=2)
    options: list[Option] = Field(min_length=1)  # every final decision type, one each
    evidence: list[str] = Field(min_length=1, max_length=6)  # references from `evidence_refs`
    # rule text, to be compiled like any other rule if accepted; None with `no_rule_reason`
    proposed_rule: str | None = Field(default=None, max_length=RULE)
    proposed_type: Literal["requirement", "prohibition"] | None = None
    # in Spanish: why no rule should decide cases like this one (a person must always look)
    no_rule_reason: str | None = Field(default=None, max_length=SHORT)


def sentences(text: str) -> int:
    return len(re.findall(r"[.!?](?=\s|$)", text.strip())) or 1


def too_long(**texts: tuple[str | None, int]) -> None:
    """ModelRetry naming every text over its sentence limit, or on more than one line."""
    wrong = [
        f"{name} has {sentences(text)} sentences (max {most})"
        if most > 1
        else f"{name} must be one line and one sentence"
        for name, (text, most) in texts.items()
        if text and (sentences(text) > most or (most == 1 and "\n" in text.strip()))
    ]
    if wrong:
        raise ModelRetry("Be concise: " + "; ".join(wrong))


@dataclass(frozen=True)
class Deps:
    decision_types: list[str]
    final_types: list[str]  # the ones that close a case: every option
    references: set[str]


# Its platform prompt is `prompts/assistant.md`; the use case adds guidance and model.
assistant = Agent(None, output_type=Suggestion, deps_type=Deps, name="assistant", retries=2)


@assistant.output_validator
def _known_decision(ctx: RunContext[Deps], suggestion: Suggestion) -> Suggestion:
    if suggestion.decision not in ctx.deps.decision_types:
        raise ModelRetry(
            f"decision {suggestion.decision!r} is not one of {ctx.deps.decision_types}"
        )
    options = [o.decision for o in suggestion.options]
    if sorted(options) != sorted(ctx.deps.final_types):
        raise ModelRetry(f"options must be exactly one per type of {ctx.deps.final_types}")
    if suggestion.decision not in options:
        raise ModelRetry(
            f"decision must be one of the options {options}, also with no_rule_reason: "
            "that a person must always decide goes in no_rule_reason, not in decision"
        )
    unknown = set(suggestion.evidence) - ctx.deps.references
    if unknown:
        raise ModelRetry(f"cite only references in evidence_refs: {sorted(unknown)}")
    if suggestion.no_rule_reason:
        if suggestion.proposed_rule:
            raise ModelRetry("with no_rule_reason, proposed_rule must be null")
    elif not (suggestion.proposed_rule and suggestion.proposed_type):
        raise ModelRetry("give proposed_rule and proposed_type, or no_rule_reason")
    elif missing := [o.decision for o in suggestion.options if not o.rule]:
        raise ModelRetry(f"every option needs the rule that justifies it: {missing}")
    too_long(
        reasoning=(suggestion.reasoning, 2),
        no_rule_reason=(suggestion.no_rule_reason, 2),
        **{f"why[{i}]": (w, 1) for i, w in enumerate(suggestion.why)},
        **{f"{o.decision}.consequence": (o.consequence, 1) for o in suggestion.options},
    )
    return suggestion


async def _context(session: AsyncSession, instance: Instance) -> tuple[dict[str, Any], list[str]]:
    latest = await session.scalar(
        select(Decision)
        .where(Decision.instance_id == instance.id)
        .order_by(Decision.id.desc())
        .limit(1)
    )
    pid = instance.process_id
    all_types = list(
        await session.scalars(
            select(DecisionType)
            .where(DecisionType.process_id == pid)
            .order_by(DecisionType.priority.desc())
        )
    )
    from app.features.processes.schemas import DecisionTypeIO
    from app.features.versions.configuration import rules as frozen_rules
    from app.features.versions.model import ProcessVersion

    version = (
        await session.get(ProcessVersion, latest.version_id)
        if latest and latest.version_id
        else None
    )
    if version:
        all_types = [
            DecisionTypeIO.model_validate(t) for t in version.snapshot["process"]["decision_types"]
        ]
    types = [t.name for t in all_types]
    human = [t.name for t in all_types if t.requires_human]
    if not (latest and latest.decision in human):
        raise ConflictError(f"Instance {instance.id} is not escalated")

    rules = {r.id: r for r in await session.scalars(select(Rule).where(Rule.process_id == pid))}
    if version:
        rules = {r.id: r for r in frozen_rules(version.snapshot)}
    file = await session.get(File, instance.file_hash)
    resolutions = await session.execute(
        select(Decision, Instance.symbols)
        .join(Instance, Decision.instance_id == Instance.id)
        .where(Instance.process_id == pid, Decision.author != ENGINE)
        .order_by(Decision.id.desc())
        .limit(MAX_RESOLUTIONS)
    )

    process = await session.get(Process, pid)
    use_case = await session.get(UseCase, process.use_case_id)
    fired = [r for r in latest.results if r.get("fires")]
    context = {
        # conventions every rule of the process follows; the proposed rule must too
        "version_id": version.id if version else None,
        "use_case_description": version.snapshot["process"]["description"]
        if version
        else use_case.description,
        "decision_types": types,
        "human_decision_types": human,
        "case": {
            "name": instance.name,
            "symbols": instance.symbols or {},
            "file_text": ((file.text if file else None) or "")[:MAX_TEXT],
        },
        "escalation": {
            "current_decision": latest.decision,
            "reason": latest.reason,
            "fired_rules": [
                {
                    "id": r.get("rule_id"),
                    "reason": r.get("reason"),
                    "text": rules[r["rule_id"]].text if r.get("rule_id") in rules else None,
                    "decision": rules[r["rule_id"]].decision if r.get("rule_id") in rules else None,
                }
                for r in fired
            ],
        },
        "active_rules": [
            {"id": r.id, "text": r.text, "type": r.type, "decision": r.decision}
            for r in rules.values()
            if r.status == "active"
        ],
        "human_resolutions": [
            {
                "ref": f"resolution:{d.id}",
                "symbols": flatten_symbols(symbols or {}),
                "decision": d.decision,
                "author": d.author,
                "reason": d.reason,
            }
            for d, symbols in resolutions
        ],
    }
    context["evidence_refs"] = sorted(
        {f"symbol:{name}" for name in instance.symbols or {}}
        | {f"rule:{r['id']}" for r in context["escalation"]["fired_rules"] if r["id"]}
        | {r["ref"] for r in context["human_resolutions"]}
        | ({"file"} if context["case"]["file_text"] else set())
        | {"escalation"}
    )
    return context, types


async def suggest(session: AsyncSession, instance_id: int) -> Suggestion:
    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise NotFoundError(f"Instance {instance_id} does not exist")
    links = {"instance_id": instance_id, "process_id": instance.process_id}
    with events.span("suggest_escalation", **links) as span:
        context, types = await _context(session, instance)
        prompt = json.dumps(context, ensure_ascii=False, default=str)
        process = await session.get(Process, instance.process_id)
        from app.features.versions.configuration import setups
        from app.features.versions.model import ProcessVersion

        version = (
            await session.get(ProcessVersion, context["version_id"])
            if context["version_id"]
            else None
        )
        setup = (
            setups(version.snapshot)
            if version
            else await use_cases.setups(session, process.use_case_id)
        ).get("assistant")
        suggestion, trace = await llm.run(
            assistant,
            "assistant",
            prompt,
            instructions=llm.prompt("assistant"),
            setup=setup,
            instance_id=instance_id,
            deps=Deps(
                types,
                [t for t in types if t not in context["human_decision_types"]],
                set(context["evidence_refs"]),
            ),
        )
        span.set(decision=suggestion.decision, model=trace.model)
    return suggestion


# After a resolution: the escalating rule, amended to generalise the person's decision.
class RuleSuggestion(BaseModel):
    text: str = Field(default="", max_length=RULE)  # the amended rule, in English; "" if none
    type: Literal["requirement", "prohibition"] | None = None  # None: the old rule's
    summary: str = Field(max_length=LINE)  # one line in Spanish for the console
    rationale: str = Field(default="", max_length=SHORT)  # in Spanish: what it generalises
    evidence: list[str] = Field(min_length=1, max_length=6)  # references from `evidence_refs`
    # in Spanish: why no rule should learn this case, and a person must always decide it
    no_rule_reason: str | None = Field(default=None, max_length=SHORT)


@dataclass(frozen=True)
class RuleDeps:
    identifiers: list[str]  # this case's own names: a general rule never mentions them
    references: set[str]
    values: dict[str, set[str]] = field(default_factory=dict)  # from `known_values`
    rejected: list[str] = field(default_factory=list)  # rule texts the manager rejected ("":
    # a "no rule" answer)


reviewer_agent = Agent(
    None, output_type=RuleSuggestion, deps_type=RuleDeps, name="reviewer_agent", retries=2
)


@reviewer_agent.output_validator
def _general(ctx: RunContext[RuleDeps], suggestion: RuleSuggestion) -> RuleSuggestion:
    too_long(
        summary=(suggestion.summary, 1),
        rationale=(suggestion.rationale, 2),
        no_rule_reason=(suggestion.no_rule_reason, 2),
    )
    if suggestion.no_rule_reason:
        if suggestion.text.strip():
            raise ModelRetry("with no_rule_reason, text must be empty")
        if "" in ctx.deps.rejected:
            raise ModelRetry(
                "the manager already rejected a no-rule answer (rejected_suggestions): "
                "propose the narrowest general rule instead"
            )
    elif not (suggestion.text.strip() and suggestion.rationale.strip()):
        raise ModelRetry("give text and rationale, or no_rule_reason")
    text = suggestion.text.casefold()
    named = [i for i in ctx.deps.identifiers if i.casefold() in text]
    if named:
        raise ModelRetry(
            f"the rule names this case ({', '.join(named)}): state conditions on symbol "
            "values, categories, thresholds or source data only"
        )
    unknown = set(suggestion.evidence) - ctx.deps.references
    if unknown:
        raise ModelRetry(f"cite only references in evidence_refs: {sorted(unknown)}")
    if " ".join(text.split()) in {" ".join(r.casefold().split()) for r in ctx.deps.rejected}:
        raise ModelRetry(
            "the manager already rejected this rule (rejected_suggestions): propose a "
            "different one that answers the reject reason"
        )
    invented = made_up_values(
        f"{suggestion.text} {suggestion.rationale} {suggestion.no_rule_reason or ''}",
        ctx.deps.values,
    )
    if invented:
        raise ModelRetry(
            "these values are not in case.symbols or related_cases: "
            + ", ".join(f"{name} {value}" for name, value in invented)
            + ". The true ones: "
            + "; ".join(
                f"{name}: {', '.join(sorted(ctx.deps.values[name]))}"
                for name in sorted({name for name, _ in invented})
            )
            + ". Read every fact from the context; never infer one"
        )
    return suggestion


def known_values(*symbol_sets: dict[str, Any]) -> dict[str, set[str]]:
    """The identifier-like values the model was shown (letters and digits: a nif, an iban,
    an order), by symbol. Amounts, rates and dates are left out: a rule may state a new
    threshold. So is free text, over 40 characters."""
    known: dict[str, set[str]] = {}
    for symbols in symbol_sets:
        for name, value in symbols.items():
            value = str(value or "")
            if 6 <= len(value) <= 40 and re.search(r"[A-Za-z]", value) and re.search(r"\d", value):
                known.setdefault(name, set()).add(value.upper())
    return known


def made_up_values(text: str, known: dict[str, set[str]]) -> list[tuple[str, str]]:
    """Tokens of `text` written like a value of a symbol (same runs of letters, digits and
    separators: B96233419 is one letter and eight digits) that are none of its values shown:
    a nif or an order the model invented, as in "the other invoice is from B12345678"."""
    found = set()
    for name, values in known.items():
        for value in values:
            shape = "".join(
                f"[A-Za-z]{{{len(run)}}}"
                if run.isalpha()
                else rf"\d{{{len(run)}}}"
                if run.isdigit()
                else re.escape(run)
                for run in re.findall(r"[A-Za-z]+|\d+|.", value)
            )
            for token in re.findall(rf"(?<![A-Za-z\d]){shape}(?![A-Za-z\d])", text):
                if token.upper() not in values:
                    found.add((name, token))
    return sorted(found)


def identifiers(instance: Instance) -> list[str]:
    """What names this one case: its file, and the invoice number and file id it carries.
    Short values are left out, since they also appear in amounts and thresholds."""
    symbols = flatten_symbols(instance.symbols or {})
    names = {
        instance.name,
        instance.name.rsplit(".", 1)[0],
        *(str(symbols.get(k) or "") for k in ("file_id", "invoice_number")),
    }
    return sorted(n for n in names if len(n.strip()) >= 4)


async def suggest_rule(
    session: AsyncSession, instance: Instance, engine: Decision, resolution: Decision, rule_id: int
) -> RuleSuggestion:
    """Amend rule `rule_id`, the one escalation rule that fired in `engine`, so that cases
    like this one get `resolution`'s decision. The caller already checked it is learnable
    (`proposals.service.learnable`) and records the `suggest_rule` span. The context is
    small on purpose: no file text, and only resolutions of cases the same rule escalated."""
    from app.features.decisions.service import current_sources
    from app.features.versions.configuration import rules as frozen_rules
    from app.features.versions.configuration import setups
    from app.features.versions.model import ProcessVersion

    version = await session.get(ProcessVersion, engine.version_id)
    rules = {r.id: r for r in frozen_rules(version.snapshot)}
    old = rules[rule_id]
    history = await session.execute(
        select(Decision, Instance.symbols)
        .join(Instance, Decision.instance_id == Instance.id)
        .where(Instance.process_id == instance.process_id, Instance.id != instance.id)
        .order_by(Decision.id)
    )
    engine_of: dict[int, Decision] = {}
    similar = []
    for d, symbols in history:  # people's resolutions of other cases this rule escalated
        if d.author == ENGINE:
            engine_of[d.instance_id] = d
            continue
        fired = engine_of[d.instance_id].results if d.instance_id in engine_of else []
        if any(r.get("rule_id") == rule_id and r.get("fires") for r in fired):
            similar.append(
                {
                    "ref": f"resolution:{d.id}",
                    "symbols": flatten_symbols(symbols or {}),
                    "decision": d.decision,
                    "reason": d.reason,
                }
            )
    similar = similar[-MAX_RESOLUTIONS:]
    sources = await current_sources(session, instance.process_id)
    case = flatten_symbols(instance.symbols or {})
    evidence = next(
        (r.get("reason") or "" for r in engine.results if r.get("rule_id") == rule_id), ""
    )
    # The other cases the rule's own reason names (a duplicate order names the invoices it
    # shares the order with), with which of their symbols equal this case's.
    named = await session.execute(
        select(Instance.name, Instance.symbols)
        .where(
            Instance.process_id == instance.process_id,
            Instance.id != instance.id,
            func.strpos(literal(evidence), Instance.name) > 0,
        )
        .order_by(Instance.id)
        .limit(MAX_RESOLUTIONS)
    )
    related = []
    for name, symbols in named:
        flat = flatten_symbols(symbols or {})
        same = sorted(k for k in case if k in flat and flat[k] == case[k])
        related.append({"name": name, "symbols": flat, "same_as_case": same})
    rejected = [
        {"text": p.payload.get("text"), "reject_reason": (p.outcome or {}).get("reason")}
        for p in await session.scalars(
            select(ManagerProposal)
            .where(
                ManagerProposal.instance_id == instance.id,
                ManagerProposal.kind == "rule",
                ManagerProposal.status == "rejected",
            )
            .order_by(ManagerProposal.id)
        )
    ]
    context = {
        "use_case_description": version.snapshot["process"]["description"],
        "decision_types": version.snapshot["process"]["decision_types"],
        "case": {"symbols": case},
        "escalation": {
            "reason": engine.reason,
            "rule": {"id": old.id, "text": old.text, "type": old.type, "decision": old.decision},
            "rule_evidence": evidence,  # what the rule itself reported when it fired
            "related_cases": related,
            "other_rules_fired": [
                {"id": r["rule_id"], "decision": rules[r["rule_id"]].decision}
                for r in engine.results
                if r.get("fires") and r.get("rule_id") != rule_id and r.get("rule_id") in rules
            ],
        },
        "resolution": {
            "ref": f"resolution:{resolution.id}",
            "decision": resolution.decision,
            "reason": resolution.reason,
        },
        "similar_resolutions": similar,
        "rejected_suggestions": rejected,
        "sources": {name: sorted(rows[0]) if rows else [] for name, rows in sources.items()},
    }
    context["evidence_refs"] = sorted(
        {f"symbol:{name}" for name in instance.symbols or {}}
        | {f"rule:{rule_id}", context["resolution"]["ref"]}
        | {r["ref"] for r in similar}
    )
    suggestion, _ = await llm.run(
        reviewer_agent,
        "assistant",
        json.dumps(context, ensure_ascii=False, default=str),
        instructions=llm.prompt("reviewer_agent", "shared"),
        setup=setups(version.snapshot).get("assistant"),
        deps=RuleDeps(
            identifiers(instance) + [r["name"] for r in related],
            set(context["evidence_refs"]),
            known_values(case, *(r["symbols"] for r in related + similar)),
            [r["text"] or "" for r in rejected],
        ),
        instance_id=instance.id,
    )
    return suggestion
