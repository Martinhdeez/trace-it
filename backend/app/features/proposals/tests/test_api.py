"""The three proposal channels behind one contract, through the API. Models are scripted."""

import copy

import pytest
from sqlalchemy import select

from app.core.database import session_factory
from app.core.events import Event
from app.features.agents import llm, sandbox
from app.features.decisions.tests.test_api import FAKE_SANDBOX, client, create_process
from app.features.learning.tests.test_api import norm, prepare, scripts, seed
from app.features.processes.tests.test_drafts import api as api
from app.features.processes.tests.test_drafts import post, prepare_new
from tests.support.models import per_role, user_json
from tests.support.users import anonymous

PROPOSAL = {
    "decision": "NO_PAGAR",
    "reasoning": "The purchase order was already paid.",
    "why": ["Two rules disagree about this invoice, so a person must look at it."],
    "options": [
        {
            "decision": "PAGAR",
            "consequence": "Se paga si se añade la regla: un pedido pendiente en el ERP no escala.",
            "rule": "Amend the conflict: an erp order still PENDIENTE does not escalate.",
        },
        {
            "decision": "NO_PAGAR",
            "consequence": "No se paga por la regla nueva: el pedido ya está pagado en el ERP.",
            "rule": "If the purchase order is paid in the ERP, do not pay.",
        },
    ],
    "evidence": ["symbol:purchase_order", "escalation"],
    "proposed_rule": "If the purchase order is paid in the ERP, do not pay.",
    "proposed_type": "prohibition",
}


async def escalated(api, monkeypatch, replies):
    monkeypatch.setattr(sandbox, "run_dataset", FAKE_SANDBOX)
    pid, headers = await create_process(api, "manager")
    assert (await api.post(f"/processes/{pid}/run")).status_code == 200
    [case] = (await api.get(f"/processes/{pid}/queue")).json()
    seen = {}
    monkeypatch.setattr(llm, "model_for", per_role({"assistant": replies}, seen))
    return pid, headers, case["id"], seen


async def propose(api, iid, headers):
    r = await api.post(f"/instances/{iid}/proposal", headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def test_escalation_proposal_is_structured_and_accepting_resolves(monkeypatch):
    async with client() as api:
        pid, headers, iid, seen = await escalated(api, monkeypatch, [PROPOSAL])
        proposal = await propose(api, iid, headers)
        listed = (await api.get(f"/processes/{pid}/proposals?status=open", headers=headers)).json()
        r = await api.post(
            f"/proposals/{proposal['id']}/accept", json={"reason": "Agreed"}, headers=headers
        )
        assert r.status_code == 200, r.text
        accepted = r.json()
        again = await api.post(f"/proposals/{proposal['id']}/accept", headers=headers)
        detail = (await api.get(f"/instances/{iid}")).json()

    assert "symbol:purchase_order" in user_json(seen["assistant"][0])["evidence_refs"]
    assert (proposal["channel"], proposal["kind"], proposal["status"]) == (
        "escalation",
        "decision",
        "open",
    )
    payload = proposal["payload"]
    assert payload["proposed"] == "NO_PAGAR" and payload["escalated_as"] == "ESCALAR"
    assert payload["why"] and [o["decision"] for o in payload["options"]] == ["PAGAR", "NO_PAGAR"]
    assert payload["options"][1]["rule"] == PROPOSAL["proposed_rule"]
    assert payload["proposed_rule"] == {"text": PROPOSAL["proposed_rule"], "type": "prohibition"}
    assert payload["no_rule_reason"] is None
    assert proposal["evidence"] == ["symbol:purchase_order", "escalation"]
    assert [p["id"] for p in listed] == [proposal["id"]]
    assert accepted["status"] == "accepted" and accepted["resolved_by"] == "Ana"
    assert again.status_code == 409
    last = detail["decisions"][-1]
    assert (last["decision"], last["author"], last["reason"]) == ("NO_PAGAR", "Ana", "Agreed")
    assert accepted["outcome"] == {"decision_id": last["id"], "decision": "NO_PAGAR"}
    resolution = next(e for e in detail["events"] if e["step"] == "resolution")
    assert resolution["data"]["proposal_id"] == proposal["id"]
    async with session_factory() as s:
        steps = set(
            await s.scalars(select(Event.step).where(Event.trace_id == resolution["trace_id"]))
        )
    assert {"accept_proposal", "resolution"} <= steps


async def test_escalation_options_must_cover_every_final_decision(monkeypatch):
    partial = {**PROPOSAL, "options": PROPOSAL["options"][1:]}
    async with client() as api:
        _, headers, iid, seen = await escalated(api, monkeypatch, [partial, PROPOSAL])
        proposal = await propose(api, iid, headers)
    assert len(seen["assistant"]) == 2 and len(proposal["payload"]["options"]) == 2


async def test_rejecting_or_resolving_otherwise_never_decides_for_the_manager(monkeypatch):
    async with client() as api:
        pid, headers, iid, _ = await escalated(api, monkeypatch, [PROPOSAL] * 3)
        first = await propose(api, iid, headers)
        second = await propose(api, iid, headers)  # supersedes the first
        r = await api.post(f"/proposals/{second['id']}/reject", headers=headers)
        assert r.status_code == 200, r.text
        rejected = r.json()
        still = (await api.get(f"/instances/{iid}")).json()
        third = await propose(api, iid, headers)
        body = {"decision": "PAGAR", "reason": "Paid by agreement", "proposal_id": third["id"]}
        r = await api.post(f"/instances/{iid}/resolve", json=body, headers=headers)
        assert r.status_code == 200, r.text
        stale = await api.post(
            f"/instances/{iid}/resolve",
            json={**body, "proposal_id": first["id"]},
            headers=headers,
        )
        everything = (await api.get(f"/processes/{pid}/proposals", headers=headers)).json()

    assert rejected["status"] == "rejected" and still["decision"] == "ESCALAR"
    assert stale.status_code == 409
    status = {p["id"]: p["status"] for p in everything}
    assert status == {first["id"]: "superseded", second["id"]: "rejected", third["id"]: "rejected"}
    overridden = next(p for p in everything if p["id"] == third["id"])
    assert overridden["outcome"]["decision"] == "PAGAR"


async def test_resolving_without_the_proposal_closes_it_as_superseded_with_a_cause(monkeypatch):
    """BE-1: a resolved case has no open proposal; `superseded` + cause is not `rejected`."""
    async with client() as api:
        pid, headers, iid, _ = await escalated(api, monkeypatch, [PROPOSAL])
        proposal = await propose(api, iid, headers)
        body = {"decision": "PAGAR", "reason": "Checked by phone"}
        assert (await api.post(f"/instances/{iid}/resolve", json=body)).status_code == 200
        listed = (await api.get(f"/processes/{pid}/proposals", headers=headers)).json()
        detail = (await api.get(f"/instances/{iid}")).json()

    [closed] = listed
    assert closed["id"] == proposal["id"]
    assert (closed["status"], closed["outcome"]) == ("superseded", {"cause": "case_changed"})
    [expired] = [e for e in detail["events"] if e["step"] == "expire_proposal"]
    assert expired["data"] == {"proposal_ids": [proposal["id"]], "cause": "case_changed"}


async def test_a_no_rule_answer_is_stored_without_a_rule(monkeypatch):
    no_rule = {
        **PROPOSAL,
        "proposed_rule": None,
        "proposed_type": None,
        "no_rule_reason": "Dos reglas chocan y solo una persona sabe cuál manda aquí.",
    }
    async with client() as api:
        _, headers, iid, _ = await escalated(api, monkeypatch, [no_rule])
        proposal = await propose(api, iid, headers)
    payload = proposal["payload"]
    assert payload["proposed_rule"] is None
    assert payload["no_rule_reason"] == no_rule["no_rule_reason"]
    assert payload["proposed"] == "NO_PAGAR"  # the decision is still proposed


async def test_an_answer_that_arrives_after_a_resolution_is_not_stored(monkeypatch):
    """R04: the case is resolved while the model answers; nothing stays open, 409."""
    from app.features.agents import assistant
    from app.features.agents.assistant import Suggestion

    async with client() as api:
        pid, headers, iid, _ = await escalated(api, monkeypatch, [])

        async def slow_suggest(session, instance_id):
            r = await api.post(
                f"/instances/{instance_id}/resolve",
                json={"decision": "PAGAR", "reason": "Resolved meanwhile"},
                headers=headers,
            )
            assert r.status_code == 200, r.text
            return Suggestion.model_validate(PROPOSAL)

        monkeypatch.setattr(assistant, "suggest", slow_suggest)
        late = await api.post(f"/instances/{iid}/proposal", headers=headers)
        listed = (await api.get(f"/processes/{pid}/proposals", headers=headers)).json()
        detail = (await api.get(f"/instances/{iid}")).json()

    assert late.status_code == 409 and "ha cambiado" in late.json()["message"]
    assert listed == []
    assert [d["author"] for d in detail["decisions"]] == ["engine", "Ana"]


async def test_only_a_manager_settles(monkeypatch):
    async with client() as api:
        pid, headers, iid, _ = await escalated(api, monkeypatch, [PROPOSAL])
        proposal = await propose(api, iid, headers)
        r = await api.post(
            "/users", json={"name": "Op", "email": f"op-{iid}@x.com", "role": "operator"}
        )
        other = {"X-User-Id": str(r.json()["id"])}
        denied = await api.post(f"/proposals/{proposal['id']}/accept", headers=other)
        hidden = await api.get(f"/processes/{pid}/proposals", headers=other)
        missing = await api.post("/proposals/0/reject", headers=headers)
    nobody = await anonymous("POST", f"/proposals/{proposal['id']}/accept")
    assert denied.status_code == 403 and hidden.status_code == 403
    assert denied.json()["code"] == "permission_denied"
    assert nobody.status_code == 401 and nobody.json()["code"] == "unauthenticated"
    assert missing.status_code == 404


async def test_chat_proposes_every_kind_and_accepting_stages_the_draft(api, monkeypatch):
    initial = await post(api, await prepare_new(api, monkeypatch), "publish")
    pid = initial["published_process_id"]
    published = (await api.get(f"/processes/{pid}")).json()["active_version_id"]
    draft = (await api.post("/process-drafts", json={"process_id": pid})).json()
    changed = copy.deepcopy(draft["plan"])
    evidence = [{"reference": "chat:1", "explanation": "The manager asked for it"}]
    changed["description"] += " Amounts are in euros."
    changed["symbols"].append({"name": "currency", "type": "text"})
    changed["rules"][0]["text"] = "amount is greater than 150."
    changed["rules"][0]["evidence"] = evidence
    changed["sources"].append(
        {
            "name": "limits",
            "kind": "constant",
            "rows": [{"limit": 150}],
            "explanation": "The manager's limit table",
            "evidence": evidence,
        }
    )
    monkeypatch.setattr(llm, "model_for", per_role({"discovery": [changed]}))
    draft = await post(api, draft, "messages", message="Raise the limit, add currency and limits.")

    listed = (await api.get(f"/processes/{pid}/proposals?status=open")).json()
    kinds = {p["kind"]: p for p in listed}
    assert {p["channel"] for p in listed} == {"chat"}
    assert set(kinds) == {"context", "input", "rule", "source"}
    assert kinds["rule"]["payload"]["after"]["text"] == "amount is greater than 150."
    assert kinds["rule"]["evidence"] == ["chat:1"]
    assert kinds["input"]["payload"]["review_key"] == "setup"

    accept = await api.post(f"/proposals/{kinds['context']['id']}/accept")
    assert accept.json()["outcome"]["staged"] is False  # the input still shares `setup`
    for kind in ("input", "rule"):
        r = await api.post(f"/proposals/{kinds[kind]['id']}/accept", json={"reason": "Fine"})
        assert r.status_code == 200, r.text
        assert r.json()["outcome"]["staged"] is True
    r = await api.post(f"/proposals/{kinds['source']['id']}/reject", json={"reason": "Not yet"})
    assert r.status_code == 200, r.text
    reviews = (await api.get(f"/process-drafts/{draft['id']}")).json()["reviews"]
    rule_key = kinds["rule"]["payload"]["review_key"]
    assert reviews == {"setup": "accepted", rule_key: "accepted", "source:limits": "rejected"}
    # Nothing is published by accepting: that stays /prepare and /publish.
    process = (await api.get(f"/processes/{pid}")).json()
    assert process["active_version_id"] == published
    assert "currency" not in [s["name"] for s in process["symbols"]]

    # A new revision supersedes what is still open.
    draft = (await api.get(f"/process-drafts/{draft['id']}")).json()
    monkeypatch.setattr(llm, "model_for", per_role({"discovery": [changed]}))
    await post(api, draft, "messages", message="Again.")
    everything = (await api.get(f"/processes/{pid}/proposals")).json()
    first = {p["id"]: p["status"] for p in everything if p["id"] in {k["id"] for k in listed}}
    assert sorted(first.values()) == ["accepted", "accepted", "accepted", "rejected"]
    assert len([p for p in everything if p["status"] == "open"]) == 4


@pytest.fixture
def learned(monkeypatch):
    changes = [
        ("context", "", "", "An invoice without a purchase order is a service invoice."),
        ("input", "delivery_note", "text", "The delivery note number printed on the invoice."),
        ("source", "contracts", "", "Signed supplier contracts with their end date."),
    ]

    async def analyze(api, pid, headers, ref):
        reply = {
            "reasoning": "Review found a pattern and three gaps in the definition.",
            "proposals": [norm("deterministic", "Escalate invoices of nif B96233419.", ref)],
            "definition_changes": [
                {
                    "kind": k,
                    "name": n,
                    "type": t,
                    "text": text,
                    "reasoning": "Resolutions cite it.",
                    "evidence": [ref],
                }
                for k, n, t, text in changes
            ],
        }
        monkeypatch.setattr(llm, "model_for", per_role({"learner": [reply]}))
        r = await api.post(f"/processes/{pid}/learning", json={}, headers=headers)
        assert r.status_code == 201, r.text
        listed = (await api.get(f"/processes/{pid}/proposals", headers=headers)).json()
        return {p["kind"]: p for p in listed}, r.json()["proposals"][0]["id"]

    return analyze


async def test_learning_proposes_every_kind_and_the_manager_settles_each(monkeypatch, learned):
    async with client() as api:
        pid, headers, ref = await seed(api)
        kinds, norm_id = await learned(api, pid, headers, ref)
        assert set(kinds) == {"rule", "context", "input", "source"}
        assert {p["channel"] for p in kinds.values()} == {"learning"}
        assert kinds["rule"]["payload"]["norm_proposal_id"] == norm_id

        unvalidated = await api.post(f"/proposals/{kinds['rule']['id']}/accept", headers=headers)
        assert unvalidated.status_code == 409 and "validate" in unvalidated.text
        await prepare(api, monkeypatch, norm_id, headers, scripts())
        rule = await api.post(f"/proposals/{kinds['rule']['id']}/accept", headers=headers)
        assert rule.status_code == 200, rule.text
        version_id = rule.json()["outcome"]["version_id"]
        assert (await api.get(f"/processes/{pid}")).json()["active_version_id"] == version_id

        for kind in ("context", "input"):
            r = await api.post(f"/proposals/{kinds[kind]['id']}/accept", headers=headers)
            assert r.status_code == 200, r.text
        source = await api.post(f"/proposals/{kinds['source']['id']}/reject", headers=headers)
        draft = (await api.get(f"/processes/{pid}/draft", headers=headers)).json()
        active = (await api.get(f"/processes/{pid}")).json()

    assert source.json()["status"] == "rejected"
    process = draft["snapshot"]["process"]
    assert process["description"].endswith("a service invoice.")
    assert process["symbols"][-1]["name"] == "delivery_note"
    # Staged only: the published version is the adopted rule's, unchanged by the draft.
    assert active["active_version_id"] == version_id
    assert "delivery_note" not in [s["name"] for s in active["symbols"]]


async def test_rejecting_a_learned_norm_directly_settles_its_proposal(monkeypatch, learned):
    async with client() as api:
        pid, headers, ref = await seed(api)
        kinds, norm_id = await learned(api, pid, headers, ref)
        r = await api.post(
            f"/norm-proposals/{norm_id}/reject", json={"reason": "Too narrow"}, headers=headers
        )
        assert r.status_code == 201, r.text
        listed = (await api.get(f"/processes/{pid}/proposals", headers=headers)).json()
    rule = next(p for p in listed if p["id"] == kinds["rule"]["id"])
    assert rule["status"] == "rejected" and rule["outcome"]["reason"] == "Too narrow"
