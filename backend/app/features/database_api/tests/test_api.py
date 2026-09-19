"""Real PostgreSQL tests: authorization, isolation, CRUD, concurrency and audit atomicity."""

import asyncio
import base64
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import text

from app.core.api_auth import API_USER_EMAIL
from app.core.config import settings
from app.core.database import session_factory
from app.main import app

TOKEN = "test-api-token-not-production"


@pytest.fixture
async def api(monkeypatch):
    monkeypatch.setattr(settings, "api_token", SecretStr(TOKEN))
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {TOKEN}"},
    ) as client:
        yield client


def user_values():
    return {"name": "API test", "email": f"api-{uuid.uuid4().hex}@test", "role": "operator"}


@pytest.mark.parametrize("authorization", ["", "Bearer wrong", "Bearer", "Basic abc", " "])
async def test_database_requires_valid_bearer(api, authorization):
    response = await api.get("/db/tables", headers={"Authorization": authorization})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_disabled_token_fails_closed(api, monkeypatch):
    monkeypatch.setattr(settings, "api_token", SecretStr(""))
    assert (await api.get("/db/tables")).status_code == 401
    assert (await api.get("/processes")).status_code == 401


async def test_bearer_works_for_business_routes_and_cannot_impersonate(api):
    response = await api.get("/me", headers={"X-User-Id": "999999"})
    assert response.status_code == 200, response.text
    assert response.json()["email"] == API_USER_EMAIL
    assert response.json()["role"] == "manager"
    response = await api.post("/users", json=user_values())
    assert response.status_code == 201, response.text
    assert (await api.get("/processes")).status_code == 200
    response = await api.get("/processes", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401


async def test_crud_audits_etags_filters_and_export(api):
    table = "/db/tables/users"
    values = user_values()
    response = await api.post(f"{table}/rows", json={"values": values, "reason": "Create test"})
    assert response.status_code == 201, response.text
    created = response.json()
    key = created["key"]
    response = await api.get(f"{table}/row", params={"key": json.dumps(key)})
    assert response.status_code == 200, response.text
    assert response.json()["etag"] == created["etag"]
    patch = {
        "key": key,
        "values": {"name": "Updated through API"},
        "expected_etag": created["etag"],
        "reason": "Correct test name",
    }
    response = await api.patch(f"{table}/row", json=patch)
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["etag"] != created["etag"]
    assert (await api.patch(f"{table}/row", json=patch)).status_code == 409
    response = await api.get(f"{table}/rows", params={"filters": json.dumps(key)})
    assert response.json()["rows"] == [{k: v for k, v in updated.items() if k != "change_id"}]
    assert response.headers["cache-control"] == "no-store"
    response = await api.get(f"{table}/export", params={"filters": json.dumps(key)})
    assert json.loads(response.text)["name"] == "Updated through API"
    response = await api.delete(
        f"{table}/row",
        # httpx delete() has no json parameter; use request() below instead.
    )
    assert response.status_code == 422
    response = await api.request(
        "DELETE",
        f"{table}/row",
        json={"key": key, "expected_etag": updated["etag"], "reason": "Remove test"},
    )
    assert response.status_code == 200, response.text
    assert (await api.get(f"{table}/row", params={"key": json.dumps(key)})).status_code == 404
    changes = (
        await api.get(
            "/db/tables/database_api_changes/rows",
            params={"filters": json.dumps({"table_name": "users", "key": key})},
        )
    ).json()["rows"]
    assert [r["values"]["operation"] for r in changes] == ["insert", "update", "delete"]
    assert changes[1]["values"]["before"]["name"] == values["name"]
    assert changes[1]["values"]["after"]["name"] == "Updated through API"
    assert all(r["values"]["actor"] == API_USER_EMAIL for r in changes)


@pytest.mark.parametrize(
    "table", ["pg_authid", "pg_class", "alembic_version", "public.users", "other_app", "users;DROP"]
)
async def test_only_registered_app_tables_are_accessible(api, table):
    assert (await api.get(f"/db/tables/{table}/rows")).status_code == 404
    assert (await api.get(f"/db/tables/{table}/schema")).status_code == 404
    response = await api.post(
        f"/db/tables/{table}/rows", json={"values": {}, "reason": "Isolation test"}
    )
    assert response.status_code == 404


async def test_schema_pagination_injection_and_validation(api):
    tables = (await api.get("/db/tables")).json()
    assert "users" in {t["name"] for t in tables}
    assert "alembic_version" not in {t["name"] for t in tables}
    response = await api.get("/db/tables/users/schema")
    assert response.status_code == 200, response.text
    schema = response.json()
    assert schema["primary_key"] == ["id"]
    assert next(c for c in schema["columns"] if c["name"] == "id")["generated"]
    page = (await api.get("/db/tables/users/rows", params={"limit": 1})).json()
    assert len(page["rows"]) == 1
    assert page["next_offset"] == 1
    assert (await api.get("/db/tables/users/rows?limit=201")).status_code == 422
    assert (await api.get("/db/tables/users/rows?offset=-1")).status_code == 422
    for filters in ('{"missing":1}', "[]", "not-json", '{"id":"1 OR 1=1"}'):
        assert (
            await api.get("/db/tables/users/rows", params={"filters": filters})
        ).status_code == 422
    response = await api.get(
        "/db/tables/users/rows", params={"filters": json.dumps({"name": "' OR 1=1 --"})}
    )
    assert response.json()["rows"] == []
    for values in ({"id": 99999}, {"unknown": True}):
        response = await api.post(
            "/db/tables/users/rows", json={"values": values, "reason": "Invalid test"}
        )
        assert response.status_code == 422, response.text


async def test_conflicts_do_not_create_audit_records(api):
    values = user_values()
    reason = uuid.uuid4().hex
    payload = {"values": values, "reason": reason}
    assert (await api.post("/db/tables/users/rows", json=payload)).status_code == 201
    response = await api.post("/db/tables/users/rows", json=payload)
    assert response.status_code == 409
    assert "INSERT" not in response.text
    rows = (
        await api.get(
            "/db/tables/database_api_changes/rows",
            params={"filters": json.dumps({"reason": reason})},
        )
    ).json()["rows"]
    assert len(rows) == 1


async def test_audit_and_api_identity_are_reserved(api):
    for name in ("events", "database_api_changes"):
        response = await api.post(
            f"/db/tables/{name}/rows", json={"values": {}, "reason": "Tampering test"}
        )
        assert response.status_code == 403
    record = (
        await api.get(
            "/db/tables/users/rows", params={"filters": json.dumps({"email": API_USER_EMAIL})}
        )
    ).json()["rows"][0]
    response = await api.request(
        "DELETE",
        "/db/tables/users/row",
        json={"key": record["key"], "expected_etag": record["etag"], "reason": "Tampering test"},
    )
    assert response.status_code == 403


async def test_binary_composite_key_and_missing_primary_key(api):
    # files uses a text primary key; discovery_revisions uses a composite primary key.
    content = b"\x00\xffbinary"
    values = {
        "hash": uuid.uuid4().hex,
        "name": "test.bin",
        "content": {"$base64": base64.b64encode(content).decode()},
    }
    response = await api.post(
        "/db/tables/files/rows", json={"values": values, "reason": "Binary test"}
    )
    assert response.status_code == 201, response.text
    assert response.json()["values"]["content"] == values["content"]
    response = await api.get("/db/tables/discovery_revisions/row", params={"key": '{"draft_id":1}'})
    assert response.status_code == 422
    assert (await api.get("/db/tables/users/row", params={"key": "{}"})).status_code == 422


async def test_body_limit_and_authorization_precede_parsing(api):
    response = await api.post("/db/tables/users/rows", content="x" * (2 * 1024 * 1024 + 1))
    assert response.status_code == 413
    response = await api.post(
        "/db/tables/users/rows", content="bad-json", headers={"Authorization": "Bearer wrong"}
    )
    assert response.status_code == 401


async def test_execution_boundaries_on_direct_database_writes(api):
    for field, value in (
        ("local_endpoint", "http://169.254.169.254"),
        ("compatible_endpoint", "http://other-app:8000"),
        ("primary_model_dir", "/etc"),
        ("verification_model_dir", "/srv/.models/../../etc"),
    ):
        response = await api.post(
            "/db/tables/process_versions/rows",
            json={"values": {"snapshot": {field: value}}, "reason": "Boundary test"},
        )
        assert response.status_code == 422
        assert "deployment" in response.text


async def test_audit_failure_rolls_back_mutation(api, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession

    values = user_values()

    async def fail_flush(*args, **kwargs):
        raise RuntimeError("Audit unavailable")

    monkeypatch.setattr(AsyncSession, "flush", fail_flush)
    with pytest.raises(RuntimeError, match="Audit unavailable"):
        await api.post("/db/tables/users/rows", json={"values": values, "reason": "Rollback test"})
    async with session_factory() as session:
        assert not await session.scalar(
            text("SELECT EXISTS (SELECT 1 FROM users WHERE email=:email)"),
            {"email": values["email"]},
        )


async def test_concurrent_updates_have_one_winner(api):
    created = (
        await api.post(
            "/db/tables/users/rows", json={"values": user_values(), "reason": "Concurrency test"}
        )
    ).json()
    payload = {"key": created["key"], "expected_etag": created["etag"], "reason": "Concurrent edit"}
    results = await asyncio.gather(
        api.patch("/db/tables/users/row", json={**payload, "values": {"name": "First"}}),
        api.patch("/db/tables/users/row", json={**payload, "values": {"name": "Second"}}),
    )
    assert sorted(r.status_code for r in results) == [200, 409]


async def test_unregistered_existing_table_is_invisible(api):
    async with session_factory() as session:
        await session.execute(text("CREATE TABLE IF NOT EXISTS outside_app (secret text)"))
        await session.commit()
    try:
        assert (await api.get("/db/tables/outside_app/rows")).status_code == 404
        assert "outside_app" not in {t["name"] for t in (await api.get("/db/tables")).json()}
    finally:
        async with session_factory() as session:
            await session.execute(text("DROP TABLE outside_app"))
            await session.commit()


async def test_typed_execution_and_runtime_endpoint_boundaries(api):
    from app.features.agents.llm import resolve
    from app.features.processes.execution import ExecutionSettings

    with pytest.raises(ValueError, match="deployment configuration"):
        resolve("local:model", "http://other-app:8000/v1")
    # Check the typed business validator as well as raw snapshot writes.
    with pytest.raises(ValueError, match="deployment configuration"):
        ExecutionSettings.model_validate(
            {
                "local_endpoint": "http://169.254.169.254/v1",
                "agents": {},
                "extraction": {
                    "primary_model_dir": "/srv/.models",
                    "verification_model_dir": "/srv/.models/verify",
                },
            }
        )


def test_runtime_role_has_only_application_grants(monkeypatch):
    import psycopg
    from sqlalchemy.engine import make_url

    from app.features.database_api import provision
    from tests.support.prepare_db import is_test_db

    url = make_url(settings.database_url)
    assert is_test_db(url.database), "Provisioning test must use a disposable test database"
    password = uuid.uuid4().hex
    monkeypatch.setenv("TRACE_APP_DATABASE_PASSWORD", password)
    provision.main()
    url = url.set(drivername="postgresql", username="trace_app", password=password)
    with psycopg.connect(url.render_as_string(hide_password=False), autocommit=True) as conn:
        assert conn.execute("SELECT count(*) FROM users").fetchone()[0] > 0
        for statement in (
            "CREATE TABLE forbidden (id int)",
            "SELECT * FROM alembic_version",
            "DELETE FROM database_api_changes",
            "SELECT pg_read_file('/etc/passwd')",
            "CREATE ROLE forbidden",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(statement)
