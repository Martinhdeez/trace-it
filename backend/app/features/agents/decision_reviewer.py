"""Optional advice after deterministic evaluation. Only a person changes the outcome."""

import asyncio
import json
from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events
from app.core.config import settings
from app.features.agents import llm
from app.features.decisions.model import Decision, DecisionReview
from app.features.ingestion.model import File, Instance
from app.features.learning import guidance
from app.features.processes.schemas import ProcessDetail
from app.features.rules.model import Rule
from app.features.sources.model import Source
from app.features.use_cases import service as use_cases

MAX_TEXT = 12_000


class Assessment(BaseModel):
    decision: str
    reasoning: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)


@dataclass(frozen=True)
class Deps:
    outcomes: set[str]
    references: set[str]


reviewer = Agent(None, output_type=Assessment, deps_type=Deps, retries=1, name="decision_reviewer")


@reviewer.output_validator
def validate(ctx: RunContext[Deps], result: Assessment) -> Assessment:
    if result.decision not in ctx.deps.outcomes:
        raise ModelRetry(f"Choose one of {sorted(ctx.deps.outcomes)}")
    if not result.reasoning.strip():
        raise ModelRetry("Explain the recommendation")
    unknown = set(result.evidence) - ctx.deps.references
    if unknown:
        raise ModelRetry(f"Unknown evidence references: {sorted(unknown)}")
    return result


async def assess(
    session: AsyncSession,
    process: ProcessDetail,
    instance: Instance,
    decision: Decision,
    rules: list[Rule],
    sources: list[Source],
    snapshot: dict | None = None,
) -> None:
    """Append one assessment or failure. Disabled processes never call a model.

    The caller holds the instance lock until both decision and assessment commit. Export
    cannot observe a new engine decision before its review has finished. No database
    operations are swallowed by the optional-agent fallback.
    """
    config = process.decision_review
    if config is None:
        return
    file = await session.get(File, instance.file_hash)
    from app.features.versions.configuration import setups

    setup = (
        setups(snapshot) if snapshot else await use_cases.setups(session, process.use_case_id)
    ).get("decision_reviewer")
    setup = setup or llm.Setup()
    evidence = {
        "guidance": config.guidance,
        **(snapshot["guidance"] if snapshot else await guidance.approved(session, process.id)),
        **{f"symbol:{k}": v for k, v in (instance.symbols or {}).items()},
        **{f"rule:{r.id}": {"text": r.text, "decision": r.decision, "hash": r.hash} for r in rules},
        **{f"source:{s.id}": {"name": s.name, "origin": s.origin, "rows": s.rows} for s in sources},
        f"file:{instance.file_hash}": {
            "text": ((file.text if file else None) or "")[:MAX_TEXT],
            "truncated": bool(file and file.text and len(file.text) > MAX_TEXT),
        },
    }
    context = {
        "use_case_description": process.description,
        "decision_types": [t.model_dump() for t in process.decision_types],
        "case": {"name": instance.name, "file_hash": instance.file_hash},
        "engine": {
            "decision": decision.decision,
            "reason": decision.reason,
            "results": decision.results,
            "rules_hash": decision.rules_hash,
        },
        "evidence": evidence,
    }
    instructions = (snapshot.get("reviewer_prompt") if snapshot else None) or llm.prompt(
        "decision_reviewer"
    )
    row = DecisionReview(
        decision_id=decision.id,
        status="failed",
        evidence=[],
        requires_human=False,
        snapshot={
            "context": context,
            "review_config": config.model_dump(),
            "agent_config_id": setup.config_id,
            "default_model": settings.decision_reviewer_model,
            "agent_settings": setup.settings.model_dump(mode="json"),
            "instructions": instructions,
        },
    )
    with events.span("review_decision", process_id=process.id, instance_id=instance.id) as span:
        try:
            # Includes model creation, provider retries and output validation. Missing keys
            # and a provider outage both leave the deterministic process usable.
            async with asyncio.timeout(config.timeout_seconds):
                result, trace = await llm.run(
                    reviewer,
                    "decision_reviewer",
                    json.dumps(context, ensure_ascii=False, default=str),
                    instructions=instructions,
                    setup=setup,
                    deps=Deps({t.name for t in process.decision_types}, set(evidence)),
                )
        except Exception as error:  # noqa: BLE001 - the optional agent must not stop decisions
            row.error = f"{type(error).__name__}: {error}"
            span.status = "error"
            span.set(error=row.error, fallback=decision.decision)
        else:
            row.status = "completed"
            row.recommendation = result.decision
            row.reasoning = result.reasoning
            row.evidence = result.evidence
            row.model = trace.model
            row.requires_human = result.decision != decision.decision
            span.set(recommendation=result.decision, requires_human=row.requires_human)
    session.add(row)


async def for_decisions(
    session: AsyncSession, decisions: list[Decision]
) -> dict[int, DecisionReview]:
    """Reviews keyed by engine decision, including failures and agreements."""
    if not decisions:
        return {}
    rows = await session.scalars(
        select(DecisionReview)
        .where(DecisionReview.decision_id.in_([d.id for d in decisions]))
        .order_by(DecisionReview.id)
    )
    return {r.decision_id: r for r in rows}
