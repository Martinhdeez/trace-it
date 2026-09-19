"""The process and rule endpoints against the local database (`make test-db`)."""

import uuid

import pytest

from app.core.database import session_factory
from app.features.agents import llm
from app.features.sources.model import Source
from tests.support.users import manager_client

INVOICES = {
    "decision_types": [
        {"name": "ESCALAR", "priority": 3, "requires_human": True},
        {"name": "NO_PAGAR", "priority": 2},
        {"name": "PAGAR", "priority": 1, "is_default": True},
    ],
    # `required` is optional: `supplier` leaves it out.
    "symbols": [
        {"name": "amount", "type": "number", "required": True},
        {"name": "supplier", "type": "text"},
    ],
}


async def test_process_rule_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    async def llm_down(*args, **kwargs):
        raise llm.AgentError("no LLM in tests")

    monkeypatch.setattr(llm, "run", llm_down)
    suffix = uuid.uuid4().hex[:8]
    async with manager_client() as api:
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
        assert [(s["name"], s["required"]) for s in process["symbols"]] == [
            ("amount", True),
            ("supplier", False),
        ]
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
        # Saved as `compiling`; the background compilation fails (no LLM) and leaves it
        # a draft with the error; published configuration remains unchanged.
        assert rule["status"] == "compiling"
        rule = (await api.get(f"/rules/{rule['id']}")).json()
        assert rule["status"] == "draft"
        assert rule["report"]["valid"] is False
        assert rule["report"]["error"] == "CompilationError: no LLM in tests"

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
    async with manager_client() as api:
        r = await api.post(
            "/processes/definition",
            json={"name": f"conflict-{uuid.uuid4().hex[:8]}", "decision_types": types},
        )
        assert r.status_code == 422, r.text
        assert message in r.text


async def test_manager_can_delete_an_unpublished_process() -> None:
    name = f"delete-me-{uuid.uuid4().hex[:8]}"
    async with manager_client() as api:
        response = await api.post(
            "/processes/definition",
            json={"name": name, **INVOICES},
        )
        assert response.status_code == 200, response.text
        process_id = response.json()["process"]["id"]

        response = await api.delete(f"/processes/{process_id}")

        assert response.status_code == 204, response.text
        assert (await api.get(f"/processes/{process_id}")).status_code == 404
        assert all(process["id"] != process_id for process in (await api.get("/processes")).json())


async def test_process_with_source_history_cannot_be_deleted() -> None:
    name = f"keep-me-{uuid.uuid4().hex[:8]}"
    async with manager_client() as api:
        response = await api.post(
            "/processes/definition",
            json={"name": name, **INVOICES},
        )
        assert response.status_code == 200, response.text
        process_id = response.json()["process"]["id"]

        async with session_factory() as session:
            session.add(Source(process_id=process_id, name="test", origin="test", rows=[]))
            await session.commit()

        response = await api.delete(f"/processes/{process_id}")

        assert response.status_code == 409, response.text
        assert "source loads" in response.json()["message"]
        assert (await api.get(f"/processes/{process_id}")).status_code == 200
