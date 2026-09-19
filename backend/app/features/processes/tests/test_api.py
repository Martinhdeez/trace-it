"""The process and rule endpoints against the local database (`make test-db`)."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.features.agents import llm
from app.main import app

INVOICES = {
    "decision_types": [
        {"name": "ESCALAR", "priority": 3, "requires_human": True},
        {"name": "NO_PAGAR", "priority": 2},
        {"name": "PAGAR", "priority": 1, "is_default": True},
    ],
    "symbols": [{"name": "amount", "type": "number"}, {"name": "supplier", "type": "text"}],
}


async def test_process_rule_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    async def llm_down(*args, **kwargs):
        raise llm.AgentError("no LLM in tests")

    monkeypatch.setattr(llm, "run", llm_down)
    suffix = uuid.uuid4().hex[:8]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.post(
            "/users",
            json={"name": "Ana", "email": f"ana-{suffix}@x.com", "role": "manager"},
        )
        assert r.status_code == 201, r.text
        r = await api.post("/login", json={"email": f"ana-{suffix}@x.com"})
        assert r.status_code == 200, r.text
        headers = {"X-User-Id": str(r.json()["id"])}

        r = await api.post("/processes/definition", json={"name": f"invoices-{suffix}", **INVOICES})
        assert r.status_code == 200, r.text
        process = r.json()["process"]
        assert [t["name"] for t in process["decision_types"]] == ["ESCALAR", "NO_PAGAR", "PAGAR"]
        assert [t["requires_human"] for t in process["decision_types"]] == [True, False, False]
        assert len(process["symbols"]) == 2
        assert (await api.get(f"/processes/{process['id']}")).json() == process

        r = await api.post(
            f"/processes/{process['id']}/rules",
            json={
                "text": "If amount > 1000, escalate",
                "type": "prohibition",
                "decision": "ESCALAR",
            },
        )
        assert r.status_code == 201, r.text
        rule = r.json()
        # Saved as `compiling`; the background compilation fails (no LLM) and leaves a
        # draft with the error, never a rule stuck in `compiling`.
        assert rule["status"] == "compiling"
        rule = (await api.get(f"/rules/{rule['id']}")).json()
        assert rule["status"] == "draft"
        assert rule["report"] == {"valid": False, "error": "CompilationError: no LLM in tests"}

        r = await api.post(f"/rules/{rule['id']}/compile")
        assert r.status_code == 502, r.text
        assert r.json()["code"] == "compilation_failed"

        r = await api.post(f"/rules/{rule['id']}/activate", headers=headers)
        assert r.status_code == 409, r.text
        assert "not compiled" in r.json()["message"]


@pytest.mark.parametrize(
    ("types", "message"),
    [
        (
            [{"name": "REVIEW", "priority": 1, "is_default": True, "requires_human": True}],
            "default decision type cannot require a human",
        ),
        (
            [{"name": "PAGAR", "priority": 1, "is_default": True}],
            "At least one decision type must require a human",
        ),
        (
            [{"name": "A", "priority": 1, "is_default": True}, {"name": "B", "priority": 1}],
            "share a priority",
        ),
    ],
)
async def test_inconsistent_decision_types_are_refused(types: list, message: str) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.post(
            "/processes/definition",
            json={"name": f"conflict-{uuid.uuid4().hex[:8]}", "decision_types": types},
        )
        assert r.status_code == 422, r.text
        assert message in r.text
