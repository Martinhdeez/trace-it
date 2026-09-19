"""One agent discovers a process from workbook evidence, snapshots and user answers."""

import json
from copy import deepcopy
from dataclasses import dataclass

from pydantic_ai import Agent, ModelRetry, RunContext

from app.features.agents import llm
from app.features.processes.draft_schemas import Discussion, DraftPlan
from app.features.sources import discovery as evidence


@dataclass
class Deps:
    data: dict
    reads: int = 0


agent = Agent(None, output_type=DraftPlan, deps_type=Deps, name="discovery", retries=2)
discussion = Agent(None, output_type=Discussion, deps_type=Deps, name="discovery", retries=2)


@discussion.tool
@agent.tool
def read_sheet(
    ctx: RunContext[Deps], document: str, sheet: str, first_row: int, last_row: int
) -> list[dict]:
    """Read up to 100 rows from a workbook, preserving cell addresses and raw values."""
    ctx.deps.reads += 1
    if ctx.deps.reads > 30 or first_row < 1 or not 0 <= last_row - first_row < 100:
        return [{"error": "Read limit reached; ask the user to narrow the material"}]
    try:
        return evidence.sheet_rows(ctx.deps.data["documents"], document, sheet, first_row, last_row)
    except ValueError as error:
        return [{"error": str(error)}]


@discussion.tool
@agent.tool
def search_snapshot(ctx: RunContext[Deps], name: str, query: str) -> list[dict]:
    """Search an already downloaded complete ERP/source snapshot; return at most 20 rows."""
    ctx.deps.reads += 1
    if ctx.deps.reads > 30:
        return [{"error": "Read limit reached"}]
    snapshot = ctx.deps.data["snapshots"].get(name)
    if snapshot is None:
        return [{"error": "Snapshot not loaded; ask the user to connect the source"}]
    return [r for r in snapshot["rows"] if query.casefold() in json.dumps(r).casefold()][:20]


@agent.output_validator
def validate(ctx: RunContext[Deps], plan: DraftPlan) -> DraftPlan:
    allowed = evidence.evidence_references(ctx.deps.data)
    unknown = {
        e.reference for p in [*plan.sources, *plan.rules, *plan.guidance] for e in p.evidence
    } - allowed
    if unknown:
        raise ModelRetry(f"Cite existing evidence references only: {sorted(unknown)}")
    decisions = {t.name for t in plan.decision_types}
    if any(r.decision not in decisions for r in plan.rules):
        raise ModelRetry("Every rule must use a proposed decision type")
    return plan


def context(data: dict) -> dict:
    return {
        "existing_process": data.get("base_fingerprint") is not None,
        "current_plan": data["plan"],
        "reviews": data["reviews"],
        "messages": data["messages"],
        "workbooks": evidence.inventory(data["documents"]),
        "snapshots": {
            name: {"origin": s["origin"], "count": len(s["rows"]), "sample": s["rows"][:10]}
            for name, s in data["snapshots"].items()
        },
        "base_references": data.get("base_references", []),
        "past_cases": data.get("case_context"),
        "editable_version_draft": data.get("version_draft"),
    }


async def discover(data: dict, setup: llm.Setup | None) -> DraftPlan:
    result, _ = await llm.run(
        agent,
        "discovery",
        json.dumps(context(data), ensure_ascii=False, default=str),
        instructions=llm.prompt("discovery"),
        setup=setup,
        deps=Deps(data),
    )
    return result


@discussion.output_validator
def valid_discussion(ctx: RunContext[Deps], result: Discussion) -> Discussion:
    unknown = set(result.evidence) - evidence.evidence_references(ctx.deps.data)
    if unknown:
        raise ModelRetry(f"Cite supplied references only: {sorted(unknown)}")
    return result


async def discuss(data: dict, setup: llm.Setup | None) -> Discussion:
    discussion_context = context(data)
    if setup:
        discussion_context["authoring_guidance"] = setup.settings.instructions
        setup = llm.Setup(setup.settings.model_copy(update={"instructions": ""}), setup.config_id)
    result, _ = await llm.run(
        discussion,
        "discovery",
        json.dumps(discussion_context, ensure_ascii=False, default=str),
        instructions=llm.prompt("process_chat"),
        setup=setup,
        deps=Deps(deepcopy(data)),
    )
    return result
