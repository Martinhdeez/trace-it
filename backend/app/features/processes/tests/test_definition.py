"""Loading process definitions from `processes/*.json`, against the local database."""

import json
import uuid
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.core.database import session_factory
from app.features.processes.definition import Definition, load_definition
from app.features.rules import service as rules
from app.main import app

PROCESSES = Path(__file__).parents[5] / "processes"


def _definition(file: str, with_code: bool = False) -> dict:
    """The file's definition with a unique process name and emails, so reruns start fresh.

    A rule's `code` names a file next to the definition, which only the CLI can resolve,
    so it is dropped unless a test is specifically about that.
    """
    data = json.loads((PROCESSES / file).read_text(encoding="utf-8"))
    suffix = uuid.uuid4().hex[:8]
    data["name"] += f" {suffix}"
    for u in data.get("users", []):
        u["email"] = f"{suffix}-{u['email']}"
    if not with_code:
        for r in data.get("rules", []):
            r.pop("code", None)
    return data


async def _load(api: AsyncClient, data: dict) -> dict:
    r = await api.post("/processes/definition", json=data)
    assert r.status_code == 200, r.text
    result = r.json()
    r = await api.get(f"/processes/{result['process']['id']}/rules")
    result["rules"] = len(r.json())
    return result


async def test_loading_twice_is_idempotent() -> None:
    data = _definition("invoice-payment.json")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        first = await _load(api, data)
        second = await _load(api, data)
    assert first["new_rules"] == first["rules"] == len(data["rules"])
    assert first["new_users"] == len(data["users"])
    assert second["new_rules"] == second["new_users"] == 0
    assert second["rules"] == first["rules"]
    assert second["process"] == first["process"]
    assert [t["name"] for t in first["process"]["decision_types"]] == [
        "ESCALAR",
        "NO_PAGAR",
        "PAGAR",
    ]


async def test_a_process_that_is_not_about_invoices() -> None:
    data = _definition("travel-expenses.json")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        result = await _load(api, data)
    assert result["rules"] == 2
    assert {t["name"] for t in result["process"]["decision_types"]} == {
        "REVIEW",
        "REJECT",
        "APPROVE",
    }


async def test_two_defaults_are_rejected() -> None:
    data = _definition("travel-expenses.json")
    data["decision_types"][1]["is_default"] = True
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.post("/processes/definition", json=data)
        assert r.status_code == 422, r.text
        assert "exactly one default" in r.text
        names = [p["name"] for p in (await api.get("/processes")).json()]
    assert data["name"] not in names


async def test_two_types_with_the_same_priority_are_rejected() -> None:
    data = _definition("travel-expenses.json")
    data["decision_types"][1]["priority"] = data["decision_types"][0]["priority"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.post("/processes/definition", json=data)
        assert r.status_code == 422, r.text
        assert "share a priority" in r.text
        names = [p["name"] for p in (await api.get("/processes")).json()]
    assert data["name"] not in names


async def test_rules_with_code_in_a_file_are_not_loaded_over_http() -> None:
    """A path would be resolved on the server, against whatever the backend can read."""
    data = _definition("invoice-payment.json", with_code=True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        r = await api.post("/processes/definition", json=data)

    assert r.status_code == 409, r.text
    assert "app.cli" in r.json()["message"]


async def test_from_disk_rules_arrive_with_their_code_and_activate() -> None:
    """How a process runs before any model is configured."""
    data = Definition.model_validate(_definition("invoice-payment.json", with_code=True))

    async with session_factory() as session:
        result = await load_definition(session, data, PROCESSES)
        process_id = result.process.id
        for rule in await rules.list_all(session, process_id, "draft"):
            detail = await rules.get(session, rule.id)
            assert detail.code_a and detail.code_a == detail.code_b
            assert detail.report["origin"] == "hand-written"
            await rules.activate(session, rule.id)

        active = await rules.list_all(session, process_id, "active")

    assert len(active) == len(data.rules) == 16
    assert all(r.hash for r in active)
