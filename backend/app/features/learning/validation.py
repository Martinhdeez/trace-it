"""Prepare norms without creating enforced rules or writing decision history."""

import asyncio
import copy
import json

from app.features.agents import compiler, decision_reviewer, llm, normalizer, sandbox
from app.features.decisions.engine import Outcomes, decide
from app.features.ingestion.symbols import flatten_symbols, scan
from app.features.learning.evidence import cases
from app.features.processes.model import DecisionType, Symbol
from app.features.rules.model import ENFORCED, Rule
from app.features.rules.service import rule_hash
from app.features.use_cases.schemas import AgentSettings


def setups(snapshot: dict) -> dict[str, llm.Setup]:
    return {
        role: llm.Setup(AgentSettings.model_validate(value["settings"]), value["config_id"])
        for role, value in snapshot["agents"].items()
    }


def rule(data: dict, process_id: int) -> Rule:
    return Rule(
        process_id=process_id,
        **{
            k: data[k]
            for k in ("id", "text", "type", "decision", "code", "hash", "status", "report")
        },
    )


def impact(snapshot: dict, added: list[dict]) -> dict:
    process = snapshot["process"]
    rules = [rule(r, process["id"]) for r in snapshot["rules"] if r["status"] in ENFORCED]
    rules += [rule(r, process["id"]) for r in added]
    types = process["decision_types"]
    outcomes = Outcomes(
        {t["name"]: t["priority"] for t in types},
        next(t["name"] for t in types if t["is_default"]),
        max((t for t in types if t["requires_human"]), key=lambda t: t["priority"])["name"],
        tuple(s["name"] for s in process["symbols"] if s["required"]),
    )
    latest = {d["instance_id"]: d for d in snapshot["decisions"]}
    selected = [i for i in snapshot["instances"] if i["id"] in latest and i["symbols"] is not None]
    population = [
        (i["id"], {**flatten_symbols(i["symbols"]), "_instance": i["name"]})
        for i in snapshot["instances"]
        if i["symbols"] is not None
    ]
    verdicts = decide(
        rules,
        outcomes,
        [(i["id"], flatten_symbols(i["symbols"])) for i in selected],
        {s["name"]: s["rows"] for s in snapshot["sources"]},
        population,
        sandbox.run_dataset,
        {i["id"]: u for i in selected if (u := scan(i["symbols"])) is not None},
    )
    pending = {
        r["decision_id"]
        for r in snapshot["reviews"]
        if r["status"] == "completed"
        and any(
            d["id"] == r["decision_id"] and d["decision"] != r["recommendation"]
            for d in latest.values()
        )
    }
    changes, conflicts, errors = [], [], []
    for instance, verdict in zip(selected, verdicts, strict=True):
        previous = latest[instance["id"]]
        if any(r.fires is None for r in verdict.results):
            errors.append({"instance_id": instance["id"], "reason": verdict.reason})
        if verdict.decision != previous["decision"]:
            change = {
                "instance_id": instance["id"],
                "decision_id": previous["id"],
                "before": previous["decision"],
                "after": verdict.decision,
                "reason": verdict.reason,
            }
            (
                conflicts
                if previous["author"] != "engine" or previous["id"] in pending
                else changes
            ).append(change)
    return {
        "basis": "stored symbols and current captured sources, not original historical replay",
        "evaluated": len(selected),
        "unchanged": len(selected) - len(changes) - len(conflicts),
        "changes": changes,
        "conflicts": conflicts,
        "errors": errors,
    }


async def deterministic(text: str, snapshot: dict) -> dict:
    process = snapshot["process"]
    config = setups(snapshot)
    types = [DecisionType(**t) for t in process["decision_types"]]
    symbols = [Symbol(**s) for s in process["symbols"]]
    sources = {s["name"]: s["rows"] for s in snapshot["sources"]}
    active = [rule(r, process["id"]) for r in snapshot["rules"] if r["status"] in ENFORCED]
    normalized, _ = await normalizer.normalize(
        text, process["description"], types, symbols, sources, active, config.get("normalizer")
    )
    checks = [c for sentence in normalized.norm_rules for c in sentence.checks]
    policies = [p for sentence in normalized.norm_rules for p in sentence.policies]
    report = {"valid": False, "normalization": normalized.model_dump(), "rules": []}
    if policies or not checks or len(checks) > 8:
        report["error"] = (
            "A deterministic proposal must yield 1-8 checks and no subjective policies; "
            "submit guidance separately"
        )
        return report
    for index, check in enumerate(checks, 1):
        candidate = Rule(
            id=-index,
            process_id=process["id"],
            text=check.text,
            type=check.type,
            decision=check.decision,
        )
        compiled = await compiler.compile_text(
            candidate, symbols, sources, process["description"], compiler.Runs(config)
        )
        report["rules"].append(
            {
                "id": -index,
                "text": check.text,
                "type": check.type,
                "decision": check.decision,
                "code": compiled.code,
                "tests": compiled.tests,
                "hash": rule_hash(check.text, compiled.code) if compiled.code else None,
                "status": "draft",
                "report": compiled.report,
                "interpretation": check.model_dump(),
            }
        )
    if not all(r["report"].get("valid") and r["code"] for r in report["rules"]):
        return report
    report["impact"] = await asyncio.to_thread(impact, snapshot, report["rules"])
    report["valid"] = not (report["impact"]["conflicts"] or report["impact"]["errors"])
    return report


async def subjective(text: str, snapshot: dict) -> dict:
    if snapshot["process"]["decision_review"] is None:
        return {"valid": False, "error": "Enable decision review before validating guidance"}
    proposed = copy.deepcopy(snapshot)
    proposed["guidance"]["proposed_norm"] = text
    return await compare_reviews(snapshot, proposed)


def review_context(snapshot: dict, case: dict, engine: dict) -> dict:
    config = snapshot["process"]["decision_review"]
    evidence = {
        "guidance": config["guidance"],
        f"file:{case['file_hash']}": snapshot["files"][case["file_hash"]],
        **snapshot["guidance"],
        **{f"symbol:{k}": v for k, v in (case["symbols"] or {}).items()},
        **{
            f"source:{s['id']}": {"name": s["name"], "rows": s["rows"], "origin": s["origin"]}
            for s in snapshot["sources"]
        },
        **{
            f"rule:{r['id']}": {"text": r["text"], "decision": r["decision"], "hash": r["hash"]}
            for r in snapshot["rules"]
            if r["status"] in ENFORCED
        },
    }
    return {
        "use_case_description": snapshot["process"]["description"],
        "decision_types": snapshot["process"]["decision_types"],
        "case": {"name": case["name"], "file_hash": case["file_hash"]},
        "engine": {k: engine[k] for k in ("decision", "reason", "results", "rules_hash")},
        "evidence": evidence,
    }


async def compare_reviews(before: dict, after: dict) -> dict:
    """Paired recommendations only; writes no decisions, resolutions or live reviews."""
    previews = []
    after_cases = {c["id"]: c for c in cases(after, 10)}
    for original in cases(before, 10):
        answers = []
        for snapshot, case in ((before, original), (after, after_cases[original["id"]])):
            config = snapshot["process"]["decision_review"]
            engine = next((d for d in reversed(case["decisions"]) if d["author"] == "engine"), None)
            if engine is None:
                break
            if config is None:
                answers.append({"assessment": None, "model": None, "status": "disabled"})
                continue
            context = review_context(snapshot, case, engine)
            async with asyncio.timeout(config["timeout_seconds"]):
                answer, trace = await llm.run(
                    decision_reviewer.reviewer,
                    "decision_reviewer",
                    json.dumps(context, default=str),
                    instructions=snapshot["prompts"]["decision_reviewer"],
                    setup=setups(snapshot).get("decision_reviewer"),
                    deps=decision_reviewer.Deps(
                        {t["name"] for t in snapshot["process"]["decision_types"]},
                        set(context["evidence"]),
                    ),
                )
            answers.append({"assessment": answer.model_dump(), "model": trace.model})
        if len(answers) == 2:
            previews.append(
                {
                    "instance_id": original["id"],
                    "decision_id": next(
                        d["id"] for d in reversed(original["decisions"]) if d["author"] == "engine"
                    ),
                    "before": answers[0],
                    "after": answers[1],
                    "final_decision": original["decisions"][-1],
                }
            )
    return {
        "valid": bool(previews),
        "basis": "Paired reviewer calls on captured evidence; model outputs can vary",
        "previews": previews,
    }
