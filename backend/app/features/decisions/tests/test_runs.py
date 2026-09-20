"""Run history (Q1) and the manager gate (Q5), through the API.

Same setup as `test_api.py`: instances, sources and rules inserted directly, sandbox faked.
"""

import pytest

from app.core.database import session_factory
from app.features.agents import sandbox
from app.features.decisions import runs
from app.features.decisions.tests.test_api import (
    FAKE_SANDBOX,
    SUPPLIERS,
    client,
    create_process,
)
from app.features.sources.model import Source
from tests.support.users import anonymous


@pytest.fixture(autouse=True)
def fake_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "run_dataset", FAKE_SANDBOX)


def test_reason_codes_drop_the_details() -> None:
    reason = "IMPOSSIBLE_DATE 2026-02-31 | SOURCE_UNAVAILABLE: erp | RULE_ERROR 7: boom"
    assert runs.reason_codes(reason) == ["IMPOSSIBLE_DATE", "SOURCE_UNAVAILABLE", "RULE_ERROR"]
    assert runs.reason_codes(None) == []


async def test_a_rerun_with_better_data_shows_fewer_escalations() -> None:
    async with client() as api:
        process_id, _ = await create_process(api, "manager")
        assert (await api.post(f"/processes/{process_id}/run")).status_code == 200

        # The supplier master now has the IBAN FA-5044 carries: the escalation goes away.
        fixed = [
            {**s, "iban": "ES3900815290070012345678"} if s["nif"] == "B78451236" else s
            for s in SUPPLIERS
        ]
        async with session_factory() as session:
            session.add(Source(process_id=process_id, name="suppliers", origin="z", rows=fixed))
            await session.commit()
        assert (await api.post(f"/processes/{process_id}/reprocess")).status_code == 200

        r = await api.get(f"/processes/{process_id}/runs")
        assert r.status_code == 200, r.text
        rerun, first = r.json()  # newest first
        assert (first["kind"], rerun["kind"]) == ("run", "reprocess")
        assert first["author"] == rerun["author"] == "Manager"
        assert first["by_decision"] == {"PAGAR": 1, "NO_PAGAR": 1, "ESCALAR": 1}
        assert (first["escalated"], first["escalation_reasons"]) == (1, {"iban_mismatch": 1})
        # Every instance counts, not only the one the reprocess rewrote: runs compare.
        assert rerun["by_decision"] == {"PAGAR": 2, "NO_PAGAR": 1}
        assert (rerun["escalated"], rerun["escalation_reasons"]) == (0, {})
        assert (first["instances"], first["decided"]) == (3, 3)
        assert (rerun["instances"], rerun["decided"]) == (3, 1)
        assert first["version_id"] == rerun["version_id"] and first["version_number"] == 1
        assert first["rules_hash"] and first["trace_id"] and first["finished_at"]
        assert first["started_at"] <= first["finished_at"] <= rerun["started_at"]

        # Going back: the first run opens read-only with what it decided then.
        r = await api.get(f"/runs/{first['id']}")
        assert r.status_code == 200, r.text
        detail = r.json()
        assert {d["name"]: d["decision"] for d in detail["decisions"]} == {
            "factura_1217.pdf": "PAGAR",
            "FA-1016_papelería.pdf": "NO_PAGAR",
            "FA-5044_mensajería2.pdf": "ESCALAR",
        }
        assert detail["escalated"] == 1
        rewritten = (await api.get(f"/runs/{rerun['id']}")).json()["decisions"]
        assert [(d["name"], d["decision"]) for d in rewritten] == [
            ("FA-5044_mensajería2.pdf", "PAGAR")
        ]

        # The trace of the run is the one the history names.
        trace = await api.get(f"/traces/{first['trace_id']}")
        assert trace.status_code == 200, trace.text

    assert (await anonymous("GET", "/runs/999999999")).status_code == 404
    assert (await anonymous("GET", "/processes/999999999/runs")).status_code == 404


async def test_a_resolution_is_not_a_run_decision() -> None:
    """A resolve reuses the run's execution_id; the run still shows only the engine's cases."""
    async with client() as api:
        process_id, headers = await create_process(api, "manager")
        assert (await api.post(f"/processes/{process_id}/run")).status_code == 200
        instances = (await api.get(f"/processes/{process_id}/instances")).json()
        escalated = next(i["id"] for i in instances if i["name"] == "FA-5044_mensajería2.pdf")
        r = await api.post(
            f"/instances/{escalated}/resolve",
            json={"decision": "PAGAR", "reason": "IBAN confirmed by phone"},
            headers=headers,
        )
        assert r.status_code == 200, r.text

        [run] = (await api.get(f"/processes/{process_id}/runs")).json()
        assert (run["decided"], run["by_decision"]) == (
            3,
            {"PAGAR": 1, "NO_PAGAR": 1, "ESCALAR": 1},
        )
        detail = (await api.get(f"/runs/{run['id']}")).json()
        assert sorted(d["name"] for d in detail["decisions"]) == sorted(
            ["factura_1217.pdf", "FA-1016_papelería.pdf", "FA-5044_mensajería2.pdf"]
        )
        assert detail["decided"] == 3


PUBLISH = {"revision": 1, "validation_hash": "x", "reason": "x"}
MUTATIONS = [
    ("POST", "/processes/{pid}/run", None),
    ("POST", "/processes/{pid}/reprocess", None),
    ("POST", "/processes/{pid}/sources/erp/sync", None),
    ("POST", "/processes/definition", {"name": "x", "decision_types": [], "symbols": []}),
    ("POST", "/processes/{pid}/draft/publish", PUBLISH),
    ("POST", "/instances/{iid}/resolve", {"decision": "PAGAR", "reason": "x"}),
    ("POST", "/alerts/999999999/ack", None),
    ("POST", "/users", {"name": "x", "email": "x@x.x", "role": "operator"}),
    ("POST", "/processes/{pid}/rules", {"text": "x", "type": "prohibition", "decision": "x"}),
    ("POST", "/processes/{pid}/norm", {"text": "x"}),
    ("POST", "/rules/999999999/compile", None),
    ("POST", "/rules/999999999/activate", None),
    ("POST", "/rules/999999999/retire", None),
    ("PUT", "/processes/{pid}/draft", {"description": "x"}),
    ("POST", "/processes/{pid}/draft/validate", None),
    ("DELETE", "/processes/{pid}/draft?revision=1", None),
]


async def test_mutations_need_a_manager() -> None:
    async with client() as api:
        pid, operator = await create_process(api, "operator")
        iid = (await api.get(f"/processes/{pid}/instances")).json()[0]["id"]
        for method, path, body in MUTATIONS:
            url = path.format(pid=pid, iid=iid)
            r = await anonymous(method, url, json=body)
            assert (r.status_code, r.json()["code"]) == (401, "unauthenticated"), url
            r = await anonymous(method, url, json=body, headers={"X-User-Id": "999999999"})
            assert r.status_code == 401, url  # nobody by that id
            r = await api.request(method, url, json=body, headers=operator)
            assert (r.status_code, r.json()["code"]) == (403, "permission_denied"), url

        # Reads stay open.
        for url in (f"/processes/{pid}/runs", f"/processes/{pid}/summary", "/processes"):
            assert (await anonymous("GET", url)).status_code == 200, url


async def test_run_cost_counts_only_its_descendants_and_excludes_replays() -> None:
    import uuid

    from sqlalchemy import delete, select

    from app.core.events import Event

    async with client() as api:
        process_id, _ = await create_process(api, "manager")
        await api.post(f"/processes/{process_id}/run")
        [run] = (await api.get(f"/processes/{process_id}/runs")).json()
        assert run["cost"] == {
            "known_cost_usd": 0,
            "requests": 0,
            "unpriced_requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }
        async with session_factory() as session:
            root = await session.scalar(
                select(Event).where(
                    Event.trace_id == run["trace_id"],
                    Event.step == "run_process",
                )
            )
            parent = uuid.uuid4().hex[:16]
            priced = {
                "requests": 2,
                "cost_status": "known",
                "cost_usd": 0.25,
                "input_tokens": 100,
                "output_tokens": 20,
            }
            for step, parent_id, span_id, data in [
                ("review_decision", root.span_id, parent, priced),
                ("llm_run", parent, uuid.uuid4().hex[:16], priced),
                (
                    "provider_call",
                    parent,
                    uuid.uuid4().hex[:16],
                    {"network_attempted": True, "cost_status": "unknown"},
                ),
                (
                    "provider_call",
                    parent,
                    uuid.uuid4().hex[:16],
                    {**priced, "outcome": "replay", "network_attempted": False},
                ),
                # A sibling in the same trace is earlier work, not part of this run.
                ("llm_run", None, uuid.uuid4().hex[:16], priced),
            ]:
                session.add(
                    Event(
                        trace_id=root.trace_id,
                        span_id=span_id,
                        parent_id=parent_id,
                        step=step,
                        status="ok",
                        started_at=root.started_at,
                        process_id=process_id,
                        duration_ms=1,
                        data=data,
                    )
                )
            root_id = root.id
            await session.commit()
        expected = {
            "known_cost_usd": 0.25,
            "requests": 3,
            "unpriced_requests": 1,
            "input_tokens": 100,
            "output_tokens": 20,
        }
        detail = (await api.get(f"/runs/{run['id']}")).json()
        assert detail["cost"] == expected
        [listed] = (await api.get(f"/processes/{process_id}/runs")).json()
        assert listed["cost"] == expected
        # Old executions without an audit root are unknown, never a measured zero.
        async with session_factory() as session:
            await session.execute(delete(Event).where(Event.id == root_id))
            await session.commit()
        assert (await api.get(f"/runs/{run['id']}")).json()["cost"] is None
