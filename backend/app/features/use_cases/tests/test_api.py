"""The agent configuration endpoints, against the local database (`make test-db`)."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import session_factory
from app.features.use_cases import service
from app.main import app
from tests.support.users import manager


@pytest.fixture
async def api():
    """A client, a use case and the headers of a manager and an operator."""
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        use_case = await service.ensure(session, f"use case {suffix}", "Conventions")
        await session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"manager": await manager(name="manager")}
        r = await client.post(
            "/users",
            json={"name": "operator", "email": f"operator-{suffix}@x.com", "role": "operator"},
            headers=headers["manager"],
        )
        headers["operator"] = {"X-User-Id": str(r.json()["id"])}
        yield client, use_case.id, headers


async def _put(client: AsyncClient, use_case_id: int, headers: dict, text: str):
    body = {"config": {"instructions": text}, "note": text}
    return await client.put(f"/use-cases/{use_case_id}/agents/compiler", json=body, headers=headers)


async def _versions(client: AsyncClient, use_case_id: int) -> list[tuple[int, bool]]:
    r = await client.get(f"/use-cases/{use_case_id}/agents/compiler/versions")
    assert r.status_code == 200, r.text
    return [(v["version"], v["active"]) for v in r.json()]


async def test_put_creates_an_active_version(api) -> None:
    client, use_case_id, headers = api
    await _put(client, use_case_id, headers["manager"], "first")
    r = await _put(client, use_case_id, headers["manager"], "second")

    assert r.status_code == 200, r.text
    assert r.json()["version"] == 2 and r.json()["active"] is True
    assert await _versions(client, use_case_id) == [(1, False), (2, True)]
    detail = (await client.get(f"/use-cases/{use_case_id}")).json()
    assert [a["config"]["instructions"] for a in detail["agents"]] == ["second"]


async def test_an_operator_cannot_configure(api) -> None:
    client, use_case_id, headers = api
    r = await _put(client, use_case_id, headers["operator"], "first")

    assert r.status_code == 403, r.text
    assert await _versions(client, use_case_id) == []


async def test_activating_an_older_version_rolls_back(api) -> None:
    client, use_case_id, headers = api
    first = (await _put(client, use_case_id, headers["manager"], "first")).json()
    await _put(client, use_case_id, headers["manager"], "second")

    r = await client.post(f"/agent-configs/{first['id']}/activate", headers=headers["manager"])

    assert r.status_code == 200, r.text
    assert await _versions(client, use_case_id) == [(1, True), (2, False)]
