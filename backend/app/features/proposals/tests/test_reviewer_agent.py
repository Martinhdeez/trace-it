"""The reviewer agent (ADR 0035): after a person resolves an escalated case, it amends the
escalation rule that fired so similar cases get that decision. Through the API, sandbox
faked, models scripted: no LLM key."""

import uuid

import pytest
from sqlalchemy import select

from app.core.database import session_factory
from app.core.events import Event
from app.features.agents import compiler, llm, sandbox
from app.features.decisions.engine import Outcomes
from app.features.decisions.model import Decision
from app.features.decisions.tests.test_api import RULES_V3, client, create_process, stored
from app.features.ingestion.model import File, Instance
from app.features.proposals.service import learnable
from app.features.versions.tests.test_api import publish, validate
from tests.support.fakes import dataset_runner
from tests.support.models import instructions, per_role, retry_prompts, user_json

OUTCOMES = Outcomes({"ESCALAR": 3, "NO_PAGAR": 2, "PAGAR": 1}, "PAGAR", "ESCALAR")
HUMAN = {"ESCALAR"}
DECISIONS = {1: "ESCALAR", 2: "NO_PAGAR", 3: "ESCALAR"}


def results(*fired: int, failed: str | None = None) -> list[dict]:
    rows = [{"rule_id": i, "fires": i in fired, "reason": ""} for i in DECISIONS]
    if failed:
        rows[0] = {"rule_id": 1, "fires": None, "reason": failed}
    return rows


@pytest.mark.parametrize(
    ("reason", "rows", "why"),
    [
        ("MISSING_DATA: iban", results(), "Faltaba un dato obligatorio (iban)"),
        ("UNVERIFIED_DATA: total", results(), "no se pudo confirmar total"),
        ("SOURCE_UNAVAILABLE: erp", results(), "No se pudo consultar erp"),
        ("RULE_CONFLICT: A, B share priority 2", results(), "Dos reglas"),
        ("SCAN_REVIEW: x", results(2), "escaneo"),
        ("RULE_ERROR 1: boom", results(failed="RULE_ERROR 1: boom"), "(RULE_ERROR)"),
        ("RULE_NEEDS_DATA 1: x", results(failed="RULE_NEEDS_DATA 1: x"), "(RULE_NEEDS_DATA)"),
        ("x", results(1, 3), "varias reglas de escalado (1, 3)"),
        ("x", results(), "Ninguna regla de escalado"),
        ("x", results(1, 2), "decidiría NO_PAGAR, no PAGAR"),
    ],
)
def test_what_no_amendment_can_learn(reason, rows, why):
    rule, message = learnable(reason, rows, DECISIONS, OUTCOMES, HUMAN, "PAGAR")
    assert rule is None and why in message


def test_one_escalation_rule_over_the_persons_decision_is_learnable():
    assert learnable("IBAN", results(1), DECISIONS, OUTCOMES, HUMAN, "PAGAR") == (1, "")
    # NO_PAGAR only when a rejection rule fired too: then the amendment is enough.
    assert learnable("IBAN", results(1, 2), DECISIONS, OUTCOMES, HUMAN, "NO_PAGAR") == (1, "")


SUGGESTION = {
    "text": "The iban differs from every iban the suppliers master has for that nif, "
    "unless the erp order is still PENDIENTE.",
    "type": "prohibition",
    "summary": "Escala un IBAN distinto del maestro salvo si el pedido sigue pendiente",
    "rationale": "La persona pagó porque el pedido seguía pendiente en el ERP.",
    "evidence": ["symbol:iban", "symbol:purchase_order"],
}


async def resolved(api, monkeypatch, replies, decision="PAGAR"):
    """FA-5044 escalated by `iban_mismatch` alone, resolved by Ana; the agent scripted."""
    monkeypatch.setattr(sandbox, "run_dataset", dataset_runner(RULES))
    pid, headers = await create_process(api, "manager")
    assert (await api.post(f"/processes/{pid}/run")).status_code == 200
    [case] = (await api.get(f"/processes/{pid}/queue")).json()
    r = await api.post(
        f"/instances/{case['id']}/resolve",
        json={"decision": decision, "reason": "The order is still pending: paid"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    seen: dict = {}
    monkeypatch.setattr(llm, "model_for", per_role({"assistant": replies}, seen))
    return pid, headers, case["id"], seen


async def suggest(api, iid, headers):
    r = await api.post(f"/instances/{iid}/rule-proposal", headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def rule_id(api, pid, text):
    return next(
        r["id"] for r in (await api.get(f"/processes/{pid}/rules")).json() if r["text"] == text
    )


async def test_the_suggestion_amends_the_rule_that_escalated(monkeypatch):
    async with client() as api:
        pid, headers, iid, seen = await resolved(api, monkeypatch, [SUGGESTION])
        proposal = await suggest(api, iid, headers)
        iban = await rule_id(api, pid, "iban_mismatch")
        detail = (await api.get(f"/instances/{iid}")).json()

    engine, resolution = detail["decisions"]
    assert (proposal["channel"], proposal["kind"], proposal["status"]) == (
        "escalation",
        "rule",
        "open",
    )
    assert proposal["summary"] == SUGGESTION["summary"]
    assert proposal["rationale"] == SUGGESTION["rationale"]
    assert proposal["payload"] == {
        "decision_id": resolution["id"],
        "engine_decision_id": engine["id"],
        "replaces": iban,
        "text": SUGGESTION["text"],
        "summary": SUGGESTION["summary"],
        "type": "prohibition",
        "decision": "ESCALAR",
        "resolved_as": "PAGAR",
        "version_id": engine["version_id"],
    }
    [messages] = seen["assistant"]
    context = user_json(messages)
    assert context["escalation"]["rule"]["id"] == iban
    assert context["resolution"]["decision"] == "PAGAR"
    assert "file_text" not in context["case"]  # a small context: no file text
    assert "Generalise, never describe this case" in instructions(messages)
    [span] = [e for e in detail["events"] if e["step"] == "suggest_rule"]
    assert span["data"]["replaces"] == iban and span["data"]["proposal_id"] == proposal["id"]


async def test_a_rule_that_names_the_case_is_sent_back(monkeypatch):
    naming = {**SUGGESTION, "text": "Pay FA-5044_mensajería2 even if the iban differs."}
    async with client() as api:
        _, headers, iid, seen = await resolved(api, monkeypatch, [naming, SUGGESTION])
        proposal = await suggest(api, iid, headers)
    assert proposal["payload"]["text"] == SUGGESTION["text"]
    [retry] = retry_prompts(seen["assistant"][-1])
    assert "names this case" in retry and "FA-5044_mensajería2" in retry


async def test_a_case_no_rule_can_learn_is_409_in_spanish_and_spends_nothing(monkeypatch):
    async with client() as api:
        pid, headers, iid, seen = await resolved(api, monkeypatch, [])
        async with session_factory() as session:  # the case escalates again: missing data
            [engine] = await session.scalars(
                select(Decision).where(Decision.instance_id == iid, Decision.author == "engine")
            )
            session.add(
                Decision(
                    instance_id=iid,
                    decision="ESCALAR",
                    results=[],
                    rules_hash=engine.rules_hash,
                    version_id=engine.version_id,
                    author="engine",
                    reason="MISSING_DATA: iban",
                )
            )
            await session.commit()
        unresolved = await api.post(f"/instances/{iid}/rule-proposal", headers=headers)
        r = await api.post(
            f"/instances/{iid}/resolve", json={"decision": "PAGAR", "reason": "Called"}
        )
        assert r.status_code == 200, r.text
        missing = await api.post(f"/instances/{iid}/rule-proposal", headers=headers)
        listed = (await api.get(f"/processes/{pid}/proposals", headers=headers)).json()
        spans = (await api.get(f"/processes/{pid}/events", params={"step": "suggest_rule"})).json()

    assert unresolved.status_code == 409 and "Resuelve el caso" in unresolved.json()["message"]
    assert missing.status_code == 409
    assert "Faltaba un dato obligatorio (iban)" in missing.json()["message"]
    assert seen == {"assistant": []} and listed == []  # the model was never called
    assert spans[0]["status"] == "error" and spans[0]["data"]["learnable"] is False


async def test_ignored_and_rejected_suggestions_differ(monkeypatch):
    """Rejected: the manager said no, with a reason. Ignored: the manager moved on and
    resolved another case; the suggestion closes as `superseded`, cause `ignored`."""
    async with client() as api:
        pid, headers, iid, _ = await resolved(api, monkeypatch, [SUGGESTION, SUGGESTION])
        first = await suggest(api, iid, headers)
        r = await api.post(
            f"/proposals/{first['id']}/reject", json={"reason": "Too broad"}, headers=headers
        )
        assert r.status_code == 200, r.text
        second = await suggest(api, iid, headers)
        other = next(
            i["id"]
            for i in (await api.get(f"/processes/{pid}/instances")).json()
            if i["name"] == "factura_1217.pdf"
        )
        r = await api.post(
            f"/instances/{other}/resolve",
            json={"decision": "PAGAR", "reason": "Fine"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        listed = {p["id"]: p for p in (await api.get(f"/processes/{pid}/proposals")).json()}
        late = await api.post(f"/proposals/{second['id']}/accept", headers=headers)
        expired = (
            await api.get(f"/processes/{pid}/events", params={"step": "expire_proposal"})
        ).json()

    rejected, ignored = listed[first["id"]], listed[second["id"]]
    assert (rejected["status"], rejected["outcome"]) == ("rejected", {"reason": "Too broad"})
    assert (ignored["status"], ignored["outcome"]) == ("superseded", {"cause": "ignored"})
    assert late.status_code == 409
    assert [e["data"] for e in expired] == [{"proposal_ids": [second["id"]], "cause": "ignored"}]


def compiled(code: str):
    """`compiler.compile_rule` answering with `code`: the amended code set by hand."""

    async def compile_rule(session, rule, symbols):
        return compiler.Compilation(code, [], {"valid": True})

    return compile_rule


async def test_accepting_stages_the_amended_rule_in_place_of_the_old_one(monkeypatch):
    """BE-3: accept creates the rule in the draft, retires `replaces` there, compiles it."""
    monkeypatch.setattr(compiler, "compile_rule", compiled("iban_unless_pending"))
    async with client() as api:
        pid, headers, iid, _ = await resolved(api, monkeypatch, [SUGGESTION])
        proposal = await suggest(api, iid, headers)
        r = await api.post(f"/proposals/{proposal['id']}/accept", headers=headers)
        assert r.status_code == 200, r.text
        accepted = r.json()
        draft = (await api.get(f"/processes/{pid}/draft", headers=headers)).json()
        rule = (await api.get(f"/rules/{accepted['outcome']['rule_id']}")).json()
        active = (await api.get(f"/processes/{pid}")).json()["active_version_id"]

    outcome = accepted["outcome"]
    assert accepted["status"] == "accepted" and accepted["resolved_by"] == "Ana"
    assert outcome["retired"] == proposal["payload"]["replaces"]
    assert outcome["draft_revision"] == draft["revision"] - 1  # then the compile refreshed it
    ids = [r["id"] for r in draft["snapshot"]["rules"]]
    assert outcome["rule_id"] in ids and outcome["retired"] not in ids
    assert (rule["text"], rule["decision"], rule["summary"]) == (
        SUGGESTION["text"],
        "ESCALAR",
        SUGGESTION["summary"],
    )
    assert rule["status"] == "draft" and rule["code"] == "iban_unless_pending"  # compiled
    assert active == proposal["payload"]["version_id"]  # nothing published by accepting
    async with session_factory() as s:
        span = await s.scalar(
            select(Event).where(Event.step == "accept_proposal").order_by(Event.id.desc())
        )
        steps = set(await s.scalars(select(Event.step).where(Event.trace_id == span.trace_id)))
    assert {"accept_proposal", "save_rule", "retire_rule", "compile_rules", "compile_rule"} <= steps


# BE-4: the program learns. Two hotel invoices at 10 % VAT escalate under "VAT other than
# 21"; a person pays one, the reviewer agent amends the rule, the manager accepts, validates
# and publishes, and a reprocess pays the other one by the engine (the demo's fallback pair,
# docs/reviewer-agent.md).
RULES = {
    **{name: fn for name, (_, fn) in RULES_V3.items()},
    "vat_rate": lambda i, s, o: i.get("vat_rate", 21) != 21,
    "vat_rate_amended": lambda i, s, o: i.get("vat_rate", 21) not in (21, 10),
    "iban_unless_pending": lambda i, s, o: False,
}
HOTEL = {**{"nif": "B96233419", "iban": "ES2100752345670600123456"}, "vat_rate": 10}
LEARNED = {
    "text": "The printed vat_rate is other than 21 and other than 10 (the reduced rate "
    "for hotel and catering services).",
    "type": "prohibition",
    "summary": "Escala un IVA distinto del 21 % y del 10 %",
    "rationale": "La persona pagó porque la hostelería tributa al 10 %; se escalan los demás.",
    "evidence": ["symbol:vat_rate"],
}


async def test_the_program_learns_from_a_resolved_escalation(monkeypatch):
    monkeypatch.setattr(sandbox, "run_dataset", dataset_runner(RULES))
    monkeypatch.setattr(sandbox, "check", lambda code: None)
    monkeypatch.setattr(compiler, "read_keys", lambda code: (set(), set()))
    monkeypatch.setattr(compiler, "compile_rule", compiled("vat_rate_amended"))
    rules = {n: (d, n) for n, (d, _) in RULES_V3.items()} | {"vat_rate": ("ESCALAR", "vat_rate")}
    async with client() as api:
        pid, headers = await create_process(api, "manager", rules)
        async with session_factory() as session:
            for name, order in (("hotel_a.pdf", "PO-2026-0008"), ("hotel_b.pdf", "PO-2026-0813")):
                digest = uuid.uuid4().hex
                session.add(File(hash=digest, name=name, content=b"%PDF", text=""))
                symbols = stored({**HOTEL, "purchase_order": order, "invoice_number": name[:7]})
                session.add(Instance(process_id=pid, file_hash=digest, name=name, symbols=symbols))
            await session.commit()
        assert (await api.post(f"/processes/{pid}/run")).status_code == 200
        cases = {i["name"]: i for i in (await api.get(f"/processes/{pid}/instances")).json()}
        a, b = cases["hotel_a.pdf"], cases["hotel_b.pdf"]
        assert (a["decision"], b["decision"]) == ("ESCALAR", "ESCALAR")

        # The person pays one; the reviewer agent amends the rule that escalated it.
        r = await api.post(
            f"/instances/{a['id']}/resolve",
            json={"decision": "PAGAR", "reason": "La hostelería tributa al 10 %"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        monkeypatch.setattr(llm, "model_for", per_role({"assistant": [LEARNED]}))
        proposal = await suggest(api, a["id"], headers)
        assert proposal["payload"]["replaces"] == await rule_id(api, pid, "vat_rate")

        # Accept: staged and compiled (the amended code, by hand). Then validate.
        r = await api.post(f"/proposals/{proposal['id']}/accept", headers=headers)
        assert r.status_code == 200, r.text
        report = (await validate(api, pid, headers))["validation"]
        assert report["valid"], report
        [mine] = report["resolved_by_person"]
        assert (mine["name"], mine["after"], mine["resolution"]) == (
            "hotel_a.pdf",
            "PAGAR",
            "PAGAR",
        )
        assert [(c["name"], c["before"], c["after"]) for c in report["changes"]] == [
            ("hotel_b.pdf", "ESCALAR", "PAGAR")
        ]

        # Publish, then next time: the sibling is decided by the engine, hers stays hers.
        await publish(api, pid, headers)
        r = await api.post(f"/processes/{pid}/reprocess")
        assert r.status_code == 200, r.text
        assert [(c["name"], c["after"]) for c in r.json()["changes"]] == [("hotel_b.pdf", "PAGAR")]
        sibling = (await api.get(f"/instances/{b['id']}")).json()
        mine = (await api.get(f"/instances/{a['id']}")).json()

    assert [(d["author"], d["decision"]) for d in sibling["decisions"]] == [
        ("engine", "ESCALAR"),
        ("engine", "PAGAR"),
    ]
    assert [(d["author"], d["decision"]) for d in mine["decisions"]] == [
        ("engine", "ESCALAR"),
        ("Ana", "PAGAR"),
    ]


async def test_the_e2e_can_seed_a_suggestion_without_a_model(monkeypatch):
    """`python -m tests.support.proposals rule <instance_id> <text>`, for Playwright."""
    from tests.support.proposals import store

    async with client() as api:
        pid, headers, iid, seen = await resolved(api, monkeypatch, [])
        proposal_id = await store("rule", iid, SUGGESTION["text"])
        [listed] = (await api.get(f"/processes/{pid}/proposals?status=open")).json()
        iban = await rule_id(api, pid, "iban_mismatch")
    assert listed["id"] == proposal_id
    assert (listed["channel"], listed["kind"]) == ("escalation", "rule")
    assert listed["payload"]["replaces"] == iban and listed["payload"]["resolved_as"] == "PAGAR"
    assert seen == {"assistant": []}
