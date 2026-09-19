"""Who changed what is in the audit: agent configuration and rule status changes carry their
author and the version before and after; failures inside a step leave `error` spans."""

import pytest

from app.core.database import session_factory
from app.features.agents import llm, sandbox
from app.features.agents.sandbox import SandboxError
from app.features.decisions.tests.test_api import FAKE_SANDBOX, client, create_process
from app.features.rules.model import Rule
from tests.support.models import down


async def feed(api, process_id: int, step: str) -> list[dict]:
    r = await api.get(f"/processes/{process_id}/events", params={"step": step})
    assert r.status_code == 200, r.text
    return r.json()


async def test_agent_config_changes_are_in_the_process_feed_with_their_author() -> None:
    async with client() as api:
        process_id, headers = await create_process(api, "manager")
        use_case_id = (await api.get(f"/processes/{process_id}")).json()["use_case_id"]
        url = f"/use-cases/{use_case_id}/agents/compiler"
        first = (await api.put(url, json={"config": {}, "note": "v1"}, headers=headers)).json()
        body = {"config": {"instructions": "Amounts in cents."}, "note": "cents"}
        assert (await api.put(url, json=body, headers=headers)).status_code == 200
        r = await api.post(f"/agent-configs/{first['id']}/activate", headers=headers)
        assert r.status_code == 200, r.text
        r = await api.post(f"/agent-configs/{first['id']}/activate", headers=headers)
        assert r.status_code == 409  # refused, and still audited

        configured = [e["data"] for e in await feed(api, process_id, "configure_agent")]
        assert [(d["author"], d["before_version"], d["after_version"]) for d in configured] == [
            ("Ana", 1, 2),
            ("Ana", None, 1),
        ]
        assert configured[0]["note"] == "cents"
        assert configured[0]["config"]["instructions"] == "Amounts in cents."
        refused, rollback = await feed(api, process_id, "activate_agent_config")
        assert refused["status"] == "error" and "already active" in refused["data"]["error"]
        assert rollback["status"] == "ok"
        assert rollback["data"]["author"] == "Ana" and rollback["data"]["role"] == "compiler"
        assert (rollback["data"]["before_version"], rollback["data"]["after_version"]) == (2, 1)


async def test_rule_status_changes_carry_author_and_show_in_the_rule_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sandbox, "run_dataset", FAKE_SANDBOX)
    async with client() as api:
        process_id, headers = await create_process(api, "manager")
        await api.post(f"/processes/{process_id}/run")
        rules = (await api.get(f"/processes/{process_id}/rules")).json()
        retired = rules[0]["id"]
        async with session_factory() as session:
            draft = Rule(
                process_id=process_id,
                text="order_already_paid",
                type="prohibition",
                decision="NO_PAGAR",
                code="order_already_paid",
                hash="hash-draft",
                status="draft",
                report={"valid": True},
            )
            session.add(draft)
            await session.commit()

        assert (await api.get(f"/rules/{retired}/impact")).status_code == 200
        assert (await api.post(f"/rules/{retired}/retire", headers=headers)).status_code == 200
        assert (await api.post(f"/rules/{draft.id}/activate", headers=headers)).status_code == 200
        r = await api.post(f"/rules/{draft.id}/activate", headers=headers)
        assert r.status_code == 409

        [retire] = await feed(api, process_id, "retire_rule")
        assert retire["rule_id"] == retired and retire["status"] == "ok"
        assert {k: retire["data"][k] for k in ("author", "before", "after")} == {
            "author": "Ana",
            "before": "active",
            "after": "retired",
        }
        assert (
            retire["data"]["findings"] == 0 and retire["data"]["rule_hash"] == "hash-iban_mismatch"
        )
        refused, activated = await feed(api, process_id, "activate_rule")
        assert activated["data"]["after"] == "active" and activated["data"]["author"] == "Ana"
        assert refused["status"] == "error" and refused["data"]["before"] == "active"

        trace = (await api.get(f"/rules/{retired}/trace")).json()
        steps = [(s["step"], s["data"].get("author")) for s in trace["lifecycle"]]
        assert steps == [("impact_check", None), ("retire_rule", "Ana")]
        assert trace["lifecycle"][0]["data"]["preview"] is True


async def test_a_rule_saved_by_a_person_names_them_and_a_failed_compile_is_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every model down: the compilation and its model call are `error` spans."""
    monkeypatch.setattr(llm, "resolve", lambda name: down(name))
    async with client() as api:
        process_id, headers = await create_process(api, "manager")
        body = {"text": "amount > 1000", "type": "prohibition", "decision": "ESCALAR"}
        r = await api.post(f"/processes/{process_id}/rules", json=body, headers=headers)
        assert r.status_code == 201, r.text
        trace = (await api.get(f"/rules/{r.json()['id']}/trace")).json()

    save, compile_ = trace["lifecycle"]
    assert (save["step"], save["data"]["author"]) == ("save_rule", "Ana")
    assert compile_["step"] == "compile_rule" and compile_["status"] == "error"
    [compilation] = trace["compilations"]
    [tester] = compilation["children"]
    assert tester["step"] == "llm_run" and tester["status"] == "error"
    assert "every model failed" in tester["data"]["error"]


async def test_a_sandbox_crash_is_an_error_span_and_the_run_goes_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def crash(code, instances, sources, population):
        if code == "iban_mismatch":
            raise SandboxError("The process failed (-9): killed")
        return FAKE_SANDBOX(code, instances, sources, population)

    monkeypatch.setattr(sandbox, "run_dataset", crash)
    async with client() as api:
        process_id, _ = await create_process(api, "manager")
        assert (await api.post(f"/processes/{process_id}/run")).status_code == 200
        spans = await feed(api, process_id, "evaluate_rule")
        [run] = await feed(api, process_id, "run_process")

    assert sorted(s["status"] for s in spans) == ["error", "ok"]
    [failed] = [s for s in spans if s["status"] == "error"]
    assert "killed" in failed["data"]["error"]
    assert run["status"] == "ok" and run["data"]["failures"]["RULE_ERROR"] == 3
