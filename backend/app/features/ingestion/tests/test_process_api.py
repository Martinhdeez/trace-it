"""Real PostgreSQL integration; enable with TRACEPAY_TEST_POSTGRES=1 after migrations."""

import asyncio
import os
import threading
import uuid
from dataclasses import replace

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core import events
from app.core.database import engine, session_factory
from app.core.events import Event
from app.features.ingestion.model import File, Instance
from app.features.ingestion.runtime import current_service
from app.features.ingestion.service import ExtractionService
from app.features.processes.model import DecisionType
from app.features.users.model import User
from app.main import app
from tests.support import rows

from .conftest import VALID, NoOCR, NoVLM, pdf_bytes

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("TRACEPAY_TEST_POSTGRES") != "1", reason="Requires test PostgreSQL"
    ),
]


def assert_reused_evidence(reused, original):
    assert reused["id"] == original["id"]
    assert reused["fields"] == original["fields"]
    assert reused["data"] == original["data"]
    assert reused["cache_hit"] is True
    assert reused["metrics"]["request_ms"] >= 0
    for reader in ("ocr", "vlm", "jev"):
        assert reused["metrics"][f"{reader}_calls_this_request"] == 0
        assert reused["metrics"][f"{reader}_cache_hits_this_request"] == 0


@pytest.fixture
async def process_api(settings):
    suffix = uuid.uuid4().hex
    async with session_factory() as session:
        process = await rows.process(session, "Ingestion test " + suffix, "Generic process")
        user = User(name="Operator", email=suffix + "@test.invalid", role="operator")
        session.add(user)
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
        # Upload and ingestion both emit spans; SQL does not guarantee their row order.
        event = await session.scalar(
            select(Event).where(Event.instance_id == instance.id, Event.step == "ingest_document")
        )
        assert event is not None
        assert event.step == "ingest_document"
        assert event.data["extraction"]["sha256"] == result["file_hash"]
    # Recovery uses PostgreSQL, not the standalone SQLite result cache.
    service.store.result = lambda _: pytest.fail("Must read PostgreSQL evidence")
    stored = await client.get(f"/instances/{result['instance_id']}/document")
    assert stored.status_code == 200
    assert stored.json() == result["extraction"]


async def test_different_documents_extract_concurrently(process_api):
    client, process_id, service = process_api
    original = service.extract
    both_running = threading.Barrier(2)

    def synchronized_extract(*args, **kwargs):
        both_running.wait(timeout=2)
        return original(*args, **kwargs)

    service.extract = synchronized_extract
    try:
        first, second = await asyncio.gather(
            client.post(
                f"/processes/{process_id}/files",
                files={"file": ("first.pdf", pdf_bytes(VALID + "\nFIRST"))},
            ),
            client.post(
                f"/processes/{process_id}/files",
                files={"file": ("second.pdf", pdf_bytes(VALID + "\nSECOND"))},
            ),
        )
    finally:
        service.extract = original

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text


async def test_document_locations_and_page_preserve_saved_reading(process_api):
    client, process_id, _ = process_api
    uploaded = await client.post(
        f"/processes/{process_id}/files", files={"file": ("invoice.pdf", pdf_bytes(VALID))}
    )
    assert uploaded.status_code == 201
    instance_id = uploaded.json()["instance_id"]
    endpoint = f"/instances/{instance_id}/document"
    before = (await client.get(endpoint)).json()
    response = await client.get(endpoint + "/locations")
    assert response.status_code == 200
    locations = response.json()
    assert locations["extraction_id"] == before["id"]
    assert locations["sha256"] == before["sha256"]
    assert locations["symbol_fields"]["invoice_number"] == "invoice_number"
    assert "total" not in locations["symbol_fields"]  # No payment adapter on this process.
    assert locations["fields"]["invoice_number"][0]["precision"] == "text"
    assert locations["fields"]["invoice_number"][0]["boxes"]
    page = await client.get(endpoint + "/pages/1")
    assert page.status_code == 200
    assert page.headers["content-type"] == "image/png"
    assert page.content.startswith(b"\x89PNG")
    assert (await client.get(endpoint + "/pages/2")).status_code == 404
    assert (await client.get(endpoint)).json() == before
    client.headers.pop("X-User-Id")
    assert (await client.get(endpoint + "/locations")).status_code == 401
    assert (await client.get(endpoint + "/pages/1")).status_code == 401


async def test_reupload_preserves_instance_state_and_distinguishes_file_names(process_api):
    client, process_id, service = process_api
    content = pdf_bytes(VALID + "\n" + uuid.uuid4().hex)
    endpoint = f"/processes/{process_id}/files"
    first = (await client.post(endpoint, files={"file": ("original.pdf", content)})).json()
    async with session_factory() as session:
        instance = await session.get(Instance, first["instance_id"])
        instance.status = "DECIDED"
        instance.symbols = {"approved_by_another_stage": {"value": True, "origin": "test"}}
        await session.commit()
    original_extract = service.extract
    service.extract = lambda *_: pytest.fail("Decided duplicate must reuse its stored evidence")
    again = (await client.post(endpoint, files={"file": ("original.pdf", content)})).json()
    service.extract = original_extract
    other = (await client.post(endpoint, files={"file": ("copy.pdf", content)})).json()
    assert again["instance_id"] == first["instance_id"]
    assert again["status"] == "DECIDED" and not again["created"]
    assert_reused_evidence(again["extraction"], first["extraction"])
    assert again["symbols"] == {"approved_by_another_stage": {"value": True, "origin": "test"}}
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
        events = list(
            await session.scalars(
                select(Event).where(
                    Event.instance_id == first["instance_id"], Event.step == "ingest_document"
                )
            )
        )
        assert len(events) == 1
    stored = await client.get(f"/instances/{first['instance_id']}/document")
    assert stored.json() == first["extraction"]


async def test_pending_duplicate_and_reextract_reuse_matching_evidence(process_api):
    client, process_id, service = process_api
    content = pdf_bytes(VALID + "\n" + uuid.uuid4().hex)
    endpoint = f"/processes/{process_id}/files"
    first = (await client.post(endpoint, files={"file": ("repeat.pdf", content)})).json()
    original_extract = service.extract
    service.extract = lambda *_: pytest.fail("Matching evidence must not run extraction")
    try:
        duplicate = await client.post(endpoint, files={"file": ("repeat.pdf", content)})
        repeated = await client.post(f"/instances/{first['instance_id']}/extract", json={})
    finally:
        service.extract = original_extract
    assert duplicate.status_code == 201, duplicate.text
    assert repeated.status_code == 200, repeated.text
    assert_reused_evidence(duplicate.json()["extraction"], first["extraction"])
    assert_reused_evidence(repeated.json()["extraction"], first["extraction"])
    async with session_factory() as session:
        events = list(
            await session.scalars(
                select(Event).where(
                    Event.instance_id == first["instance_id"],
                    Event.step.in_(("ingest_document", "extract_document")),
                )
            )
        )
    assert len(events) == 1
    stored = await client.get(f"/instances/{first['instance_id']}/document")
    assert stored.json() == first["extraction"]


async def test_legacy_ignored_ingest_event_is_not_reused_as_applied_evidence(process_api):
    client, process_id, service = process_api
    content = pdf_bytes(VALID + "\n" + uuid.uuid4().hex)
    endpoint = f"/processes/{process_id}/files"
    first = (await client.post(endpoint, files={"file": ("legacy.pdf", content)})).json()
    ignored = {**first["extraction"], "id": "ignored-upload"}
    async with session_factory() as session:
        events.record(
            session,
            "ingest_document",
            process_id=process_id,
            instance_id=first["instance_id"],
            data={"created": False, "extraction": ignored},
        )
        await session.commit()
    original_extract = service.extract
    service.extract = lambda *_: pytest.fail("Matching applied evidence must be reused")
    try:
        duplicate = await client.post(endpoint, files={"file": ("legacy.pdf", content)})
    finally:
        service.extract = original_extract
    assert duplicate.status_code == 201, duplicate.text
    assert_reused_evidence(duplicate.json()["extraction"], first["extraction"])
    stored = await client.get(f"/instances/{first['instance_id']}/document")
    assert stored.json() == first["extraction"]


async def test_changed_options_and_legacy_provenance_refresh_pending(process_api):
    client, process_id, _ = process_api
    content = pdf_bytes(VALID + "\n" + uuid.uuid4().hex)
    first = (
        await client.post(
            f"/processes/{process_id}/files", files={"file": ("changed.pdf", content)}
        )
    ).json()
    endpoint = f"/instances/{first['instance_id']}/extract"
    changed = await client.post(endpoint, json={"ocr": False, "vlm": False, "jev": False})
    assert changed.status_code == 200, changed.text
    assert changed.json()["extraction"]["id"] != first["extraction"]["id"]
    async with session_factory() as session:
        event = await session.scalar(
            select(Event)
            .where(Event.instance_id == first["instance_id"], Event.step == "extract_document")
            .order_by(Event.id.desc())
        )
        data = dict(event.data)
        extraction = dict(data["extraction"])
        extraction["data"] = dict(extraction["data"])
        extraction["data"]["provenance"] = {}
        data["extraction"] = extraction
        event.data = data
        await session.commit()
    legacy = await client.post(endpoint, json={"ocr": False, "vlm": False, "jev": False})
    assert legacy.status_code == 200, legacy.text
    assert legacy.json()["extraction"]["data"]["provenance"]["cache_key"]
    async with session_factory() as session:
        events = list(
            await session.scalars(
                select(Event).where(
                    Event.instance_id == first["instance_id"],
                    Event.step.in_(("ingest_document", "extract_document")),
                )
            )
        )
    assert len(events) == 3


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


@pytest.mark.parametrize("decided", [False, True])
async def test_reupload_only_refreshes_pending_evidence_when_options_change(process_api, decided):
    client, process_id, _ = process_api
    content = pdf_bytes(VALID)
    endpoint = f"/processes/{process_id}/files"
    first = (await client.post(endpoint, files={"file": ("invoice.pdf", content)})).json()
    instance_id = first["instance_id"]
    fresh = await client.post(
        f"/instances/{instance_id}/extract", json={"ocr": False, "vlm": False, "jev": False}
    )
    assert fresh.status_code == 200, fresh.text
    attached = fresh.json()["extraction"]
    if decided:
        async with session_factory() as session:
            instance = await session.get(Instance, instance_id)
            instance.status = "DECIDED"
            await session.commit()

    duplicate = await client.post(endpoint, files={"file": ("invoice.pdf", content)})
    assert duplicate.status_code == 201, duplicate.text
    assert duplicate.json()["created"] is False
    stored = await client.get(f"/instances/{instance_id}/document")
    if decided:
        assert_reused_evidence(duplicate.json()["extraction"], attached)
        assert stored.json() == attached
    else:
        assert duplicate.json()["extraction"]["id"] != attached["id"]
        assert stored.json() == duplicate.json()["extraction"]
    async with session_factory() as session:
        audit = list(
            await session.scalars(
                select(Event)
                .where(Event.instance_id == instance_id, Event.step == "ingest_document")
                .order_by(Event.id)
            )
        )
        assert [event.data["created"] for event in audit] == [True]
        applied = list(
            await session.scalars(
                select(Event)
                .where(Event.instance_id == instance_id, Event.step == "extract_document")
                .order_by(Event.id)
            )
        )
        assert len(applied) == (1 if decided else 2)
        assert applied[-1].data["extraction"] == stored.json()


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


async def test_upload_and_reextraction_are_each_one_trace_of_the_instance(process_api):
    client, process_id, _ = process_api
    content = pdf_bytes(VALID + "\n" + uuid.uuid4().hex)
    r = await client.post(f"/processes/{process_id}/files", files={"file": ("t.pdf", content)})
    instance_id = r.json()["instance_id"]
    options = {"ocr": False, "vlm": False, "jev": False}
    r = await client.post(f"/instances/{instance_id}/extract", json=options)
    assert r.status_code == 200, r.text

    journey = (await client.get(f"/instances/{instance_id}/trace")).json()

    def tree(nodes):
        return [(n["step"], tree(n["children"])) for n in nodes]

    assert tree(journey["spans"]) == [
        (
            "upload_document",
            [("store_file", []), ("extraction", [("native_text", [])]), ("ingest_document", [])],
        ),
        ("reextract_document", [("extraction", [("native_text", [])]), ("extract_document", [])]),
    ]


async def test_visual_provider_is_linked_to_invoice_and_cache_usage_is_not_billed_twice(
    process_api, monkeypatch
):
    from app.features.ingestion.ocr.vision import VisionFallback

    client, process_id, service = process_api
    service.settings = replace(
        service.settings, gemini_api_key="offline-test-key", vlm_model="incomplete-config"
    )
    service.vlm = VisionFallback(service.settings)
    sent = []

    def respond(request):
        sent.append(request)
        return httpx.Response(
            200,
            json={
                "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": VALID}]}}],
                "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 10},
            },
        )

    original_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    content = pdf_bytes("")
    options = {"ocr": "false", "vlm": "true", "jev": "false"}
    uploads = []
    for index in range(3):
        response = await client.post(
            f"/processes/{process_id}/files",
            files={"file": (f"scan-{index}.pdf", content)},
            data=options if index < 2 else {**options, "verify_fields": "supplier_tax_id"},
        )
        assert response.status_code == 201, response.text
        uploads.append(response.json())
        assert response.json()["extraction"]["data"]["provenance"]["visual_model"] == (
            service.settings.gemini_model
        )
    assert len(sent) == 1
    assert uploads[1]["extraction"]["cache_hit"] is True
    assert uploads[2]["extraction"]["cache_hit"] is False

    def flatten(nodes):
        return [row for node in nodes for row in [node, *flatten(node["children"])]]

    for index, upload in enumerate(uploads):
        journey = (await client.get(f"/instances/{upload['instance_id']}/trace")).json()
        nodes = flatten(journey["spans"])
        extraction = next(node for node in nodes if node["step"] == "extraction")
        assert extraction["data"]["extraction_id"] == upload["extraction"]["id"]
        providers = [node for node in nodes if node["step"] == "provider_call"]
        if index == 1:
            assert providers == []
            assert extraction["data"]["cached_from_extraction_id"] == uploads[0]["extraction"]["id"]
            continue
        [provider] = providers
        assert provider["data"]["outcome"] == ("success" if index == 0 else "replay")
        assert provider["data"]["network_attempted"] is (index == 0)
        assert provider["process_id"] == process_id
        assert provider["parent_id"] == next(n["span_id"] for n in nodes if n["step"] == "vision")

    metrics = (await client.get(f"/processes/{process_id}/metrics")).json()["providers"]
    assert len(metrics) == 1
    assert metrics[0]["attempts"] == 2
    assert metrics[0]["network_requests"] == metrics[0]["replays"] == 1
    assert metrics[0]["input_tokens"] == 20 and metrics[0]["output_tokens"] == 10
