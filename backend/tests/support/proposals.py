"""Store a proposal as an agent would, for the e2e that runs with no LLM key (D4).

`python -m tests.support.proposals escalation <instance_id> <decision>`: the assistant's
proposal on an escalated case, answering its current decision.
`python -m tests.support.proposals rule <instance_id> <text>`: the reviewer agent's amended
rule on a case a person resolved (ADR 0035), replacing the escalation rule that fired. Exits
with the Spanish reason when the case is not learnable, as the API answers 409.
`python -m tests.support.proposals source <process_id> <summary>`: a learning proposal that
accepting only records. Prints the proposal id. Reads TRACE_DATABASE_URL (a `_test` one).
"""

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.database import session_factory
from app.features.decisions.model import ENGINE, Decision
from app.features.decisions.service import latest_decisions
from app.features.ingestion.model import Instance
from app.features.proposals.model import ManagerProposal
from app.features.proposals.service import learnable
from app.features.versions import configuration as config
from app.features.versions.model import ProcessVersion
from tests.support.prepare_db import is_test_db


async def _rule(session, instance: Instance, text: str) -> ManagerProposal:
    history = list(
        await session.scalars(
            select(Decision).where(Decision.instance_id == instance.id).order_by(Decision.id)
        )
    )
    resolution = history[-1]
    engine = next(d for d in reversed(history) if d.author == ENGINE)
    snapshot = (await session.get(ProcessVersion, engine.version_id)).snapshot
    rules = {r.id: r for r in config.rules(snapshot)}
    human = {t["name"] for t in snapshot["process"]["decision_types"] if t["requires_human"]}
    replaces, why = learnable(
        engine.reason,
        engine.results,
        {i: r.decision for i, r in rules.items()},
        config.outcomes(snapshot),
        human,
        resolution.decision,
    )
    if replaces is None or resolution.author == ENGINE:
        sys.exit(why or "Resolve the case first")
    summary = f"Escala como la regla {replaces}, salvo casos como este"
    return ManagerProposal(
        process_id=instance.process_id,
        instance_id=instance.id,
        channel="escalation",
        kind="rule",
        summary=summary,
        rationale="Stored by the e2e: no LLM key",
        evidence=[f"rule:{replaces}"],
        payload={
            "decision_id": resolution.id,
            "engine_decision_id": engine.id,
            "replaces": replaces,
            "text": text,
            "summary": summary,
            "type": rules[replaces].type,
            "decision": rules[replaces].decision,
            "resolved_as": resolution.decision,
            "version_id": engine.version_id,
        },
        author="assistant",
    )


async def store(kind: str, target: int, value: str) -> int:
    async with session_factory() as session:
        if kind == "rule":
            row = await _rule(session, await session.get(Instance, target), value)
        elif kind == "escalation":
            instance = await session.get(Instance, target)
            latest = (await latest_decisions(session, [instance]))[instance.id]
            row = ManagerProposal(
                process_id=instance.process_id,
                instance_id=instance.id,
                channel="escalation",
                kind="decision",
                summary=f"{value} for {instance.name}",
                rationale="Stored by the e2e: no LLM key",
                evidence=[],
                payload={
                    "proposed": value,
                    "why": [latest.reason],
                    "options": [{"decision": value, "consequence": "Stored by the e2e"}],
                    "decision_id": latest.id,
                    "escalated_as": latest.decision,
                    "escalation_reason": latest.reason,
                },
                author="assistant",
            )
        else:
            row = ManagerProposal(
                process_id=target,
                channel="learning",
                kind="source",
                summary=value,
                rationale="Stored by the e2e: no LLM key",
                evidence=[],
                payload={},
                author="learner",
            )
        session.add(row)
        await session.commit()
        return row.id


if __name__ == "__main__":
    if not is_test_db(make_url(settings.database_url).database):
        sys.exit("TRACE_DATABASE_URL must name a test database")
    kind, target, value = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    print(asyncio.run(store(kind, target, value)))
