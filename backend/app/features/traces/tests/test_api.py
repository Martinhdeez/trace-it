"""The trace endpoints over a real run, against the local database (`make test-db`). Same
setup as `decisions/tests/test_api.py`: seeded instances and rules, the sandbox faked."""

import pytest

from app.core import events
from app.core.database import session_factory
from app.features.agents import sandbox
from app.features.decisions.tests.test_api import FAKE_SANDBOX, client, create_process
from app.features.rules.model import Rule


@pytest.fixture
def fake_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "run_dataset", FAKE_SANDBOX)


def steps(nodes: list[dict]) -> list:
    """A tree as nested (step, children)."""
    return [(n["step"], steps(n["children"])) for n in nodes]


async def test_run_journey_and_metrics(fake_sandbox: None) -> None:
    async with client() as api:
        process_id, headers = await create_process(api, "manager")
        # Two syncs of the ERP before the decisions: the latest one is what they read.
        for retries in (0, 2):
            with events.span("sync_source", process_id=process_id, source="erp") as sync:
                sync.set(requests=5, retries=retries, rate_limited=1, timeouts=0)
        assert (await api.post(f"/processes/{process_id}/run")).status_code == 200
        [escalated] = (await api.get(f"/processes/{process_id}/queue")).json()
        metrics = (await api.get(f"/processes/{process_id}/metrics/execution")).json()
        assert metrics["escalated"] == 1
        assert sum(metrics["escalation_reasons"].values()) == 1
        r = await api.post(
            f"/instances/{escalated['id']}/resolve",
            json={"decision": "NO_PAGAR", "reason": "checked by phone"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        with events.span("sync_source", process_id=process_id, source="erp"):
            pass  # after every decision: not read by any

        # The run: one span, one span per rule with its counts, one point per decision.
        [run] = (
            await api.get("/traces", params={"process_id": process_id, "name": "run_process"})
        ).json()
        assert run["data"]["instances"] == 3 and run["data"]["by_decision"]["ESCALAR"] == 1
        tree = (await api.get(f"/traces/{run['trace_id']}")).json()
        [(root, children)] = [t for t in steps(tree) if t[0] == "run_process"]
        assert sorted(s for s, _ in children) == ["decision"] * 3 + ["evaluate_rule"] * 2
        rules = [c for c in tree[0]["children"] if c["step"] == "evaluate_rule"]
        assert sum(c["data"]["fired"] for c in rules) == 2
        assert all(c["data"]["instances"] == 3 and c["data"]["errors"] == 0 for c in rules)

        # The journey of the escalated invoice.
        journey = (await api.get(f"/instances/{escalated['id']}/trace")).json()
        assert journey["file"]["size_bytes"] == 4
        assert journey["symbols"]["nif"]["origin"] == "text"
        engine, person = journey["decisions"]
        fired = [r for r in engine["rule_results"] if r["fires"]]
        assert [r["rule_text"] for r in fired] == ["iban_mismatch"]
        assert person["author"] == "Ana" and journey["exported_decision"] == "ESCALAR"
        [erp] = journey["sources_read"]
        assert (erp["source"], erp["status"], erp["trace_id"]) == ("erp", "ok", sync.trace_id)
        assert (erp["requests"], erp["retries"], erp["rate_limited"]) == (5, 2, 1)
        roots = steps(journey["spans"])
        assert ("resolution", []) in roots
        [run_tree] = [c for s, c in roots if s == "run_process"]
        assert sorted(s for s, _ in run_tree) == ["decision", "evaluate_rule", "evaluate_rule"]

        # How often each rule fired in runs, and the process's aggregates.
        rule = (await api.get(f"/rules/{fired[0]['rule_id']}/trace")).json()
        assert rule["runtime"]["runs"] == 1 and rule["runtime"]["fired"] == 1
        assert rule["compilations"] == []  # seeded with its code, never compiled
        metrics = (await api.get(f"/processes/{process_id}/metrics")).json()
        assert metrics["runs"] == 1 and metrics["instances_decided"] == 3
        by_step = {s["step"]: s for s in metrics["steps"]}
        assert by_step["evaluate_rule"]["count"] == 2 and by_step["run_process"]["errors"] == 0
        # Each instance counts once, by its latest decision: the person's NO_PAGAR.
        assert metrics["decisions_by_outcome"] == {"PAGAR": 1, "NO_PAGAR": 2}
        assert metrics["escalated"] == 0 and metrics["escalation_reasons"] == {}
        assert metrics["pending"] == 1
        assert metrics["providers"] == []
        assert set(metrics["failures"].values()) == {0}


async def test_reprocess_and_runs_during_draft_compilation_are_spans(fake_sandbox: None) -> None:
    async with client() as api:
        process_id, _ = await create_process(api, "manager")
        await api.post(f"/processes/{process_id}/run")
        r = await api.post(f"/processes/{process_id}/reprocess", params={"dry_run": True})
        assert r.status_code == 200, r.text
        [span] = (
            await api.get("/traces", params={"process_id": process_id, "name": "reprocess"})
        ).json()
        assert span["data"]["dry_run"] is True and span["data"]["unchanged"] == 3
        assert span["data"]["changed"] == 0 and span["data"]["conflicts"] == 0

        # Draft compilation does not interrupt the published version.
        async with session_factory() as session:
            session.add(
                Rule(
                    process_id=process_id,
                    text="t",
                    type="prohibition",
                    decision="ESCALAR",
                    status="compiling",
                )
            )
            await session.commit()
        assert (await api.post(f"/processes/{process_id}/run")).status_code == 200
        runs = (
            await api.get("/traces", params={"process_id": process_id, "name": "run_process"})
        ).json()
        assert runs[0]["status"] == "ok"
        metrics = (await api.get(f"/processes/{process_id}/metrics")).json()
        [run] = [s for s in metrics["steps"] if s["step"] == "run_process"]
        assert run["count"] == 2 and run["errors"] == 0 and metrics["runs"] == 2


async def test_provider_metrics_separate_network_usage_from_journal_replay() -> None:
    async with client() as api:
        process_id, _ = await create_process(api, "manager")
        common = {
            "process_id": process_id,
            "provider": "gemini",
            "model": "gemini-test",
            "operation": "image_transcription",
        }
        with events.span("provider_call", **common) as span:
            span.set(network_attempted=True, outcome="success", input_tokens=12, output_tokens=4)
        with events.span("provider_call", **common) as span:
            span.set(
                network_attempted=False,
                journal_hit=True,
                outcome="replay",
                input_tokens=12,
                output_tokens=4,
            )
        with events.span("provider_call", **common) as span:
            span.status = "error"
            span.set(network_attempted=False, journal_hit=True, outcome="blocked_uncertain")
        with events.span("provider_call", **{**common, "provider": "vision"}) as span:
            span.set(network_attempted=True, outcome="success", input_tokens=3, output_tokens=1)

        response = await api.get(f"/processes/{process_id}/metrics")
        assert response.status_code == 200, response.text
        metrics = response.json()
        assert metrics["llm"] == []
        expected = [
            {
                "provider": "gemini",
                "model": "gemini-test",
                "operation": "image_transcription",
                "attempts": 3,
                "network_requests": 1,
                "replays": 1,
                "errors": 1,
                "input_tokens": 12,
                "output_tokens": 4,
            },
            {
                "provider": "vision",
                "model": "gemini-test",
                "operation": "image_transcription",
                "attempts": 1,
                "network_requests": 1,
                "replays": 0,
                "errors": 0,
                "input_tokens": 3,
                "output_tokens": 1,
            },
        ]
        assert [{key: row[key] for key in expected[0]} for row in metrics["providers"]] == expected
        assert metrics["providers"][0]["blocked"] == 1
        assert metrics["providers"][0]["unpriced_requests"] == 1


async def test_the_journey_says_what_is_pending_and_which_version_decided(
    fake_sandbox: None,
) -> None:
    from app.features.alerts.model import Alert
    from app.features.proposals.model import ManagerProposal

    async with client() as api:
        process_id, headers = await create_process(api, "manager")
        assert (await api.post(f"/processes/{process_id}/run")).status_code == 200
        [escalated] = (await api.get(f"/processes/{process_id}/queue")).json()
        [decision] = (await api.get(f"/instances/{escalated['id']}/trace")).json()["decisions"]
        async with session_factory() as session:
            proposal = ManagerProposal(
                process_id=process_id,
                instance_id=escalated["id"],
                channel="escalation",
                kind="decision",
                summary="Pay it",
                rationale="r",
                evidence=[],
                payload={},
                author="assistant",
            )
            alert = Alert(
                process_id=process_id,
                instance_id=escalated["id"],
                decision_id=decision["id"],
                before="ESCALAR",
                after="PAGAR",
                trigger={"kind": "source_sync"},
                evidence={},
                status="open",
            )
            session.add_all([proposal, alert])
            await session.commit()
        journey = (await api.get(f"/instances/{escalated['id']}/trace")).json()
        proposals = await api.get(
            f"/processes/{process_id}/proposals",
            params={"instance_id": escalated["id"]},
            headers=headers,
        )
        alerts = await api.get(
            f"/processes/{process_id}/alerts", params={"instance_id": escalated["id"] + 10**6}
        )
        versions = (await api.get(f"/processes/{process_id}/versions")).json()

    pending = journey["pending"]
    assert pending["waiting_for_person"] is True and pending["review_pending"] is False
    assert [(p["id"], p["kind"]) for p in pending["proposals"]] == [(proposal.id, "decision")]
    assert [(a["id"], a["kind"]) for a in pending["alerts"]] == [(alert.id, "source_sync")]
    assert [p["id"] for p in proposals.json()] == [proposal.id]
    assert alerts.json() == []  # another instance's: none
    version = next(v for v in versions if v["id"] == decision["version_id"])
    assert journey["version"] == {
        "id": version["id"],
        "number": version["number"],
        "author": version["author"],
        "created_at": version["created_at"],
    }
