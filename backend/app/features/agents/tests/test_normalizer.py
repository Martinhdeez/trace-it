"""The normalizer: its output validator (scripted model, no database) and the norm endpoint
(against the local database, `make test-db`)."""

import asyncio
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.database import engine, session_factory
from app.core.events import Event
from app.features.agents import llm, normalizer
from app.features.agents.tests.test_assistant import _db_available
from app.features.processes.model import DecisionType, Symbol
from app.features.rules import service as rules_service
from app.features.rules.model import Rule
from app.main import app
from tests.support.models import per_role, retry_prompts, user_prompt

TYPES = [
    DecisionType(name="ESCALAR", priority=3, is_default=False, requires_human=True),
    DecisionType(name="NO_PAGAR", priority=2, is_default=False, requires_human=False),
    DecisionType(name="PAGAR", priority=1, is_default=True, requires_human=False),
]
SYMBOLS = [Symbol(name="iban", type="text", description="IBAN on the invoice.")]
SOURCES = {"suppliers": [{"nif": "B1", "iban": "ES00"}]}
ACTIVE = [Rule(id=7, text="`iban` is not empty.")]
NORM = "1. Pagar solo si el IBAN coincide con el maestro. Ante duda, escalar."

CHECK = {
    "text": "`iban` equals `suppliers.iban` of the issuer's row.",
    "type": "requirement",
    "decision": "NO_PAGAR",
    "interpretation": "'Pay only if' means do not pay when it fails.",
}


def answer(checks: list[dict] | None = None, covered: list[int] | None = None) -> dict:
    sentence = {
        "number": 1,
        "text": "Pagar solo si el IBAN coincide con el maestro.",
        "checks": [CHECK] if checks is None else checks,
        "policies": ["When in doubt, escalate."],
        "covered": covered or [],
    }
    return {"norm_rules": [sentence]}


async def run(monkeypatch, replies: list[dict]) -> tuple[normalizer.Normalization, list]:
    seen: dict = {}
    monkeypatch.setattr(llm, "model_for", per_role({"normalizer": replies}, seen))
    output, _ = await normalizer.normalize(NORM, "Conventions", TYPES, SYMBOLS, SOURCES, ACTIVE)
    return output, seen["normalizer"]


async def test_sees_the_whole_context(monkeypatch) -> None:
    output, calls = await run(monkeypatch, [answer(covered=[7])])

    assert output.norm_rules[0].checks[0].decision == "NO_PAGAR"
    prompt = user_prompt(calls[0])
    for part in (NORM, "Conventions", "PAGAR, 1, True, False", "iban (text)", "- 7: `iban`"):
        assert part in prompt
    assert "suppliers: columns ['nif', 'iban']" in prompt


@pytest.mark.parametrize(
    ("bad", "complaint"),
    [
        (answer([{**CHECK, "decision": "REJECT"}]), "'REJECT' is not a decision type"),
        (answer([{**CHECK, "decision": "PAGAR"}]), "decides the default 'PAGAR'"),
        (answer([CHECK, {**CHECK, "decision": "ESCALAR"}]), "check texts must be unique"),
        (answer([{**CHECK, "text": "`iban` is not empty."}]), "already active rules"),
        (answer(covered=[99]), "names rules that do not exist: [99]"),
        ({"norm_rules": [{"number": 1, "text": "x"}]}, "have no check"),
    ],
)
async def test_invalid_answers_are_retried(monkeypatch, bad: dict, complaint: str) -> None:
    output, calls = await run(monkeypatch, [bad, answer()])

    assert output == normalizer.Normalization.model_validate(answer())
    assert complaint in retry_prompts(calls[-1])[0]


# --- The endpoint -------------------------------------------------------------------------

needs_db = pytest.mark.skipif(not _db_available(), reason="Local Postgres not available")

PROCESS = {
    "decision_types": [
        {"name": "ESCALAR", "priority": 3, "requires_human": True},
        {"name": "NO_PAGAR", "priority": 2},
        {"name": "PAGAR", "priority": 1, "is_default": True},
    ],
    "symbols": [{"name": "iban", "type": "text"}],
}


@pytest.fixture
async def api():
    suffix = uuid.uuid4().hex[:8]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {}
        for role in ("manager", "operator"):
            r = await client.post(
                "/users", json={"name": role, "email": f"{role}-{suffix}@x.com", "role": role}
            )
            headers[role] = {"X-User-Id": str(r.json()["id"])}
        r = await client.post("/processes/definition", json={"name": f"norm-{suffix}", **PROCESS})
        yield client, r.json()["process"]["id"], headers
    await engine.dispose()  # connections are bound to this test's event loop


CODE = """
def evaluate(instance, sources, others):
    return {"fires": not instance.get("iban"), "reason": "NO_IBAN"}
"""
TESTS = [
    {
        "name": f"iban {iban!r}",
        "instance_json": json.dumps({"iban": iban}),
        "sources_json": "{}",
        "others_json": "[]",
        "fires": not iban,
    }
    for iban in ["", "ES1", "ES2", "ES3", "ES4", "ES5"]
]


@needs_db
async def test_the_norm_becomes_norm_rules_whose_checks_compile(api, monkeypatch) -> None:
    """Three checks in two norm rules: all compiled concurrently in one background job,
    each keeping the normalizer's reading next to the compiler's report."""
    client, process_id, headers = api
    second = {**CHECK, "text": "`iban` is a valid IBAN.", "decision": "ESCALAR"}
    third = {**CHECK, "text": "`iban` is not blacklisted."}
    reply = answer([CHECK, second])
    reply["norm_rules"].append(
        {"number": 2, "text": "Nunca pagar a la lista negra.", "checks": [third]}
    )
    scripts = {
        "normalizer": [reply],
        "tester": [{"tests": TESTS}] * 3,
        "compiler": [{"code": CODE}] * 3,
    }
    monkeypatch.setattr(llm, "model_for", per_role(scripts))

    r = await client.post(
        f"/processes/{process_id}/norm", json={"text": NORM}, headers=headers["manager"]
    )

    assert r.status_code == 201, r.text
    first, other = r.json()["norm_rules"]
    assert first["policies"] == ["When in doubt, escalate."]
    ids = [c["rule_id"] for n in (first, other) for c in n["checks"]]
    for rule_id in ids:
        rule = (await client.get(f"/rules/{rule_id}")).json()
        assert rule["status"] == "active", rule["report"]
        assert rule["code"] == CODE
        assert rule["report"]["valid"] is True
        assert rule["report"]["norm"]["interpretation"] == CHECK["interpretation"]
    rule = (await client.get(f"/rules/{ids[0]}")).json()
    assert rule["norm_rule_id"] == first["id"]
    assert rule["report"]["norm"]["policies"] == ["When in doubt, escalate."]

    norm_rules = (await client.get(f"/processes/{process_id}/norm-rules")).json()
    assert [n["text"] for n in norm_rules] == [first["text"], "Nunca pagar a la lista negra."]
    assert [(c["id"], c["decision"], c["status"]) for c in norm_rules[0]["rules"]] == [
        (ids[0], "NO_PAGAR", "active"),
        (ids[1], "ESCALAR", "active"),
    ]
    async with session_factory() as s:
        event = await s.scalar(
            select(Event).where(Event.step == "normalize_norm").order_by(Event.id.desc()).limit(1)
        )
    assert event.data["model"] == "fake/model"
    assert event.data["output"]["norm_rules"][0]["number"] == 1


async def test_compilations_run_concurrently_up_to_the_limit(monkeypatch) -> None:
    running, peak = 0, 0

    async def compile_one(rule_id: int) -> None:
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.01)
        running -= 1

    monkeypatch.setattr(rules_service, "compile_in_background", compile_one)
    monkeypatch.setattr(settings, "compile_concurrency", 3)

    await rules_service.compile_all_in_background(list(range(8)))

    assert peak == 3


@needs_db
async def test_an_operator_cannot_change_the_norm(api, monkeypatch) -> None:
    client, process_id, headers = api
    monkeypatch.setattr(llm, "model_for", per_role({"normalizer": []}))

    r = await client.post(
        f"/processes/{process_id}/norm", json={"text": NORM}, headers=headers["operator"]
    )

    assert r.status_code == 403, r.text
    assert (await client.get(f"/processes/{process_id}/norm-rules")).json() == []
