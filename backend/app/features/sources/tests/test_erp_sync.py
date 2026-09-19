"""Syncs against the real challenge ERP (a local subprocess) and the local database:
`docker compose up db -d` and migrations applied."""

import json
import shutil
import uuid
from collections import Counter
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.database import session_factory
from app.core.events import Event
from app.features.processes.model import Process
from app.features.sources import service
from app.features.sources.http_connector import HttpConnector
from app.features.sources.model import Source
from app.features.sources.tests.conftest import SOURCES_JSON, erp_config, start_erp
from app.main import app
from tests.support import challenge, rows

SEED_ORIGIN = "erp:test-seed"


def expected_rows() -> list[dict]:
    """The ERP's own embedded export, shaped as the connector stores it (offline oracle)."""
    rows = [{**r, "amount": f"{float(r['amount']):.2f}"} for r in challenge.sources()["erp"]]
    return sorted(rows, key=lambda r: r["entry_id"])


async def new_process() -> int:
    async with session_factory() as session:
        process = await rows.process(session, f"erp-sync-{uuid.uuid4().hex[:8]}")
        await session.commit()
        return process.id


async def snapshots(process_id: int) -> list[Source]:
    async with session_factory() as session:
        return list(
            await session.scalars(
                select(Source).where(Source.process_id == process_id).order_by(Source.id)
            )
        )


async def test_full_sync_with_the_pack_configuration(erp: str) -> None:
    """All 516 entries through ORA-00600 every 10th call, twice, identical both times."""
    process_id = await new_process()
    config = erp_config(erp)
    async with session_factory() as session:
        first = await service.sync(session, process_id, "erp", config)
        second = await service.sync(session, process_id, "erp", config)

    assert first.rows == 516
    assert first.stats["pages"] == 26
    assert first.stats["transient_errors"]["ORA-00600"] >= 2  # 28+ authenticated calls
    assert first.stats["rate_limited"] == 0  # the client stays under the limit on its own
    assert first.diff.summary() == {"added": 516, "removed": 0, "changed": 0}
    assert second.diff.summary() == {"added": 0, "removed": 0, "changed": 0}
    assert first.rows_hash == second.rows_hash

    stored = await snapshots(process_id)
    assert [s.id for s in stored] == [first.source_id, second.source_id]
    rows = stored[-1].rows
    assert stored[-1].origin.startswith("erp:") and stored[-1].origin.endswith(f"|{erp}")
    assert Counter(r["status"] for r in rows) == {"PENDIENTE": 507, "PAGADA": 9}
    assert [r["entry_id"] for r in rows] == sorted(r["entry_id"] for r in rows)
    assert all("_invalid" not in r for r in rows)
    assert rows[0] == {
        "entry_id": "AS-00001",
        "date": "2026-01-31",
        "supplier_id": "P003",
        "nif": "B30455812",
        "purchase_order": "PO-2026-0001",
        "amount": "9221.75",
        "status": "PENDIENTE",
    }
    # What the API served is exactly the ERP's own data (read offline from its source).
    assert rows == expected_rows()

    async with session_factory() as session:
        event = await session.scalar(
            select(Event).where(
                Event.step == "sync_source", Event.data["source_id"].as_integer() == first.source_id
            )
        )
    assert event.data["rows"] == 516 and event.data["retries"] >= 2


async def test_429_is_honoured(erp: str) -> None:
    """A client configured above the server's 10 requests/s gets 429s and still finishes."""
    config = erp_config(erp, rate_limit={"requests_per_second": 100})
    connector = HttpConnector(config)
    rows = await connector.download()
    assert len(rows) == 516
    assert connector.stats.rate_limited >= 1


async def test_token_renewed_by_uses(erp: str) -> None:
    config = erp_config(
        erp, auth={"max_uses": 5, "renew_margin_uses": 1}, rate_limit={"requests_per_second": 9}
    )
    connector = HttpConnector(config)
    assert len(await connector.download()) == 516
    assert connector.stats.logins >= 7  # 26 pages plus retries, 4 calls per token


async def test_failed_sync_keeps_the_previous_snapshot() -> None:
    process_id = await new_process()
    async with session_factory() as session:
        session.add(
            Source(process_id=process_id, name="erp", origin=SEED_ORIGIN, rows=expected_rows())
        )
        await session.commit()

    down = httpx.MockTransport(lambda r: httpx.Response(503, content=b"down"))
    config = erp_config("http://down", retry={"max_attempts": 2, "backoff_seconds": 0.001})
    async with session_factory() as session:
        with pytest.raises(service.SourceUnavailableError, match="previous snapshot stays"):
            await service.sync(session, process_id, "erp", config, transport=down)

    stored = await snapshots(process_id)
    assert [s.origin for s in stored] == [SEED_ORIGIN]
    async with session_factory() as session:
        failure = await session.scalar(
            select(Event)
            .where(Event.step == "sync_source", Event.status == "error")
            .order_by(Event.id.desc())
        )
    assert "gave up after 2 attempts" in failure.data["error"]


def batch2_csv(folder: Path) -> Path:
    """A Saturday-style update: one entry becomes paid with a new amount, one is added."""
    path = folder / "erp_export_lote2.csv"
    path.write_text(
        "asiento_id,fecha_registro,proveedor_id,nif,pedido,importe_esperado,estado\n"
        "AS-00001,2026-01-31,P003,B30455812,PO-2026-0001,9300.00,PAGADA\n"
        "AS-00999,2026-03-01,P004,B12345678,PO-2026-0999,1234.5,PENDIENTE\n",
        encoding="utf-8",
    )
    return path


async def test_sync_endpoint_and_diff_after_an_erp_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, erp: str
) -> None:
    process_id = await new_process()
    async with session_factory() as session:
        name = (await session.get(Process, process_id)).name
    # A pack folder for this process, with the real sources.json, re-read on every sync.
    (tmp_path / "pack.json").write_text(json.dumps({"name": name}))
    (tmp_path / "pack").mkdir()
    shutil.copy(SOURCES_JSON, tmp_path / "pack/sources.json")
    monkeypatch.setattr(settings, "processes_dir", tmp_path)

    updated, updated_url = start_erp("--lote2", str(batch2_csv(tmp_path)))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as api:
            monkeypatch.setenv("TRACE_ERP_URL", erp)
            r = await api.post(f"/processes/{process_id}/sources/erp/sync")
            assert r.status_code == 200, r.text
            assert r.json()["rows"] == 516

            monkeypatch.setenv("TRACE_ERP_URL", updated_url)
            r = await api.post(f"/processes/{process_id}/sources/erp/sync")
            assert r.status_code == 200, r.text
            result = r.json()
            assert result["rows"] == 517
            assert result["stats"]["status"] == {"entries": "517", "update_loaded": "SI"}

            r = await api.get(f"/processes/{process_id}/sources/erp/diff")
            assert r.status_code == 200, r.text
            diff = r.json()
    finally:
        updated.kill()
        updated.wait()

    assert diff == result["diff"]
    assert diff["added"] == ["AS-00999"]
    assert diff["removed"] == []
    assert diff["changed"] == {
        "AS-00001": {"amount": ["9221.75", "9300.00"], "status": ["PENDIENTE", "PAGADA"]}
    }


async def test_sync_endpoint_unknown_process() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as api:
        r = await api.post("/processes/999999999/sources/erp/sync")
    assert r.status_code == 404
