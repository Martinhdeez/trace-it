"""The trace endpoints over a real run, against the local database (`make test-db`). Same
setup as `decisions/tests/test_api.py`: seeded instances and rules, the sandbox faked."""

import pytest

from app.features.agents import sandbox
from app.features.decisions.tests.test_api import FAKE_SANDBOX, client, create_process


@pytest.fixture
def fake_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "run_dataset", FAKE_SANDBOX)


def steps(nodes: list[dict]) -> list:
    """A tree as nested (step, children)."""
    return [(n["step"], steps(n["children"])) for n in nodes]


async def test_run_journey_and_metrics(fake_sandbox: None) -> None:
    async with client() as api:
        process_id, headers = await create_process(api, "manager")
        assert (await api.post(f"/processes/{process_id}/run")).status_code == 200
        [escalated] = (await api.get(f"/processes/{process_id}/queue")).json()
        r = await api.post(
            f"/instances/{escalated['id']}/resolve",
            json={"decision": "NO_PAGAR", "reason": "checked by phone"},
            headers=headers,
        )
        assert r.status_code == 200, r.text

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
        assert metrics["decisions_by_outcome"] == {"PAGAR": 1, "NO_PAGAR": 2, "ESCALAR": 1}
        assert metrics["escalated"] == 0 and metrics["pending"] == 1
        assert metrics["failures"] == {"RULE_ERROR": 0, "RULE_NEEDS_DATA": 0, "RULE_CONFLICT": 0}
