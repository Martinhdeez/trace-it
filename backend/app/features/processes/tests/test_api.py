"""End-to-end against the local database: `docker compose up db -d` and migrations applied."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_process_rule_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    async def llm_down(*args, **kwargs):
        raise RuntimeError("no LLM in tests")

    monkeypatch.setattr("app.features.llm.client.complete", llm_down)
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

        r = await api.post(
            "/processes",
            json={
                "name": f"invoices-{suffix}",
                "decision_types": [
                    {"name": "ESCALAR", "priority": 3, "requires_human": True},
                    {"name": "NO_PAGAR", "priority": 2},
                    {"name": "PAGAR", "priority": 1, "is_default": True},
                ],
                "symbols": [
                    {"name": "amount", "type": "number"},
                    {"name": "supplier", "type": "text"},
                ],
            },
        )
        assert r.status_code == 201, r.text
        process = r.json()
        assert [t["name"] for t in process["decision_types"]] == ["ESCALAR", "NO_PAGAR", "PAGAR"]
        assert [t["requires_human"] for t in process["decision_types"]] == [True, False, False]
        assert len(process["symbols"]) == 2

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
        assert rule["status"] == "draft"

        r = await api.post(f"/rules/{rule['id']}/compile")
        assert r.status_code == 502, r.text
        assert r.json()["code"] == "compilation_failed"

        r = await api.post(f"/rules/{rule['id']}/activate", headers=headers)
        assert r.status_code == 409, r.text


async def test_default_cannot_require_a_human() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.post(
            "/processes",
            json={
                "name": f"conflict-{uuid.uuid4().hex[:8]}",
                "decision_types": [
                    {
                        "name": "REVIEW",
                        "priority": 1,
                        "is_default": True,
                        "requires_human": True,
                    }
                ],
            },
        )
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "conflict"
