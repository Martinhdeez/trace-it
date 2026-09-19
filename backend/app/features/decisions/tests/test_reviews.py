"""Optional review through the API, with real persistence and scripted model responses."""

import asyncio
import json

import pytest

from app.core.database import session_factory
from app.features.agents import llm, sandbox
from app.features.decisions import service
from app.features.decisions.tests.test_api import (
    FAKE_SANDBOX,
    INVOICE_PROCESS,
    NAMES,
    client,
    create_process,
)
from app.features.decisions.tests.test_reprocess import resync_erp
from tests.support.models import down, per_role, user_json

GUIDANCE = "Prefer escalation when refusing could cause disproportionate harm."


def answer(decision):
    return {
        "decision": decision,
        "reasoning": "The supplied guidance warrants checking the consequences with a manager.",
        "evidence": ["guidance"],
    }


@pytest.fixture(autouse=True)
def fake_sandbox(monkeypatch):
    monkeypatch.setattr(sandbox, "run_dataset", FAKE_SANDBOX)


async def configure(api, process_id, config):
    process = (await api.get(f"/processes/{process_id}")).json()
    response = await api.post(
        "/processes/definition",
        json={"name": process["name"], **INVOICE_PROCESS, "decision_review": config},
    )
    assert response.status_code == 200, response.text
    assert response.json()["process"]["decision_review"] == config


async def details(api, process_id):
    instances = (await api.get(f"/processes/{process_id}/instances")).json()
    return {
        i["name"]: (await api.get(f"/instances/{i['id']}")).json()
        for i in instances
        if i["name"] in NAMES
    }


async def export(process_id, names=None):
    async with session_factory() as session:
        body, _ = await service.export(session, process_id, set(names or NAMES))
    return [json.loads(line) for line in body.splitlines()]


async def test_disagreement_waits_for_human_and_exports_resolution(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        llm,
        "model_for",
        per_role(
            {"decision_reviewer": [answer("PAGAR"), answer("PAGAR"), answer("ESCALAR")]}, seen
        ),
    )
    async with client() as api:
        pid, headers = await create_process(api, "manager")
        await configure(api, pid, {"guidance": GUIDANCE, "timeout_seconds": 30})
        response = await api.post(f"/processes/{pid}/run")
        assert response.status_code == 200, response.text
        assert response.json()["by_decision"] == {"PAGAR": 1, "NO_PAGAR": 1, "ESCALAR": 1}
        cases = await details(api, pid)
        case = cases[NAMES[1]]
        [original] = case["decisions"]
        [review] = case["reviews"]
        assert case["decision"] == "NO_PAGAR" and case["review_pending"]
        assert review["recommendation"] == "PAGAR" and review["requires_human"]
        assert review["reasoning"] and review["model"] == "fake/model"
        assert review["decision_id"] == original["id"]
        assert review["snapshot"]["context"] == user_json(seen["decision_reviewer"][1])
        assert len(review["snapshot"]["context"]["engine"]["results"]) == 2
        assert any(k.startswith("source:") for k in review["snapshot"]["context"]["evidence"])
        assert not cases[NAMES[0]]["review_pending"]
        assert not cases[NAMES[2]]["review_pending"]  # engine escalation still queues normally
        queue = (await api.get(f"/processes/{pid}/queue")).json()
        assert {i["name"] for i in queue} == set(NAMES[1:])
        assert (await api.get(f"/processes/{pid}/summary")).json()["queue"] == 2
        assert len((await api.get(f"/processes/{pid}/queue?type=NO_PAGAR")).json()) == 1

        from app.common.exceptions import ConflictError

        with pytest.raises(ConflictError, match="awaiting human review"):
            await export(pid)
        assert (await export(pid, [NAMES[0]]))[0]["result"] == "PAGAR"
        trace = (await api.get(f"/instances/{case['id']}/trace")).json()
        assert trace["exported_decision"] is None

        # Disabling review cannot remove an already-pending approval or change its snapshot.
        await configure(api, pid, None)
        assert (await api.get(f"/instances/{case['id']}")).json()["review_pending"]
        with pytest.raises(ConflictError, match="awaiting human review"):
            await export(pid)
        response = await api.post(
            f"/instances/{case['id']}/resolve",
            headers=headers,
            json={"decision": "PAGAR", "reason": "Checked the exception with the supplier."},
        )
        resolved = response.json()
        assert response.status_code == 200, response.text
        assert not resolved["review_pending"]
        assert resolved["decisions"][0] == original
        assert resolved["reviews"] == [review]
        assert resolved["decisions"][-1]["author"] == "Ana"
        assert (await export(pid))[1]["result"] == "PAGAR"
        trace = (await api.get(f"/instances/{case['id']}/trace")).json()
        assert trace["exported_decision"] == "PAGAR"
        assert (await api.get(f"/processes/{pid}/summary")).json()["queue"] == 1
        # Running again never calls the reviewer for an already-decided instance.
        assert (await api.post(f"/processes/{pid}/run")).json()["decided"] == 0
        assert len(seen["decision_reviewer"]) == 3


@pytest.mark.parametrize("failure", ["provider", "missing", "invalid", "timeout"])
async def test_optional_agent_failure_keeps_deterministic_outcomes(monkeypatch, failure):
    if failure == "provider":
        monkeypatch.setattr(llm, "model_for", lambda role: down("unavailable"))
    elif failure == "missing":

        def missing(role):
            raise ValueError("No model configured")

        monkeypatch.setattr(llm, "model_for", missing)
    elif failure == "invalid":
        monkeypatch.setattr(
            llm, "model_for", per_role({"decision_reviewer": [answer("UNKNOWN")] * 6})
        )
    else:

        async def slow(*args, **kwargs):
            await asyncio.sleep(1)

        monkeypatch.setattr(llm, "run", slow)
    async with client() as api:
        pid, _ = await create_process(api, "manager")
        await configure(
            api,
            pid,
            {"guidance": GUIDANCE, "timeout_seconds": 0.01 if failure == "timeout" else 30},
        )
        response = await api.post(f"/processes/{pid}/run")
        assert response.status_code == 200, response.text
        assert response.json()["by_decision"] == {"PAGAR": 1, "NO_PAGAR": 1, "ESCALAR": 1}
        for case in (await details(api, pid)).values():
            [review] = case["reviews"]
            assert review["status"] == "failed" and review["error"]
            assert review["recommendation"] is None and not case["review_pending"]
        assert [r["result"] for r in await export(pid)] == ["PAGAR", "NO_PAGAR", "ESCALAR"]
        assert len((await api.get(f"/processes/{pid}/queue")).json()) == 1


async def test_disabled_agent_never_runs(monkeypatch):
    def unexpected(role):
        pytest.fail("Disabled review called a model")

    monkeypatch.setattr(llm, "model_for", unexpected)
    async with client() as api:
        pid, _ = await create_process(api, "manager")
        assert (await api.post(f"/processes/{pid}/run")).status_code == 200
        assert all(not c["reviews"] for c in (await details(api, pid)).values())


async def test_bad_evidence_retries_and_human_can_reject_advice(monkeypatch):
    invalid = {**answer("PAGAR"), "evidence": ["source:invented"]}
    monkeypatch.setattr(
        llm,
        "model_for",
        per_role(
            {
                "decision_reviewer": [
                    invalid,
                    answer("NO_PAGAR"),
                    answer("NO_PAGAR"),
                    answer("ESCALAR"),
                ],
            }
        ),
    )
    async with client() as api:
        pid, headers = await create_process(api, "manager")
        await configure(api, pid, {"guidance": GUIDANCE, "timeout_seconds": 30})
        assert (await api.post(f"/processes/{pid}/run")).status_code == 200
        case = (await details(api, pid))[NAMES[0]]
        assert case["review_pending"]
        response = await api.post(
            f"/instances/{case['id']}/resolve",
            headers=headers,
            json={"decision": "PAGAR", "reason": "The engine outcome is correct."},
        )
        assert response.status_code == 200 and not response.json()["review_pending"]
        assert (await export(pid))[0]["result"] == "PAGAR"


async def test_reprocess_protects_pending_review_and_dry_run_does_not_call_agent(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        llm,
        "model_for",
        per_role(
            {
                "decision_reviewer": [answer("ESCALAR"), answer("NO_PAGAR"), answer("ESCALAR")],
            },
            seen,
        ),
    )
    async with client() as api:
        pid, _ = await create_process(api, "manager")
        await configure(api, pid, {"guidance": GUIDANCE, "timeout_seconds": 30})
        assert (await api.post(f"/processes/{pid}/run")).status_code == 200
        before = (await details(api, pid))[NAMES[0]]
        await resync_erp(pid)
        preview = await api.post(f"/processes/{pid}/reprocess?dry_run=true")
        applied = await api.post(f"/processes/{pid}/reprocess")
        assert preview.json() == applied.json()
        assert applied.json()["changes"] == []
        assert applied.json()["conflicts"][0]["name"] == NAMES[0]
        after = (await details(api, pid))[NAMES[0]]
        assert before["reviews"] == after["reviews"] and after["review_pending"]
        assert before["decisions"] == after["decisions"]
        assert len(seen["decision_reviewer"]) == 3


async def test_reprocessed_engine_decision_gets_its_own_review(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        llm,
        "model_for",
        per_role(
            {
                "decision_reviewer": [
                    answer("PAGAR"),
                    answer("NO_PAGAR"),
                    answer("ESCALAR"),
                    answer("ESCALAR"),
                ],
            },
            seen,
        ),
    )
    async with client() as api:
        pid, _ = await create_process(api, "manager")
        await configure(api, pid, {"guidance": GUIDANCE, "timeout_seconds": 30})
        assert (await api.post(f"/processes/{pid}/run")).status_code == 200
        await resync_erp(pid)
        preview = (await api.post(f"/processes/{pid}/reprocess?dry_run=true")).json()
        assert len(seen["decision_reviewer"]) == 3
        response = await api.post(f"/processes/{pid}/reprocess")
        assert response.json() == preview
        case = (await details(api, pid))[NAMES[0]]
        assert [d["decision"] for d in case["decisions"]] == ["PAGAR", "NO_PAGAR"]
        assert len(case["reviews"]) == 2 and case["review_pending"]
        assert case["reviews"][-1]["snapshot"]["context"]["engine"]["decision"] == "NO_PAGAR"
