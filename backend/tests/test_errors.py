"""Error shapes (B3): a 500 is `{code, message}` and an `error` span; a 422 keeps `{detail}`."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core import events
from app.main import app


async def test_an_unhandled_error_is_json_and_traced(monkeypatch: pytest.MonkeyPatch) -> None:
    written: list[dict] = []
    monkeypatch.setattr(events, "_write", written.extend)

    async def boom() -> None:
        raise RuntimeError("secret detail")

    app.add_api_route("/test-boom", boom, include_in_schema=False)
    try:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://t") as api:
            r = await api.get("/test-boom")
    finally:
        app.router.routes.pop()

    assert r.status_code == 500
    body = r.json()
    assert body["code"] == "internal_error"
    assert "secret detail" not in body["message"] and "Traceback" not in r.text
    assert r.headers["access-control-allow-origin"] == "*"  # the console can read it
    [span] = [w for w in written if w["step"] == "unhandled_error"]
    assert span["status"] == "error"
    assert span["data"]["error"] == "RuntimeError: secret detail"
    assert span["trace_id"] in body["message"]


async def test_a_validation_error_keeps_detail() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as api:
        r = await api.post("/login", json={})
    assert r.status_code == 422
    assert "detail" in r.json()
