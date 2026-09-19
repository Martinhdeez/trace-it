"""Bounded concurrency must preserve evidence, tracing, and replay semantics."""

import io
import json
import threading
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest

from app.core import events
from app.features.ingestion.cache import reader_usage
from app.features.ingestion.ocr import budget, journal
from app.features.ingestion.ocr.errors import ProviderUnavailable
from app.features.ingestion.ocr.vision import VisionFallback
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService
from app.features.processes.execution import ExtractionSettings, ingestion_settings

from .conftest import VALID, NoOCR, lines, pdf_bytes


def test_parallel_readers_share_trace_usage_and_connection_pool(settings, monkeypatch):
    rendezvous = threading.Barrier(2)
    calls, clients, rows = [], [], []

    def respond(request):
        body = json.loads(request.content)
        calls.append(body["model"])
        rendezvous.wait(timeout=3)
        return httpx.Response(
            200, json={"choices": [{"finish_reason": "stop", "message": {"content": VALID}}]}
        )

    original = httpx.Client

    def client(**kwargs):
        instance = original(transport=httpx.MockTransport(respond), **kwargs)
        clients.append(instance)
        return instance

    monkeypatch.setattr(httpx, "Client", client)
    monkeypatch.setattr(events, "_write", rows.extend)
    configured = replace(settings, helmcode_api_key="test", vision_providers=("helmcode",))
    reader = VisionFallback(configured)
    with events.span("extraction") as parent, reader_usage() as usage:
        first = reader.transcribe_readers(b"image", 1, (595, 842))
        second = reader.transcribe_readers(b"image", 1, (595, 842))
        assert usage["vlm_requests"] == 2
        assert usage["vlm_cache_hits"] == 2
    assert first == second
    assert set(first) == {"visual:helmcode:qwen3.6", "visual:helmcode:gemma4"}
    assert sorted(calls) == ["gemma4", "qwen3.6"]
    assert len(clients) == 1
    provider_rows = [r for r in rows if r["step"] == "provider_call"]
    assert len(provider_rows) == 4
    assert all(
        r["trace_id"] == parent.trace_id and r["parent_id"] == parent.span_id for r in provider_rows
    )
    reader.http.close()
    assert clients[0].is_closed


def test_single_reader_does_not_spend_calls_on_impossible_verification(settings):
    class Visual:
        configured = True
        independent_readers = 1
        calls = 0

        def transcribe_readers(self, *args):
            self.calls += 1
            return {"visual:test:only": lines(VALID, "vlm")}

    class Judge:
        configured = True

        def select(self, *args):
            pytest.fail("A text judge cannot corroborate a sole visual candidate")

    visual = Visual()
    service = ExtractionService(settings, NoOCR(), visual, Judge())
    result = service.extract(
        service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf"), ExtractOptions(mode="api")
    )
    assert visual.calls == 1
    assert result.metrics["jev_calls_this_request"] == 0
    assert not any(f.value for f in result.fields.values())
    assert any(w["code"] == "INSUFFICIENT_VISUAL_READERS" for w in result.warnings)
    assert result.data["focused_verification"] == {}


def test_queued_expiration_can_retry_without_uncertain_delivery(settings, monkeypatch):
    slot = threading.BoundedSemaphore(1)
    slot.acquire()
    monkeypatch.setattr(journal, "_slot", lambda provider: slot)
    calls = []

    def call(mark):
        mark()
        calls.append(True)
        return {"text": "observed"}

    args = (settings.data_dir / "journal", {"request": 1}, call)
    with budget.extraction_budget(0.03), pytest.raises(ProviderUnavailable):
        journal.recorded_call(*args, provider="helmcode", model="qwen3.6")
    assert calls == []
    records = list((settings.data_dir / "journal").glob("*.json"))
    assert json.loads(records[0].read_text())["state"] == "not_started"
    slot.release()
    with budget.extraction_budget(1):
        assert journal.recorded_call(*args, provider="helmcode", model="qwen3.6") == {
            "text": "observed"
        }
    assert calls == [True]


def test_nested_budget_never_resets_the_document_deadline(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(budget, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    with budget.extraction_budget(5):
        clock[0] += 3
        with budget.extraction_budget(100):
            assert budget.remaining(60) == 2
        clock[0] += 3
        with pytest.raises(ProviderUnavailable):
            budget.remaining(60)
    assert budget.remaining(60) == 60


def test_version_pins_independent_models_without_inheriting_others(settings):
    selected = ExtractionSettings(
        primary_model_dir=str(settings.model_dir),
        verification_model_dir=str(settings.model_dir / "verify"),
        mode="api",
        vision_model="helmcode:qwen3.6",
        vision_verification_models=["gemini:gemini-test"],
    )
    config = SimpleNamespace(extraction=selected, local_endpoint=None, compatible_endpoint=None)
    bound = ingestion_settings(
        config, replace(settings, helmcode_api_key="test", gemini_api_key="test")
    )
    assert bound.visual_chain() == [("helmcode", "qwen3.6"), ("gemini", "gemini-test")]
    assert bound.extraction_timeout == 120


@pytest.mark.parametrize(
    "models", [["helmcode:qwen3.6"], ["compatible:qwen3.6"], ["helmcode:unsupported"]]
)
def test_invalid_verification_configuration_is_rejected(settings, models):
    with pytest.raises(ValueError):
        ExtractionSettings(
            primary_model_dir=str(settings.model_dir),
            verification_model_dir=str(settings.model_dir / "verify"),
            vision_model="helmcode:qwen3.6",
            vision_verification_models=models,
        )


def test_shared_identifier_region_is_rendered_and_read_once(settings, monkeypatch):
    from app.features.ingestion.pdf import focused
    from app.features.ingestion.pdf.committee import reconcile

    renders, calls = [], []
    readers = {"visual:fake:a": lines(VALID, "vlm")}
    fields = reconcile(readers, 0.9)[0]

    class Visual:
        independent_readers = 2

        def transcribe_readers(self, *args):
            calls.append(True)
            return {f"visual:fake:{name}": lines(VALID, "vlm") for name in ["a", "b"]}

    def render(*args, **kwargs):
        renders.append(True)
        return b"image"

    monkeypatch.setattr(focused, "render_region", render)
    metrics = {"vlm_calls": 0}
    result = focused.verify_identifiers(
        b"pdf",
        fields,
        readers,
        [{"number": 1, "size": (595, 842)}],
        settings,
        None,
        Visual(),
        ExtractOptions(mode="api"),
        True,
        metrics,
    )
    assert len(result) == 3
    assert all(report["value"] for report in result.values())
    assert renders == calls == [True]
    assert metrics["focused_calls"] == 2
    assert metrics["focused_region_reuses"] == 2


def test_failed_verifier_does_not_cache_incomplete_reading(settings, monkeypatch):
    from app.features.ingestion.ocr import errors

    failing = [True]
    calls = []

    def respond(request):
        model = json.loads(request.content)["model"]
        calls.append(model)
        if model == "gemma4" and failing[0]:
            return httpx.Response(503)
        return httpx.Response(
            200, json={"choices": [{"finish_reason": "stop", "message": {"content": VALID}}]}
        )

    original = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(respond), **kw)
    )
    monkeypatch.setattr(errors, "_cooldown_until", {})
    settings = replace(
        settings, ocr_mode="api", helmcode_api_key="test", vision_providers=("helmcode",)
    )
    service = ExtractionService(settings, NoOCR())
    item = service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf")
    first = service.extract(item, ExtractOptions(jev=False))
    assert not first.fields["payment_iban"].value
    assert any(w["code"] == "VLM_ERROR" for w in first.warnings)
    assert first.data["focused_verification"] == {}
    failing[0] = False
    monkeypatch.setattr(errors, "_cooldown_until", {})
    second = service.extract(item, ExtractOptions(jev=False))
    assert not second.cache_hit
    assert second.fields["payment_iban"].value == "ES4414650100951704302211"
    assert calls.count("qwen3.6") == 1
    assert calls.count("gemma4") == 2
    service.close()


def test_current_scan_labels_identify_current_pdf_bytes():
    from pathlib import Path

    from app.features.ingestion.tools.evaluate_scans import validate_references

    from .conftest import MATERIAL

    labels = json.loads(
        (Path(__file__).parent / "fixtures/scans-reviewed-current.json").read_text()
    )
    if not (MATERIAL / "facturas").is_dir():
        pytest.skip("Challenge corpus is not installed")
    validate_references(MATERIAL / "facturas", labels)


def test_stale_labels_fail_before_provider_work(tmp_path):
    from app.features.ingestion.tools.evaluate_scans import validate_references

    (tmp_path / "scan.pdf").write_bytes(b"new PDF")
    with pytest.raises(ValueError, match="visual re-review.*scan.pdf"):
        validate_references(tmp_path, [{"file_id": "scan.pdf", "sha256": "old"}])


def test_queue_expiration_returns_a_retryable_api_error(settings):
    from fastapi.testclient import TestClient

    from app.features.ingestion.application import create_app

    settings = replace(settings, ocr_mode="api", extraction_timeout=0.03)
    service = ExtractionService(settings, NoOCR())
    service.slots.acquire()
    try:
        with TestClient(create_app(settings, service)) as client:
            response = client.post(
                "/v1/extractions",
                files={"file": ("invoice.pdf", pdf_bytes(VALID), "application/pdf")},
            )
        assert response.status_code == 503
        assert response.json()["code"] == "extraction_deadline_exceeded"
    finally:
        service.slots.release()
