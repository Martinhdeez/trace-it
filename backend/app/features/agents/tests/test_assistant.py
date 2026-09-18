"""Against the local database (`docker compose up db -d` + migrations); skipped if absent.
The LLM is monkeypatched: no network."""

import json
import socket
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.database import engine, session_factory
from app.features.agents import assistant
from app.features.decisions.model import Decision
from app.features.ingestion.model import File, Instance
from app.features.llm.client import Reply
from app.features.processes.model import DecisionType, Process
from app.features.rules.model import Rule
from app.features.traces.model import Event
from app.main import app


def _db_available() -> bool:
    url = make_url(settings.database_url)
    try:
        socket.create_connection((url.host, url.port or 5432), timeout=1).close()
        return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="Local Postgres not available")

SUGGESTION = {
    "decision": "NO_PAGAR",
    "reasoning": "amount=5000 (text) exceeds the limit of the rule 'amount > 1000'",
    "proposed_rule": "If amount (invoice text) > 4000 and supplier (Excel) = 'ACME', do not pay",
    "proposed_type": "prohibition",
}


DESCRIPTION = "Amounts in whole cents; if a value is missing, the rule does not fire."


@pytest.fixture
async def case(request):
    """A process with an escalated instance, a past human resolution and a pending one. The
    human-queue type is named ESCALAR unless the test passes another name as param."""
    escalate = getattr(request, "param", "ESCALAR")
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as s:
        process = Process(name=f"assistant-{suffix}", description=DESCRIPTION)
        s.add(process)
        await s.flush()
        s.add_all(
            [
                DecisionType(process_id=process.id, name=escalate, priority=3, requires_human=True),
                DecisionType(process_id=process.id, name="NO_PAGAR", priority=2),
                DecisionType(process_id=process.id, name="PAGAR", priority=1, is_default=True),
            ]
        )
        await s.flush()
        rule = Rule(
            process_id=process.id,
            text="If amount > 1000, escalate",
            type="prohibition",
            decision=escalate,
            status="active",
        )
        file = File(hash=uuid.uuid4().hex, name="f.pdf", content=b"x", text="Total: 5000 EUR")
        s.add_all([rule, file])
        await s.flush()
        symbols = {"amount": {"value": 5000, "origin": "text"}}
        escalated, old, pending = (
            Instance(process_id=process.id, file_hash=file.hash, name=n, symbols=symbols)
            for n in ("a", "b", "c")
        )
        s.add_all([escalated, old, pending])
        await s.flush()
        results = [{"rule_id": rule.id, "hash": "h", "fires": True, "reason": "amount > 1000"}]
        s.add_all(
            [
                Decision(
                    instance_id=escalated.id,
                    decision=escalate,
                    results=results,
                    rules_hash="h",
                    author="engine",
                ),
                Decision(
                    instance_id=old.id,
                    decision="NO_PAGAR",
                    results=results,
                    rules_hash="h",
                    author="Ana",
                    reason="ACME does not charge above 4000",
                ),
            ]
        )
        await s.commit()
        yield {"escalated": escalated.id, "pending": pending.id}
    await engine.dispose()  # connections are bound to this test's event loop


def _llm(monkeypatch, replies: list[dict]) -> list[list[dict]]:
    calls = []

    async def fake(session, role, messages, response_format=None):
        assert role == "assistant"
        calls.append(list(messages))
        return Reply(json.dumps(replies.pop(0)), "fake/model", 0.01, 5)

    monkeypatch.setattr(assistant, "complete", fake)
    return calls


async def test_suggests_and_records_an_event(case, monkeypatch) -> None:
    calls = _llm(monkeypatch, [SUGGESTION])
    async with session_factory() as s:
        suggestion = await assistant.suggest(s, case["escalated"])
    assert suggestion == assistant.Suggestion(**SUGGESTION)

    context = json.loads(calls[0][1]["content"])
    assert context["process_description"] == DESCRIPTION
    assert context["decision_types"] == ["ESCALAR", "NO_PAGAR", "PAGAR"]
    assert context["human_decision_types"] == ["ESCALAR"]
    assert context["escalation"]["fired_rules"][0]["text"].startswith("If amount")
    assert context["human_resolutions"][0]["reason"] == "ACME does not charge above 4000"
    assert context["case"]["file_text"] == "Total: 5000 EUR"

    async with session_factory() as s:
        event = await s.scalar(select(Event).where(Event.instance_id == case["escalated"]))
    assert event.step == "suggest_escalation"
    assert event.data["model"] == "fake/model"
    assert event.latency_ms == 5


@pytest.mark.parametrize("case", ["MANUAL_REVIEW"], indirect=True)
async def test_human_type_with_another_name(case, monkeypatch) -> None:
    calls = _llm(monkeypatch, [SUGGESTION])
    async with session_factory() as s:
        suggestion = await assistant.suggest(s, case["escalated"])
    assert suggestion.decision == "NO_PAGAR"
    context = json.loads(calls[0][1]["content"])
    assert context["human_decision_types"] == ["MANUAL_REVIEW"]
    assert context["escalation"]["current_decision"] == "MANUAL_REVIEW"


async def test_invalid_decision_retries_once(case, monkeypatch) -> None:
    calls = _llm(monkeypatch, [{**SUGGESTION, "decision": "REJECT"}, SUGGESTION])
    async with session_factory() as s:
        suggestion = await assistant.suggest(s, case["escalated"])
    assert suggestion.decision == "NO_PAGAR"
    assert len(calls) == 2
    assert "REJECT" in calls[1][-1]["content"]


async def test_not_escalated_gives_409(case, monkeypatch) -> None:
    _llm(monkeypatch, [])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.get(f"/instances/{case['pending']}/suggestion")
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "conflict"
        r = await api.get("/instances/0/suggestion")
        assert r.status_code == 404, r.text
