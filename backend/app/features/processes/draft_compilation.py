"""Compile reviewed rules without activating them; reuse the engine and historical audit."""

import asyncio

from app.common.exceptions import ConflictError
from app.features.agents import compiler, normalizer, sandbox
from app.features.agents.llm import Setup
from app.features.decisions import service as decisions
from app.features.decisions.engine import Outcomes, decide
from app.features.processes.draft_schemas import DraftPlan
from app.features.processes.model import DecisionType, Symbol
from app.features.rules.model import Rule
from app.features.rules.service import rule_hash
from app.features.versions import configuration as config
from app.features.versions import execution
from app.features.versions import service as versions


def proposals(plan: DraftPlan) -> list[str]:
    return [
        "setup",
        *[f"source:{s.name}" for s in plan.sources],
        *[f"rule:{r.name}" for r in plan.rules],
        *[f"example:{e.name}" for e in plan.examples],
    ]


def ready(plan: DraftPlan, reviews: dict):
    if plan.questions:
        raise ConflictError("Answer the outstanding questions before compiling")
    if not plan.name.strip() or not plan.rules or not plan.examples:
        raise ConflictError("A name, rules and confirmed acceptance examples are required")
    if any(reviews.get(p) != "accepted" for p in proposals(plan)):
        raise ConflictError("Review and accept every proposal before compiling")
    try:
        plan.definition()
    except ValueError as error:
        raise ConflictError(str(error)) from error
    known = {t.name for t in plan.decision_types}
    if any(e.decision not in known for e in plan.examples):
        raise ConflictError("An acceptance example names an unknown outcome")


def compiled_rules(compilations: list[dict]) -> list[Rule]:
    return [
        Rule(
            id=-(i + 1),
            process_id=0,
            text=r["text"],
            type=r["type"],
            decision=r["decision"],
            code=r["code"],
            hash=r["hash"],
            report=r["report"],
            tests=r.get("tests", []),
            status="active",
        )
        for i, r in enumerate(compilations)
    ]


def candidate(plan: DraftPlan, compilations: list[dict], base: dict) -> dict:
    from copy import deepcopy

    snapshot = deepcopy(base)
    snapshot["rules"] = [config.artifact(r) for r in compiled_rules(compilations)]
    snapshot["process"].update(
        plan.model_dump(include={"name", "description", "decision_types", "symbols"})
    )
    return snapshot


async def compile_plan(plan: DraftPlan, tables: dict, setups: dict) -> list[dict]:
    symbols = [Symbol(process_id=0, **s.model_dump()) for s in plan.symbols]
    types = [DecisionType(process_id=0, **t.model_dump()) for t in plan.decision_types]
    compilations = []
    for proposal in plan.rules:
        # The manager's chosen outcome is explicit. Never inherit a use-case rejection
        # default over the outcome the user just approved.
        setup = setups.get("normalizer")
        if setup:
            setup = Setup(
                setup.settings.model_copy(update={"failed_check_decision": None}), setup.config_id
            )
        text = (
            f"{proposal.text}\nRule type: {proposal.type}. "
            f"When this rule fires, outcome: {proposal.decision}."
        )
        normalized, _ = await normalizer.normalize(
            text, plan.description, types, symbols, tables, [], setup
        )
        checks = [c for s in normalized.norm_rules for c in s.checks]
        if not checks or any(c.decision != proposal.decision for c in checks):
            raise ConflictError(
                f"Normalizer changed the approved outcome for {proposal.name}; clarify its rule"
            )
        for check in checks:
            rule = Rule(text=check.text, type=check.type, decision=proposal.decision, process_id=0)
            result = await compiler.compile_text(
                rule, symbols, tables, plan.description, compiler.Runs(setups)
            )
            compilations.append(
                {
                    "proposal": proposal.name,
                    "text": rule.text,
                    "type": rule.type,
                    "decision": rule.decision,
                    "code": result.code,
                    "tests": result.tests,
                    "hash": rule_hash(rule.text, result.code) if result.code else None,
                    "report": result.report,
                    "interpretation": check.interpretation,
                }
            )
    return compilations


async def preview(
    session,
    process_id: int | None,
    plan: DraftPlan,
    tables: dict,
    compilations: list[dict],
    base: dict | None = None,
) -> dict:
    rules = compiled_rules(compilations)
    types = plan.decision_types
    outcomes = Outcomes(
        {t.name: t.priority for t in types},
        next(t.name for t in types if t.is_default),
        max((t for t in types if t.requires_human), key=lambda t: t.priority).name,
        tuple(s.name for s in plan.symbols if s.required),
    )
    results = []
    for example in plan.examples:
        dataset = [(0, example.instance)]
        population = [*dataset, *((i + 1, row) for i, row in enumerate(example.others))]
        verdict = (
            await asyncio.to_thread(
                decide,
                rules,
                outcomes,
                dataset,
                {**tables, **example.sources},
                population,
                sandbox.run_dataset,
            )
        )[0]
        results.append(
            {
                "name": example.name,
                "expected": example.decision,
                "actual": verdict.decision,
                "reason": verdict.reason,
                "passed": verdict.decision == example.decision
                and not verdict.reason.startswith(
                    ("RULE_ERROR", "RULE_NEEDS_DATA", "RULE_CONFLICT")
                ),
            }
        )
    impact = {"valid": True, "unchanged": 0, "changes": [], "conflicts": [], "errors": []}
    if process_id:
        if base is None:
            base = (await versions.active(session, process_id)).snapshot
        impact = await versions.inspect(
            session,
            candidate(plan, compilations, base),
            await execution.capture(session, process_id),
            tables=tables,
        )
    return {
        "valid": all(r["report"].get("valid") for r in compilations)
        and all(e["passed"] for e in results)
        and impact["valid"],
        "compilations": compilations,
        "examples": results,
        "impact": impact,
        "source_counts": {name: len(rows) for name, rows in tables.items()},
        "replaced_rules": [
            {"id": r.id, "text": r.text, "decision": r.decision}
            for r in (await decisions.active_rules(session, process_id) if process_id else [])
        ],
    }
