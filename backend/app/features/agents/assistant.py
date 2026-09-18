"""Escalation assistant: suggests a decision, its reasoning and a new rule (3.4).
Owner: Martín.

The LLM never decides anything in the pipeline. This is only a suggestion shown to a
person, who then resolves the case and, if they want, adds the proposed rule (which is
compiled and validated like any other rule)."""

import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError, TraceError
from app.features.decisions.model import ENGINE, Decision
from app.features.ingestion.model import File, Instance
from app.features.llm.client import complete
from app.features.processes.model import DecisionType, Process
from app.features.rules.model import Rule
from app.features.traces.service import record

MAX_TEXT = 12_000  # chars of the file's text sent to the model
MAX_RESOLUTIONS = 10

SYSTEM = """\
You assist a person who must resolve a case that an automatic, rule-based decision process \
sent to a person (its decision type requires a human, or it is under review). You do not \
decide: you suggest, and the person decides.

Given the case, answer with:
- decision: the decision you would take. It MUST be exactly one of decision_types. Avoid the \
types in human_decision_types: those only send the case to a person, who needs a final one.
- reasoning: why, citing the concrete symbol values (with their origin) and the rule(s) \
that fired. Be brief and factual. Write in English.
- proposed_rule: ONE new rule, in English, that would resolve this case and similar future \
ones automatically. It must be general enough to cover similar cases but not broader: name \
the exact symbols it uses (by their name) and where each comes from, with precise conditions \
(thresholds, comparisons, lists), so a code agent can implement it without ambiguity. Follow the \
conventions in process_description (normalisation, units, tolerances, missing values) and do \
not restate them in the rule. Do not restate an existing rule. Follow how people resolved \
past cases when they are relevant.
- proposed_type: "requirement" if the rule states a condition that must hold, \
"prohibition" if it states a condition that must not happen."""


class AssistantError(TraceError):
    status_code = 502
    code = "llm_error"


class _Output(BaseModel):
    decision: str
    reasoning: str
    proposed_rule: str
    proposed_type: Literal["requirement", "prohibition"]


@dataclass(frozen=True)
class Suggestion:
    decision: str
    reasoning: str
    proposed_rule: str  # rule text, to be compiled like any other rule if accepted
    proposed_type: str  # requirement | prohibition


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
    types = [t.name for t in all_types]
    human = [t.name for t in all_types if t.requires_human]
    if not (latest and latest.decision in human) and instance.status != "REVIEW":
        raise ConflictError(f"Instance {instance.id} is neither escalated nor in review")

    rules = {r.id: r for r in await session.scalars(select(Rule).where(Rule.process_id == pid))}
    file = await session.get(File, instance.file_hash)
    resolutions = await session.execute(
        select(Decision, Instance.symbols)
        .join(Instance, Decision.instance_id == Instance.id)
        .where(Instance.process_id == pid, Decision.author != ENGINE)
        .order_by(Decision.id.desc())
        .limit(MAX_RESOLUTIONS)
    )

    process = await session.get(Process, pid)
    fired = [r for r in (latest.results if latest else []) if r.get("fires")]
    context = {
        # conventions every rule of the process follows; the proposed rule must too
        "process_description": process.description if process else "",
        "decision_types": types,
        "human_decision_types": human,
        "case": {
            "name": instance.name,
            "symbols": instance.symbols or {},
            "file_text": ((file.text if file else None) or "")[:MAX_TEXT],
        },
        "escalation": {
            "current_decision": latest.decision if latest else None,
            "status": instance.status,
            "review_reason": instance.review_reason,
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
            {"symbols": symbols, "decision": d.decision, "author": d.author, "reason": d.reason}
            for d, symbols in resolutions
        ],
    }
    return context, types


async def suggest(session: AsyncSession, instance_id: int) -> Suggestion:
    instance = await session.get(Instance, instance_id)
    if instance is None:
        raise NotFoundError(f"Instance {instance_id} does not exist")
    context, types = await _context(session, instance)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False, default=str)},
    ]
    latency, cost, output, model, attempts = 0, None, None, None, 0
    while attempts < 2:  # one retry if the reply is invalid
        attempts += 1
        try:
            reply = await complete(session, "assistant", messages, _Output)
        except TraceError:
            raise
        except Exception as error:
            raise AssistantError(f"The assistant's model failed: {error}") from error
        model = reply.model
        latency += reply.latency_ms
        if reply.cost is not None:
            cost = (cost or 0) + reply.cost
        try:
            output = _Output.model_validate_json(reply.content)
            if output.decision in types:
                break
            problem = f"decision {output.decision!r} is not one of {types}"
        except ValidationError as error:
            problem = f"invalid reply: {error}"
        output = None
        messages += [
            {"role": "assistant", "content": reply.content},
            {"role": "user", "content": f"Fix this: {problem}. Answer again."},
        ]
    if output is None:
        raise AssistantError(f"The assistant gave no valid suggestion: {problem}")

    record(
        session,
        "suggest_escalation",
        instance_id=instance_id,
        data={"model": model, "decision": output.decision, "attempts": attempts},
        latency_ms=latency,
        cost=cost,
    )
    await session.commit()
    return Suggestion(**output.model_dump())
