import io
import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from app.features.ingestion.cache import cached_read, reader_usage
from app.features.ingestion.ocr.journal import recorded_call
from app.features.ingestion.ocr.local import LocalOCR
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService

from .conftest import VALID, NoOCR, NoVLM, lines, pdf_bytes


def test_final_cache_tracks_render_limits_and_provider_prompts(settings, monkeypatch):
    item = {"sha256": "same", "kind": "invoice"}
    options = ExtractOptions()
    base = ExtractionService(settings, NoOCR(), NoVLM()).cache_key(item, options)
    for changes in ({"max_image_pixels": 1000}, {"max_pages": 1}, {"ocr_min_confidence": 0.8}):
        assert (
            ExtractionService(replace(settings, **changes), NoOCR(), NoVLM()).cache_key(
                item, options
            )
            != base
        )

    configured = replace(settings, gemini_api_key="test", jev_api_key="test")
    service = ExtractionService(configured, NoOCR())
    before = service.cache_key(item, options)
    monkeypatch.setattr("app.features.ingestion.ocr.vision.PROMPT", "Changed transcription prompt")
    assert service.cache_key(item, options) != before
    before = service.cache_key(item, options)
    monkeypatch.setattr(
        "app.features.ingestion.ocr.judge.INSTRUCTIONS", "Changed judge instructions"
    )
    assert service.cache_key(item, options) != before


def test_cache_canonicalizes_field_order_and_ignores_unused_provider_settings(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    item = {"sha256": "same", "kind": "invoice"}
    left = ExtractOptions(vlm=False, jev=False, verify_fields=["payment_iban", "supplier_tax_id"])
    right = left.model_copy(
        update={"verify_fields": ["supplier_tax_id", "payment_iban", "payment_iban"]}
    )
    assert service.cache_key(item, left) == service.cache_key(item, right)
    other = ExtractionService(
        replace(settings, gemini_model="changed", jev_model="changed"), NoOCR(), NoVLM()
    )
    assert service.cache_key(item, left) == other.cache_key(item, left)


def test_workbook_cache_ignores_ocr_but_tracks_excel_limits(settings):
    item = {"sha256": "same", "kind": "workbook"}
    service = ExtractionService(settings, NoOCR(), NoVLM())
    before = service.cache_key(item, ExtractOptions())
    changed = ExtractionService(
        replace(settings, ocr_dpi=600, gemini_model="changed"), NoOCR(), NoVLM()
    )
    assert changed.cache_key(item, ExtractOptions(ocr=False, vlm=False, jev=False)) == before
    changed = ExtractionService(replace(settings, max_excel_rows=5), NoOCR(), NoVLM())
    assert changed.cache_key(item, ExtractOptions()) != before


def test_unconfigured_visual_reader_does_not_report_a_network_request(settings):
    service = ExtractionService(settings, NoOCR())
    item = service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf")
    result = service.extract(item, ExtractOptions(ocr=False, vlm=True, jev=False))
    assert any(w["code"] == "VLM_ERROR" for w in result.warnings)
    assert result.metrics["vlm_calls"] == 1
    assert result.metrics["vlm_calls_this_request"] == 0


def test_partial_compatible_configuration_keys_the_active_gemini_fallback(settings):
    configured = replace(
        settings, vlm_url="https://unused.example", vlm_model=None, gemini_api_key="test-key"
    )
    item = {"sha256": "same", "kind": "invoice"}
    first = ExtractionService(configured, NoOCR())
    assert first.vlm.signature()["model"] == configured.gemini_model
    assert first.vlm.signature()["endpoint"] is None
    second = ExtractionService(replace(configured, gemini_model="gemini-changed"), NoOCR())
    assert first.cache_key(item, ExtractOptions()) != second.cache_key(item, ExtractOptions())


def test_models_changed_in_place_invalidate_without_manifest_edits(settings):
    model = settings.model_dir / "rec/inference.onnx"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"old-weights")
    engine = LocalOCR(settings)
    before = engine.signature()
    stat = model.stat()
    model.write_bytes(b"new-weights")
    os.utime(model, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    assert engine.signature() != before


def test_reparse_reuses_local_readings_and_preserves_result_history(settings, monkeypatch):
    # Distinct artifacts represent the two independent recognizers.
    for directory, content in (
        (settings.model_dir, "primary"),
        (settings.model_dir / "verify", "secondary"),
    ):
        directory.mkdir(parents=True)
        (directory / "manifest.json").write_text(content)
    calls = []

    def recognize(self, png, page, size, signature):
        calls.append(self.settings.model_dir)
        return lines(VALID, "ocr", 0.99)

    monkeypatch.setattr(LocalOCR, "_recognize", recognize)
    first_service = ExtractionService(settings, vlm=NoVLM())
    item = first_service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf")
    first = first_service.extract(item, ExtractOptions(vlm=False, jev=False))
    changed = ExtractionService(replace(settings, ocr_min_confidence=0.95), vlm=NoVLM())
    second = changed.extract({**item, "id": "second"}, ExtractOptions(vlm=False, jev=False))
    assert not second.cache_hit  # Field interpretation ran with the new threshold.
    assert len(calls) == 2
    assert second.metrics["ocr_calls_this_request"] == 0
    assert second.metrics["ocr_cache_hits_this_request"] == 2
    assert first.fields == second.fields
    assert (
        first_service.get_result(first.id)["data"]["provenance"]["cache_key"]
        != second.data["provenance"]["cache_key"]
    )
    third = changed.extract({**item, "id": "third"}, ExtractOptions(vlm=False, jev=False))
    assert third.cache_hit and third.metrics["ocr_cache_hits_this_request"] == 0


def test_reader_cache_concurrency_errors_and_corruption(tmp_path):
    calls = []

    def read():
        calls.append(1)
        return [{"text": "original"}]

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(
            executor.map(lambda _: cached_read(tmp_path, {"image": "same"}, read), range(8))
        )
    assert len(calls) == 1 and all(result == results[0] for result in results)
    path = next(tmp_path.glob("*.json"))
    path.write_text("[]")
    assert cached_read(tmp_path, {"image": "same"}, read) == results[0]
    assert len(calls) == 2

    def fail():
        raise RuntimeError("reader failed")

    with pytest.raises(RuntimeError):
        cached_read(tmp_path, {"image": "other"}, fail)
    assert cached_read(tmp_path, {"image": "other"}, read) == results[0]


def test_provider_metrics_separate_replay_and_uncertain_delivery(tmp_path):
    with reader_usage() as usage:
        for _ in range(2):
            assert (
                recorded_call(tmp_path, {"image": "same"}, lambda: "text", reader="vlm") == "text"
            )
    assert usage == {"vlm_journal_calls": 2, "vlm_requests": 1, "vlm_cache_hits": 1}
    path = next(tmp_path.glob("*.json"))
    record = json.loads(path.read_text())
    record["state"] = "uncertain_or_failed"
    path.write_text(json.dumps(record))
    with reader_usage() as usage, pytest.raises(RuntimeError, match="uncertain"):
        recorded_call(tmp_path, {"image": "same"}, lambda: "text", reader="vlm")
    assert usage == {"vlm_journal_calls": 1}
