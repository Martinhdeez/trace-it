"""Documents -> conversation -> reviewed rules -> compilation -> backtest -> publication."""

import copy
import io
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook
from sqlalchemy import func, select

from app.core.database import session_factory
from app.features.agents import llm
from app.features.decisions.model import Decision, Finding
from app.features.ingestion.model import File, Instance
from app.features.processes.draft_compilation import proposals
from app.features.processes.draft_schemas import DraftPlan
from app.features.processes.model import Process
from app.features.rules.model import Rule
from app.main import app
from tests.support.models import per_role, user_json


def plan(name=None, threshold=100, field="amount", default="PAY", review="REVIEW"):
    return {
        "name": name or f"discovery-{uuid.uuid4().hex[:10]}",
        "description": "Compare with Decimal(str(value)); missing required fields escalate.",
        "decision_types": [
            {"name": review, "priority": 2, "requires_human": True},
            {"name": default, "priority": 1, "is_default": True},
        ],
        "symbols": [{"name": field, "type": "number", "required": True}],
        "rules": [
            {
                "name": "limit",
                "text": f"{field} is greater than {threshold}.",
                "type": "prohibition",
                "decision": review,
                "evidence": [{"reference": "chat:1", "explanation": "Manager's threshold"}],
            }
        ],
        "examples": [
            {
                "name": "ordinary",
                "instance": {field: 20},
                "decision": default,
                "explanation": "Below the threshold",
            },
            {
                "name": "large",
                "instance": {field: 250},
                "decision": review,
                "explanation": "Above the threshold",
            },
            {
                "name": "missing",
                "instance": {},
                "decision": review,
                "explanation": "Required data missing",
            },
        ],
        "questions": [],
        "summary": "Proposed the threshold and its review examples.",
    }


def scripts(proposal, threshold=100, field="amount", broken=False):
    rule = proposal["rules"][0]
    normal = {
        "norm_rules": [
            {
                "number": 1,
                "text": f"{rule['text']} {rule['decision']}",
                "checks": [
                    {
                        "text": rule["text"],
                        "type": "prohibition",
                        "decision": rule["decision"],
                        "decision_source": "explicit",
                        "quote": rule["decision"],
                        "interpretation": "Escalate amounts above the confirmed threshold.",
                    }
                ],
            }
        ]
    }
    code = (
        "from decimal import Decimal\n"
        "def evaluate(instance, sources, others):\n"
        f"    fires = Decimal(str(instance['{field}'])) > {threshold}\n"
        "    return {'fires': fires, 'reason': 'LIMIT'}"
    )
    if broken:
        code = (
            "def evaluate(instance, sources, others):\n"
            "    return {'fires': False, 'reason': 'wrong'}"
        )
    tests = {
        "tests": [
            {
                "name": str(i),
                "instance_json": json.dumps({field: v}),
                "sources_json": "{}",
                "others_json": "[]",
                "fires": v > threshold,
            }
            for i, v in enumerate([0, 20, 40, 100, 200, 300])
        ]
    }
    return {
        "discovery": [proposal],
        "normalizer": [normal],
        "tester": [tests],
        "compiler": [{"code": code}] * (4 if broken else 1),
    }


@pytest.fixture
async def api():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await client.post(
            "/users",
            json={
                "name": "Draft manager",
                "role": "manager",
                "email": f"draft-{uuid.uuid4().hex}@test.com",
            },
        )
        client.headers["X-User-Id"] = str(user.json()["id"])
        yield client


async def post(api, draft, action, **body):
    response = await api.post(
        f"/process-drafts/{draft['id']}/{action}", json={"revision": draft["revision"], **body}
    )
    assert response.status_code == 200, response.text
    return response.json()


async def accept(api, draft):
    for key in proposals(DraftPlan.model_validate(draft["plan"])):
        draft = await post(api, draft, "reviews", proposal=key, disposition="accepted")
    return draft


async def prepare_new(api, monkeypatch, proposal=None):
    proposal = proposal or plan()
    monkeypatch.setattr(llm, "model_for", per_role(scripts(proposal)))
    response = await api.post("/process-drafts", json={"name": proposal["name"]})
    assert response.status_code == 201, response.text
    draft = await post(api, response.json(), "messages", message="Review amounts above 100.")
    draft = await accept(api, draft)
    return await post(api, draft, "prepare")


async def test_new_process_compiles_without_activation_and_publishes_atomically(api, monkeypatch):
    draft = await prepare_new(api, monkeypatch)
    assert draft["preview"]["valid"]
    assert all(e["passed"] for e in draft["preview"]["examples"])
    async with session_factory() as session:
        assert not await session.scalar(
            select(Process.id).where(Process.name == draft["plan"]["name"])
        )
    published = await post(api, draft, "publish")
    pid = published["published_process_id"]
    rules = (await api.get(f"/processes/{pid}/rules")).json()
    assert len(rules) == 1 and rules[0]["status"] == "active"
    assert rules[0]["report"]["discovery"]["revision"] == draft["revision"]
    again = await api.post(
        f"/process-drafts/{draft['id']}/publish", json={"revision": draft["revision"]}
    )
    assert again.status_code == 409
    history = (await api.get(f"/process-drafts/{draft['id']}/revisions")).json()
    assert history[0]["plan"]["rules"] == []
    assert len(history) == published["revision"]


async def add_decision(pid, author="engine"):
    async with session_factory() as session:
        digest = uuid.uuid4().hex
        session.add(File(hash=digest, name="invoice.pdf", content=b"invoice", text="invoice"))
        await session.flush()
        instance = Instance(
            process_id=pid,
            name="invoice.pdf",
            file_hash=digest,
            status="DECIDED",
            symbols={"amount": {"value": 50, "origin": "test"}},
        )
        session.add(instance)
        await session.flush()
        decision = Decision(
            instance_id=instance.id,
            decision="PAY",
            author=author,
            rules_hash="original",
            results=[],
            reason="original decision",
        )
        session.add(decision)
        await session.commit()
        return decision.id


@pytest.mark.parametrize("human", [False, True])
async def test_existing_process_backtest_keeps_identity_and_history(api, monkeypatch, human):
    initial = await post(api, await prepare_new(api, monkeypatch), "publish")
    pid = initial["published_process_id"]
    decision_id = await add_decision(pid, author="Manager" if human else "engine")
    start = (await api.post("/process-drafts", json={"process_id": pid})).json()
    proposal = plan(initial["plan"]["name"], threshold=40)
    monkeypatch.setattr(llm, "model_for", per_role(scripts(proposal, threshold=40)))
    draft = await post(api, start, "messages", message="Lower the threshold to 40.")
    draft = await post(api, await accept(api, draft), "prepare")
    impact = draft["preview"]["impact"]
    assert len(impact["conflicts" if human else "changes"]) == 1
    assert draft["preview"]["valid"] is not human
    result = await api.post(
        f"/process-drafts/{draft['id']}/publish", json={"revision": draft["revision"]}
    )
    assert result.status_code == (409 if human else 200), result.text
    if not human:
        assert result.json()["published_process_id"] == pid
        rules = (await api.get(f"/processes/{pid}/rules")).json()
        assert [r["status"] for r in rules] == ["retired", "active"]
    async with session_factory() as session:
        original = await session.get(Decision, decision_id)
        assert original.decision == "PAY" and original.rules_hash == "original"
        count = await session.scalar(
            select(func.count()).select_from(Finding).where(Finding.decision_id == decision_id)
        )
        assert count == (0 if human else 1)


async def test_stale_revision_rejection_and_chat_invalidate_preview(api, monkeypatch):
    draft = await prepare_new(api, monkeypatch)
    stale = copy.deepcopy(draft)
    draft = await post(
        api,
        draft,
        "reviews",
        proposal="rule:limit",
        disposition="rejected",
        explanation="Need to clarify the limit",
    )
    assert draft["preview"] is None
    r = await api.post(
        f"/process-drafts/{draft['id']}/publish", json={"revision": stale["revision"]}
    )
    assert r.status_code == 409
    r = await api.post(
        f"/process-drafts/{draft['id']}/prepare", json={"revision": draft["revision"]}
    )
    assert r.status_code == 409 and "accept" in r.text
    revised = plan(draft["plan"]["name"])
    monkeypatch.setattr(llm, "model_for", per_role({"discovery": [revised]}))
    draft = await post(api, draft, "messages", message="Keep 100 after all.")
    assert draft["reviews"] == {} and draft["preview"] is None


async def test_manager_answer_resolves_question_but_does_not_approve_draft(api, monkeypatch):
    proposed = plan()
    proposed["questions"] = ["Should amounts above 100 escalate?"]
    proposed["rules"] = []
    proposed["examples"] = []
    monkeypatch.setattr(llm, "model_for", per_role({"discovery": [proposed]}))
    draft = (await api.post("/process-drafts", json={"name": proposed["name"]})).json()
    draft = await post(api, draft, "messages", message="Discover the amount policy.")
    draft = await accept(api, draft)
    response = await api.post(
        f"/process-drafts/{draft['id']}/prepare", json={"revision": draft["revision"]}
    )
    assert response.status_code == 409 and "questions" in response.text

    revised = plan(proposed["name"])
    reference = f"chat:{len(draft['messages']) + 1}"
    revised["rules"][0]["evidence"] = [
        {"reference": reference, "explanation": "Manager confirmed escalation above 100"}
    ]
    seen = {}
    monkeypatch.setattr(llm, "model_for", per_role({"discovery": [revised]}, seen))
    draft = await post(api, draft, "messages", message="Yes, escalate amounts above 100.")
    context = user_json(seen["discovery"][0])
    assert context["current_plan"]["questions"] == proposed["questions"]
    assert context["messages"][-1]["text"] == "Yes, escalate amounts above 100."
    assert draft["plan"]["questions"] == []
    assert draft["plan"]["rules"][0]["evidence"][0]["reference"] == reference
    assert draft["reviews"] == {} and draft["preview"] is None
    assert draft["published_process_id"] is None
    response = await api.post(
        f"/process-drafts/{draft['id']}/prepare", json={"revision": draft["revision"]}
    )
    assert response.status_code == 409 and "accept" in response.text


async def test_fixed_examples_reject_wrong_interpretation(api, monkeypatch):
    proposal = plan()
    proposal["examples"][0]["decision"] = "REVIEW"  # differs from the generated tests
    draft = await prepare_new(api, monkeypatch, proposal)
    assert not draft["preview"]["valid"]
    assert draft["preview"]["compilations"][0]["report"]["valid"]
    assert not draft["preview"]["examples"][0]["passed"]
    response = await api.post(
        f"/process-drafts/{draft['id']}/publish", json={"revision": draft["revision"]}
    )
    assert response.status_code == 409


async def test_hiring_process_uses_same_workflow(api, monkeypatch):
    proposal = plan(field="assessment", default="HIRE", review="ESCALATE")
    monkeypatch.setattr(llm, "model_for", per_role(scripts(proposal, field="assessment")))
    draft = (await api.post("/process-drafts", json={})).json()
    draft = await post(api, draft, "messages", message="Set up our supplied hiring rubric.")
    draft = await post(api, await accept(api, draft), "prepare")
    assert draft["preview"]["valid"]
    published = await post(api, draft, "publish")
    process = (await api.get(f"/processes/{published['published_process_id']}")).json()
    assert process["symbols"][0]["name"] == "assessment"


def workbook_bytes(formula=False):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Reference"
    sheet.append(["Vendor", "Limit"])
    sheet.append(["001", "=1+2" if formula else 100.01])
    sheet.append(["002", 200])
    policy = workbook.create_sheet("Policy")
    policy.append(["Ask the manager before accepting exceptions."])
    stream = io.BytesIO()
    workbook.save(stream)
    return stream.getvalue()


async def test_workbook_mapping_preserves_cells_and_complete_rows(api, monkeypatch):
    draft = (await api.post("/process-drafts", json={})).json()
    r = await api.post(
        f"/process-drafts/{draft['id']}/workbooks",
        data={"revision": draft["revision"]},
        files={"file": ("reference.xlsx", workbook_bytes())},
    )
    assert r.status_code == 200, r.text
    draft = r.json()
    digest = draft["documents"][0]["document"]
    proposal = plan()
    proposal["sources"] = [
        {
            "name": "limits",
            "kind": "workbook",
            "document": digest,
            "sheet": "Reference",
            "first_row": 2,
            "last_row": 3,
            "columns": {"vendor": "A", "maximum": "B"},
            "explanation": "Limits",
            "evidence": [{"reference": f"{digest}:Reference!A1", "explanation": "Header"}],
        }
    ]
    seen = {}
    monkeypatch.setattr(llm, "model_for", per_role(scripts(proposal), seen))
    draft = await post(
        api, draft, "messages", message="Use the reference table; escalate amounts above 100."
    )
    assert user_json(seen["discovery"][0])["workbooks"][0]["sheets"][1]["name"] == "Policy"
    draft = await post(api, await accept(api, draft), "prepare")
    assert draft["preview"]["source_counts"] == {"limits": 2}
    draft = await post(api, draft, "publish")
    source = (await api.get(f"/processes/{draft['published_process_id']}/sources/limits")).json()
    assert source["data"] == [
        {"vendor": "001", "maximum": "100.01"},
        {"vendor": "002", "maximum": "200"},
    ]


async def test_operator_cannot_create_or_review_drafts(api):
    user = await api.post(
        "/users",
        json={"name": "Operator", "role": "operator", "email": f"{uuid.uuid4().hex}@test.com"},
    )
    api.headers["X-User-Id"] = str(user.json()["id"])
    assert (await api.post("/process-drafts", json={})).status_code == 403


async def test_publication_refuses_new_history_since_preview(api, monkeypatch):
    original = await post(api, await prepare_new(api, monkeypatch), "publish")
    pid = original["published_process_id"]
    draft = (await api.post("/process-drafts", json={"process_id": pid})).json()
    proposal = plan(original["plan"]["name"])
    monkeypatch.setattr(llm, "model_for", per_role(scripts(proposal)))
    draft = await post(api, draft, "messages", message="Keep the same policy.")
    draft = await post(api, await accept(api, draft), "prepare")
    await add_decision(pid)
    r = await api.post(
        f"/process-drafts/{draft['id']}/publish", json={"revision": draft["revision"]}
    )
    assert r.status_code == 409 and "changed" in r.text
    async with session_factory() as session:
        assert len(list(await session.scalars(select(Rule).where(Rule.process_id == pid)))) == 1


async def test_failed_compilation_stays_a_draft(api, monkeypatch):
    proposal = plan()
    monkeypatch.setattr(llm, "model_for", per_role(scripts(proposal, broken=True)))
    draft = (await api.post("/process-drafts", json={})).json()
    draft = await post(api, draft, "messages", message="Escalate amounts above 100.")
    draft = await post(api, await accept(api, draft), "prepare")
    assert not draft["preview"]["valid"]
    async with session_factory() as session:
        assert not await session.scalar(select(Process.id).where(Process.name == proposal["name"]))


async def test_erp_sync_is_complete_and_failed_sync_preserves_draft(api, monkeypatch):
    import httpx

    from app.features.processes import drafts
    from app.features.sources.http_connector import HttpConnector, SyncError
    from app.features.sources.tests.conftest import erp_config
    from app.features.sources.tests.test_http_connector import FAST, FakeERP

    config = erp_config("http://fake", **FAST)
    monkeypatch.setenv("TRACE_ERP_USER", "test")
    monkeypatch.setenv("TRACE_ERP_PASSWORD", "test")

    async def configured(*args):
        return {"erp": config}

    monkeypatch.setattr(drafts, "connectors", configured)
    connector = HttpConnector(config, httpx.MockTransport(FakeERP()))
    monkeypatch.setattr(drafts, "HttpConnector", lambda _: connector)
    draft = (await api.post("/process-drafts", json={})).json()
    draft = await post(api, draft, "sources/erp/sync")
    assert draft["snapshots"][0]["rows"] == 45

    async def broken():
        raise SyncError("page 2 unavailable")

    monkeypatch.setattr(connector, "download", broken)
    result = await api.post(
        f"/process-drafts/{draft['id']}/sources/erp/sync", json={"revision": draft["revision"]}
    )
    assert result.status_code == 502
    after = (await api.get(f"/process-drafts/{draft['id']}")).json()
    assert after["revision"] == draft["revision"]
    assert after["snapshots"] == draft["snapshots"]


async def test_existing_setup_cannot_be_changed_by_an_import(api, monkeypatch):
    original = await post(api, await prepare_new(api, monkeypatch), "publish")
    draft = (
        await api.post("/process-drafts", json={"process_id": original["published_process_id"]})
    ).json()
    changed = plan(original["plan"]["name"])
    changed["symbols"].append({"name": "new_field", "type": "text"})
    monkeypatch.setattr(llm, "model_for", per_role({"discovery": [changed]}))
    draft = await post(api, draft, "messages", message="Add a field.")
    draft = await accept(api, draft)
    r = await api.post(
        f"/process-drafts/{draft['id']}/prepare", json={"revision": draft["revision"]}
    )
    assert r.status_code == 409 and "keep existing symbols" in r.text


async def test_runtime_error_cannot_satisfy_an_escalation_example():
    from app.features.processes import draft_compilation

    proposed = DraftPlan.model_validate(plan())
    code = "def evaluate(instance, sources, others):\n    raise ValueError('broken rule')"
    compiled = [
        {
            "text": "test",
            "type": "prohibition",
            "decision": "REVIEW",
            "code": code,
            "hash": "test",
            "report": {"valid": True},
        }
    ]
    result = await draft_compilation.preview(None, None, proposed, {}, compiled)
    large = next(e for e in result["examples"] if e["name"] == "large")
    assert large["actual"] == "REVIEW"
    assert not large["passed"] and not result["valid"]
