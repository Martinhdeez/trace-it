"""Capture the inputs once; previews run on that capture, never on moving source data."""

import hashlib
import json
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError
from app.core import events
from app.core.config import settings
from app.features.agents import llm
from app.features.decisions.model import Decision, DecisionReview
from app.features.ingestion.model import File, Instance
from app.features.processes import service as processes
from app.features.sources import service as sources


def digest(snapshot: dict) -> str:
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, default=str).encode()).hexdigest()


async def capture(session: AsyncSession, process_id: int) -> dict:
    process = await processes.get(session, process_id)
    instances = list(
        await session.scalars(
            select(Instance).where(Instance.process_id == process_id).order_by(Instance.id)
        )
    )
    decisions = list(
        await session.scalars(
            select(Decision)
            .join(Instance)
            .where(Instance.process_id == process_id)
            .order_by(Decision.id)
        )
    )
    reviews = list(
        await session.scalars(
            select(DecisionReview)
            .join(Decision)
            .join(Instance)
            .where(Instance.process_id == process_id)
            .order_by(DecisionReview.id)
        )
    )
    files = await session.execute(
        select(File.hash, File.text).where(File.hash.in_([i.file_hash for i in instances]))
    )
    from app.features.versions import configuration as version_config
    from app.features.versions import service as versions

    version = await versions.active(session, process_id)
    setups = version_config.setups(version.snapshot)
    return {
        "version_id": version.id,
        "execution": version.snapshot.get("execution", {}),
        "process": process.model_dump(mode="json"),
        "files": {
            key: {"text": (text or "")[:12000], "truncated": bool(text and len(text) > 12000)}
            for key, text in files
        },
        "rules": version.snapshot["rules"],
        "sources": [
            {"id": s.id, "name": s.name, "rows": s.rows, "origin": s.origin}
            for s in await sources.current_loads(session, process_id)
        ],
        "instances": [
            {"id": i.id, "name": i.name, "symbols": i.symbols, "file_hash": i.file_hash}
            for i in instances
        ],
        "decisions": [
            {
                k: getattr(d, k)
                for k in (
                    "id",
                    "instance_id",
                    "decision",
                    "author",
                    "reason",
                    "results",
                    "rules_hash",
                )
            }
            for d in decisions
        ],
        "reviews": [
            {
                k: getattr(r, k)
                for k in ("id", "decision_id", "status", "recommendation", "reasoning", "evidence")
            }
            for r in reviews
        ],
        "guidance": version.snapshot["guidance"],
        "agents": {
            role: {"config_id": setup.config_id, "settings": setup.settings.model_dump(mode="json")}
            for role, setup in sorted(setups.items())
        },
        "defaults": {
            role: getattr(settings, f"{role}_model")
            for role in ("learner", "normalizer", "compiler", "tester", "decision_reviewer")
        },
        "prompts": {
            name: llm.prompt(name)
            for name in (
                "learner",
                "normalizer",
                "coder",
                "tester",
                "reviewer",
                "shared",
                "decision_reviewer",
            )
        },
    }


def cases(snapshot: dict, limit: int) -> list[dict]:
    history = {}
    reviews = {}
    for decision in snapshot["decisions"]:
        history.setdefault(decision["instance_id"], []).append(decision)
    for review in snapshot["reviews"]:
        reviews.setdefault(review["decision_id"], []).append(review)
    resolved, ordinary = [], []
    for instance in reversed(snapshot["instances"]):
        decisions = history.get(instance["id"], [])
        if not decisions:
            continue
        case = {
            **instance,
            "decisions": decisions,
            "reviews": [r for d in decisions for r in reviews.get(d["id"], [])],
        }
        (resolved if decisions[-1]["author"] != "engine" else ordinary).append(case)
    # Reserve half the bounded sample for ordinary cases; fill unused slots from either side.
    selected = resolved[: limit // 2] + ordinary[: limit // 2]
    ids = {c["id"] for c in selected}
    return (selected + [c for c in resolved + ordinary if c["id"] not in ids])[:limit]


async def context(session: AsyncSession, snapshot: dict, limit: int) -> dict:
    selected = cases(snapshot, limit)
    if not selected:
        raise ConflictError("Run the process before requesting learning analysis")
    refs = {f"case:{c['id']}": c for c in selected}
    rows = await session.scalars(
        select(events.Event)
        .where(
            events.Event.process_id == snapshot["process"]["id"],
            events.Event.instance_id.in_([c["id"] for c in selected]),
        )
        .order_by(events.Event.id.desc())
        .limit(limit * 3)
    )
    # Operational details aid diagnosis; raw prompts/documents stay out of this bounded context.
    for row in rows:
        refs[f"span:{row.span_id}"] = {
            "instance_id": row.instance_id,
            "step": row.step,
            "status": row.status,
            "data": {
                k: v
                for k, v in row.data.items()
                if k
                in (
                    "decision",
                    "reason",
                    "author",
                    "before",
                    "error",
                    "recommendation",
                    "requires_human",
                )
            },
        }
    return {
        "process": snapshot["process"],
        "rules": [
            {k: r[k] for k in ("id", "text", "decision", "status")} for r in snapshot["rules"]
        ],
        "guidance": snapshot["guidance"],
        "sources": [
            {"id": s["id"], "name": s["name"], "sample_rows": s["rows"][:3]}
            for s in snapshot["sources"]
        ],
        "sampling": {
            "selected": len(selected),
            "outcome_counts": dict(Counter(c["decisions"][-1]["decision"] for c in selected)),
            "author_counts": dict(Counter(c["decisions"][-1]["author"] for c in selected)),
            "population": len(snapshot["instances"]),
            "method": "recent cases, half human resolutions and half ordinary cases",
        },
        "evidence": refs,
    }
