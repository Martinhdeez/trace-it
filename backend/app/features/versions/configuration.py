"""Convert stored configuration to engine inputs without reading live settings."""

import hashlib
import json
from copy import deepcopy

from sqlalchemy import select

from app.core.config import settings
from app.features.agents import llm
from app.features.decisions.engine import Outcomes
from app.features.learning import guidance
from app.features.processes.model import DecisionType, Process, Symbol
from app.features.processes.schemas import ProcessDetail
from app.features.rules.model import ENFORCED, Rule
from app.features.use_cases import service as use_cases
from app.features.use_cases.model import UseCase
from app.features.use_cases.schemas import ROLES, AgentSettings

RULE_FIELDS = (
    "id",
    "norm_rule_id",
    "text",
    "type",
    "decision",
    "code",
    "tests",
    "hash",
    "report",
    "status",
)


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def artifact(rule: Rule) -> dict:
    return deepcopy(
        {
            **{k: getattr(rule, k) for k in RULE_FIELDS},
            "status": "active" if rule.code else "blocked",
        }
    )


def rules(snapshot: dict) -> list[Rule]:
    return [Rule(**r) for r in snapshot["rules"]]


def outcomes(snapshot: dict) -> Outcomes:
    types = snapshot["process"]["decision_types"]
    return Outcomes(
        priorities={t["name"]: t["priority"] for t in types},
        default=next(t["name"] for t in types if t["is_default"]),
        escalate=max((t for t in types if t["requires_human"]), key=lambda t: t["priority"])[
            "name"
        ],
        required=tuple(s["name"] for s in snapshot["process"]["symbols"] if s["required"]),
    )


def setups(snapshot: dict) -> dict[str, llm.Setup]:
    execution = snapshot.get("execution", {})
    return {
        role: llm.Setup(
            settings=AgentSettings.model_validate(row["settings"]),
            config_id=row["config_id"],
            local_only=execution.get("local_only", False),
            local_endpoint=execution.get("local_endpoint"),
            execution_hash=digest({"execution": execution, "agents": snapshot["agents"]}),
        )
        for role, row in snapshot["agents"].items()
    }


async def agents(session, use_case_id: int) -> dict:
    configured = await use_cases.setups(session, use_case_id)
    result = {}
    for role in ROLES:
        setup = configured.get(role, llm.Setup())
        config = setup.settings.model_dump(mode="json")
        config["model"] = config["model"] or getattr(settings, f"{role}_model")
        result[role] = {"config_id": setup.config_id, "settings": config}
    return result


async def workspace(session, process_id: int) -> dict:
    """Legacy tables hold authoring inputs only. Runtime reads published snapshots."""
    process = await session.get(Process, process_id)
    types = list(
        await session.scalars(
            select(DecisionType)
            .where(DecisionType.process_id == process_id)
            .order_by(DecisionType.name)
        )
    )
    symbols = list(
        await session.scalars(
            select(Symbol).where(Symbol.process_id == process_id).order_by(Symbol.name)
        )
    )
    description = (await session.get(UseCase, process.use_case_id)).description
    detail = ProcessDetail(
        id=process.id,
        name=process.name,
        use_case_id=process.use_case_id,
        description=description,
        decision_types=[
            {k: getattr(t, k) for k in ("name", "priority", "is_default", "requires_human")}
            for t in types
        ],
        symbols=[
            {k: getattr(s, k) for k in ("name", "type", "description", "required", "extraction")}
            for s in symbols
        ],
        decision_review=process.decision_review,
    )
    rows = await session.scalars(
        select(Rule)
        .where(Rule.process_id == process_id, Rule.status.in_(ENFORCED))
        .order_by(Rule.id)
    )
    snapshot = {
        "process": detail.model_dump(mode="json", exclude={"active_version_id"}),
        "rules": [artifact(r) for r in rows],
        "guidance": await guidance.approved(session, process_id),
        "agents": await agents(session, process.use_case_id),
        "reviewer_prompt": llm.prompt("decision_reviewer"),
    }
    from app.features.processes import execution as execution_config

    execution_config.write(snapshot, execution_config.read(snapshot))
    return snapshot
