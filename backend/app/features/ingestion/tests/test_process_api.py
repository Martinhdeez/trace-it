"""Real PostgreSQL integration; enable with TRACEPAY_TEST_POSTGRES=1 after migrations."""

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.database import engine, session_factory
from app.features.ingestion.model import File, Instance
from app.features.ingestion.runtime import current_service
from app.features.ingestion.service import ExtractionService
from app.features.processes.model import DecisionType, Process
from app.features.traces.model import Event
from app.features.users.model import User
from app.main import app

from .conftest import VALID, NoOCR, NoVLM, pdf_bytes

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("TRACEPAY_TEST_POSTGRES") != "1", reason="Requires test PostgreSQL"
    ),
]


@pytest.fixture
async def process_api(settings):
    suffix = uuid.uuid4().hex
    async with session_factory() as session:
        process = Process(name="Ingestion test " + suffix, description="Generic process")
        user = User(name="Operator", email=suffix + "@test.invalid", role="operator")
        session.add_all([process, user])
        await session.flush()
        session.add(DecisionType(process_id=process.id, name="ACCEPT", priority=0, is_default=True))
        await session.commit()
        process_id, user_id = process.id, user.id
    service = ExtractionService(settings, NoOCR(), NoVLM())
    app.dependency_overrides[current_service] = lambda: service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-User-Id": str(user_id)},
        ) as client:
            yield client, process_id, service
    finally:
        app.dependency_overrides.pop(current_service)
        await engine.dispose()


async def test_upload_persists_original_and_evidence_without_approving_symbols(process_api):
    client, process_id, service = process_api
    content = pdf_bytes(VALID)
    response = await client.post(
        f"/processes/{process_id}/files", files={"file": ("invoice.pdf", content)}
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["created"] and result["status"] == "PENDING"
    async with session_factory() as session:
        original = await session.get(File, result["file_hash"])
        instance = await session.get(Instance, result["instance_id"])
        assert original.content == content and "F26-1234" in original.text
        assert instance.symbols is None
        event = await session.scalar(select(Event).where(Event.instance_id == instance.id))
        assert event.step == "ingest_document"
        assert event.data["extraction"]["sha256"] == result["file_hash"]
    # Recovery uses PostgreSQL, not the standalone SQLite result cache.
    service.store.result = lambda _: pytest.fail("Must read PostgreSQL evidence")
    stored = await client.get(f"/instances/{result['instance_id']}/document")
    assert stored.status_code == 200
    assert stored.json() == result["extraction"]


async def test_reupload_preserves_instance_state_and_distinguishes_file_names(process_api):
    client, process_id, _ = process_api
    content = pdf_bytes(VALID + "\n" + uuid.uuid4().hex)
    endpoint = f"/processes/{process_id}/files"
    first = (await client.post(endpoint, files={"file": ("original.pdf", content)})).json()
    async with session_factory() as session:
        instance = await session.get(Instance, first["instance_id"])
        instance.status = "DECIDED"
        instance.symbols = {"approved_by_another_stage": {"value": True}}
        await session.commit()
    again = (await client.post(endpoint, files={"file": ("original.pdf", content)})).json()
    other = (await client.post(endpoint, files={"file": ("copy.pdf", content)})).json()
    assert again["instance_id"] == first["instance_id"]
    assert again["status"] == "DECIDED" and not again["created"]
    assert other["instance_id"] != first["instance_id"] and other["created"]
    assert other["file_hash"] == first["file_hash"]
    async with session_factory() as session:
        instance = await session.get(Instance, first["instance_id"])
        assert instance.symbols["approved_by_another_stage"]["value"] is True
        assert (
            await session.scalar(
                select(func.count()).select_from(File).where(File.hash == first["file_hash"])
            )
            == 1
        )


async def test_unreadable_scan_does_not_decide_the_process_review_state(process_api):
    client, process_id, _ = process_api
    response = await client.post(
        f"/processes/{process_id}/files",
        files={"file": ("scan.pdf", pdf_bytes(""))},
        data={"ocr": "false", "vlm": "false", "jev": "false"},
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["status"] == "PENDING"
    queue = await client.get(f"/processes/{process_id}/queue")
    assert not any(row["id"] == result["instance_id"] for row in queue.json())
    detail = (await client.get(f"/instances/{result['instance_id']}")).json()
    assert detail["symbols"] is None and detail["decisions"] == []


async def test_generic_document_is_not_forced_into_invoice_symbols(process_api):
    client, process_id, _ = process_api
    response = await client.post(
        f"/processes/{process_id}/files",
        files={
            "file": (
                "receipt.pdf",
                pdf_bytes("Travel request\nDestination: London\nReason: annual conference"),
            )
        },
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert "status" not in result["extraction"]
    assert result["status"] == "PENDING"


async def test_unknown_process_is_rejected_before_processing(process_api):
    client, _, service = process_api
    response = await client.post(
        "/processes/2147483647/files", files={"file": ("test.pdf", pdf_bytes(VALID))}
    )
    assert response.status_code == 404 and response.json()["code"] == "not_found"
    assert not list(service.objects.iterdir())
