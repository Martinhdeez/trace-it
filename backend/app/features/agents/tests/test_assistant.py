"""Against the local database (`make test-db`); skipped if absent. The model is scripted:
no network."""

import socket
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.database import engine, session_factory
from app.core.events import Event
from app.features.agents import assistant, llm
from app.features.decisions.model import Decision
from app.features.ingestion.model import File, Instance
from app.features.processes.model import DecisionType
from app.features.rules.model import Rule
from app.main import app
from tests.support import rows
from tests.support.models import per_role, retry_prompts, user_json


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
    "why": ["The invoice is over 1000, and amounts above it need a person."],
    "options": [
        {
            "decision": "PAGAR",
            "consequence": "Se paga si se añade la regla: hasta 4000 no escala.",
            "rule": "Amend rule 1: amount > 1000, unless amount <= 4000.",
        },
        {
            "decision": "NO_PAGAR",
            "consequence": "No se paga por la regla nueva: ACME no factura por encima de 4000.",
            "rule": "If amount (invoice text) > 4000 and supplier (Excel) = 'ACME', do not pay",
        },
    ],
    "evidence": ["symbol:amount", "file"],
    "proposed_rule": "If amount (invoice text) > 4000 and supplier (Excel) = 'ACME', do not pay",
    "proposed_type": "prohibition",
}
# "No rule" is an answer too: a person must always look at cases like this one.
NO_RULE = {
    **SUGGESTION,
    "options": [{**o, "rule": None} for o in SUGGESTION["options"]],
    "proposed_rule": None,
    "proposed_type": None,
    "no_rule_reason": "Falta un dato que ninguna regla puede suplir: una persona debe pedirlo.",
}


DESCRIPTION = "Amounts in whole cents; if a value is missing, the rule does not fire."


@pytest.fixture
async def case(request):
    """A process with an escalated instance, a past human resolution and a pending one. The
    human-queue type is named ESCALAR unless the test passes another name as param."""
    escalate = getattr(request, "param", "ESCALAR")
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as s:
        process = await rows.process(s, f"assistant-{suffix}", DESCRIPTION)
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


def script(monkeypatch, replies: list[dict]) -> list:
    seen: dict = {}
    monkeypatch.setattr(llm, "model_for", per_role({"assistant": replies}, seen))
    return seen.setdefault("assistant", [])


async def test_suggests_and_records_an_event(case, monkeypatch) -> None:
    calls = script(monkeypatch, [SUGGESTION])
    async with session_factory() as s:
        suggestion = await assistant.suggest(s, case["escalated"])
    assert suggestion == assistant.Suggestion(**SUGGESTION)

    context = user_json(calls[0])
    assert context["use_case_description"] == DESCRIPTION
    assert context["decision_types"] == ["ESCALAR", "NO_PAGAR", "PAGAR"]
    assert context["human_decision_types"] == ["ESCALAR"]
    assert context["escalation"]["fired_rules"][0]["text"].startswith("If amount")
    assert context["human_resolutions"][0]["reason"] == "ACME does not charge above 4000"
    assert context["case"]["file_text"] == "Total: 5000 EUR"

    async with session_factory() as s:
        event = await s.scalar(
            select(Event).where(
                Event.instance_id == case["escalated"], Event.step == "suggest_escalation"
            )
        )
    assert event.step == "suggest_escalation"
    assert event.data["model"] == "fake/model"
    assert event.data["decision"] == "NO_PAGAR"
    assert event.duration_ms is not None


@pytest.mark.parametrize("case", ["MANUAL_CHECK"], indirect=True)
async def test_human_type_with_another_name(case, monkeypatch) -> None:
    calls = script(monkeypatch, [SUGGESTION])
    async with session_factory() as s:
        suggestion = await assistant.suggest(s, case["escalated"])
    assert suggestion.decision == "NO_PAGAR"
    context = user_json(calls[0])
    assert context["human_decision_types"] == ["MANUAL_CHECK"]
    assert context["escalation"]["current_decision"] == "MANUAL_CHECK"


async def test_invalid_decision_retries_once(case, monkeypatch) -> None:
    calls = script(monkeypatch, [{**SUGGESTION, "decision": "REJECT"}, SUGGESTION])
    async with session_factory() as s:
        suggestion = await assistant.suggest(s, case["escalated"])
    assert suggestion.decision == "NO_PAGAR"
    assert len(calls) == 2
    async with session_factory() as s:
        event = await s.scalar(
            select(Event).where(
                Event.instance_id == case["escalated"], Event.step == "suggest_escalation"
            )
        )
        run = await s.scalar(
            select(Event).where(Event.trace_id == event.trace_id, Event.step == "llm_run")
        )
    assert run.parent_id == event.span_id
    assert run.data["retries"] == 1 and run.data["agent"] == "assistant"
    [retry] = run.data["retry_prompts"]
    assert "REJECT" in retry and run.data["output"]["decision"] == "NO_PAGAR"


async def test_three_invalid_decisions_give_502(case, monkeypatch) -> None:
    script(monkeypatch, [{**SUGGESTION, "decision": "REJECT"}] * 3)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.get(f"/instances/{case['escalated']}/suggestion")
    assert r.status_code == 502, r.text
    assert r.json()["code"] == "llm_error"


async def test_no_llm_key_gives_502(case, monkeypatch) -> None:
    for key in ("HELMCODE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.setenv(key, "")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.get(f"/instances/{case['escalated']}/suggestion")
    assert r.status_code == 502, r.text
    assert r.json()["code"] == "llm_error"


async def test_not_escalated_gives_409(case, monkeypatch) -> None:
    script(monkeypatch, [])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.get(f"/instances/{case['pending']}/suggestion")
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "conflict"
        r = await api.get("/instances/0/suggestion")
        assert r.status_code == 404, r.text


async def test_a_long_answer_is_sent_back(case, monkeypatch) -> None:
    """Concise by contract: over the character caps (schema) or the sentence limits
    (validator), the model is asked again."""
    essay = {
        **SUGGESTION,
        "why": ["Se escaló por el importe. Además hay otras cosas que contar aquí."],
        "reasoning": "x" * 400,
    }
    calls = script(monkeypatch, [essay, {**essay, "reasoning": "Corto."}, SUGGESTION])
    async with session_factory() as s:
        suggestion = await assistant.suggest(s, case["escalated"])
    assert suggestion == assistant.Suggestion(**SUGGESTION)
    first, second = retry_prompts(calls[-1])
    assert "at most 320 characters" in first
    assert "Be concise: why[0] must be one line and one sentence" in second


async def test_every_option_carries_its_rule(case, monkeypatch) -> None:
    bare = {**SUGGESTION, "options": [{**SUGGESTION["options"][0], "rule": None}]}
    bare["options"].append(SUGGESTION["options"][1])
    calls = script(monkeypatch, [bare, SUGGESTION])
    async with session_factory() as s:
        suggestion = await assistant.suggest(s, case["escalated"])
    assert all(o.rule for o in suggestion.options)
    [retry] = retry_prompts(calls[-1])
    assert "every option needs the rule that justifies it: ['PAGAR']" in retry


async def test_no_rule_is_a_valid_answer(case, monkeypatch) -> None:
    half = {**NO_RULE, "proposed_rule": "Pay it."}  # no rule and a rule at once
    calls = script(monkeypatch, [half, {**NO_RULE, "no_rule_reason": None}, NO_RULE])
    async with session_factory() as s:
        suggestion = await assistant.suggest(s, case["escalated"])
    assert suggestion.proposed_rule is None and suggestion.no_rule_reason.startswith("Falta")
    assert suggestion.decision == "NO_PAGAR"  # still a final decision
    first, second = retry_prompts(calls[-1])
    assert "proposed_rule must be null" in first and "or no_rule_reason" in second
