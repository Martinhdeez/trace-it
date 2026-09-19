"""Store a proposal as an agent would, for the e2e that runs with no LLM key (D4).

`python -m tests.support.proposals escalation <instance_id> <decision>`: the assistant's
proposal on an escalated case, answering its current decision.
`python -m tests.support.proposals source <process_id> <summary>`: a learning proposal that
accepting only records. Prints the proposal id. Reads TRACE_DATABASE_URL (a `_test` one).
"""

import asyncio
import sys

from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.database import session_factory
from app.features.decisions.service import latest_decisions
from app.features.ingestion.model import Instance
from app.features.proposals.model import ManagerProposal
from tests.support.prepare_db import is_test_db


async def store(kind: str, target: int, value: str) -> int:
    async with session_factory() as session:
        if kind == "escalation":
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
