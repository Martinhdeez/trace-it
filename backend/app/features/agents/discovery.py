"""One agent discovers a process from workbook evidence, snapshots and user answers."""

import json
from dataclasses import dataclass

from pydantic_ai import Agent, ModelRetry, RunContext

from app.features.agents import llm
from app.features.processes.draft_schemas import DraftPlan
from app.features.sources import discovery as evidence


@dataclass
class Deps:
    data: dict
    reads: int = 0


agent = Agent(None, output_type=DraftPlan, deps_type=Deps, name="discovery", retries=2)


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
    unknown = {e.reference for p in [*plan.sources, *plan.rules] for e in p.evidence} - allowed
    if unknown:
        raise ModelRetry(f"Cite existing evidence references only: {sorted(unknown)}")
    decisions = {t.name for t in plan.decision_types}
    if any(r.decision not in decisions for r in plan.rules):
        raise ModelRetry("Every rule must use a proposed decision type")
    return plan


async def discover(data: dict, setup: llm.Setup | None) -> DraftPlan:
    context = {
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
    }
    result, _ = await llm.run(
        agent,
        "discovery",
        json.dumps(context, ensure_ascii=False),
        instructions=llm.prompt("discovery"),
        setup=setup,
        deps=Deps(data),
    )
    return result
