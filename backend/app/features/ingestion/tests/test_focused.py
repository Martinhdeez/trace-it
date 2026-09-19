import io
from dataclasses import replace

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from app.features.ingestion.application import create_app
from app.features.ingestion.ocr.bands import flatten_periodic_bands
from app.features.ingestion.pdf.committee import reconcile
from app.features.ingestion.pdf.focused import region_for, render_region, verify_identifiers
from app.features.ingestion.readings import field_readings
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService

from .conftest import VALID, NoOCR, NoVLM, lines, pdf_bytes


def verify(settings, original, primary, secondary, visual, name="purchase_order_ref"):
    original = {
        family: [
            line.model_copy(update={"id": family + ":" + line.id})
            if family in {"primary", "secondary"}
            else line
            for line in observed
        ]
        for family, observed in original.items()
    }

    class OCR:
        def recognize(self, *args):
            return lines(next(primary), "ocr", 0.99)

        def verify(self, *args):
            return lines(secondary, "ocr", 0.99)

    class Visual:
        def transcribe(self, *args):
            return lines(next(visual), "vlm")

    fields, decisions, _ = reconcile(original, 0.9)
    metrics = {"ocr_calls": 0, "vlm_calls": 0}
    reports = verify_identifiers(
        pdf_bytes(""),
        fields,
        original,
        [{"number": 1, "size": (595, 842)}],
        settings,
        OCR(),
        Visual(),
        ExtractOptions(),
        True,
        metrics,
    )
    reading = field_readings(
        fields, {"committee": {"fields": decisions}, "focused_verification": reports}
    )[name]
    return reading, reports[name], metrics


def test_scale_change_cannot_turn_a_disputed_year_into_a_verified_order(settings):
    correct, wrong = "Pedido: PO-2031-9876", "Pedido: PO-2037-9876"
    reading, report, metrics = verify(
        settings,
        {"secondary": lines(wrong, "ocr", 0.99)},
        iter([correct, wrong]),
        correct,
        iter([wrong]),
    )
    assert reading.value is None
    assert reading.verification == "ambiguous"
    assert {c.value for c in reading.candidates} == {"PO-2031-9876", "PO-2037-9876"}
    assert report["reason"] == "focused_conflict"
    assert metrics["vlm_calls"] == 1


def test_stable_local_iban_can_be_corroborated_by_final_visual_crop(settings):
    correct = "IBAN: ES9368884400123588900142"
    wrong = correct.replace("1235", "1236")
    reading, report, metrics = verify(
        settings,
        {"primary": lines(correct, "ocr", 0.99), "visual": lines(wrong, "vlm")},
        iter([correct, correct]),
        "",
        iter([wrong, correct]),
        "payment_iban",
    )
    assert reading.value == "ES9368884400123588900142"
    assert reading.selected_by == "focused_agreement"
    assert reading.agreeing_readers == ["primary", "visual"]
    assert report["reason"] == "scale_stable_local_and_visual_agreement"
    assert metrics == {"ocr_calls": 3, "vlm_calls": 2, "focused_calls": 5}
    assert all(
        c.evidence.bbox == report["bbox"]
        for c in reading.candidates
        if "focus" in c.evidence.locator
    )


def test_repeated_local_readings_and_text_proposals_are_not_independent_support(settings):
    text = "Pedido: PO-2031-9876"
    reading, report, _ = verify(
        settings, {"primary": lines(text, "ocr", 0.99)}, iter([text, text]), text, iter(["", ""])
    )
    assert reading.value is None
    assert reading.proposed_value == "PO-2031-9876"
    assert report["reason"] == "insufficient_independent_support"


def test_two_corroborated_alternatives_remain_ambiguous(settings):
    a, b = "Pedido: PO-2031-9876", "Pedido: PO-2037-9876"
    reading, _, _ = verify(
        settings, {"visual": lines(a + "\n" + b, "vlm")}, iter([a, b]), b, iter([a])
    )
    assert reading.value is None


def test_regions_never_merge_identifiers_from_different_pages():
    candidates = lines("Pedido: PO-2031-9876", "ocr", 0.99)
    candidates += [line.model_copy(update={"page": 2}) for line in candidates]
    fields, _, _ = reconcile({"primary": candidates}, 0.9)
    assert (
        region_for(
            "purchase_order_ref", fields["purchase_order_ref"], {}, {1: (595, 842), 2: (595, 842)}
        )
        is None
    )


def test_rendering_respects_pixel_budget(settings):
    png = render_region(
        pdf_bytes(VALID), 1, (0, 0, 595, 842), replace(settings, max_image_pixels=1_000_000)
    )
    with Image.open(io.BytesIO(png)) as image:
        # MuPDF rounds the two dimensions upward to integral pixels.
        assert image.width * image.height < 1_003_000


def png(array):
    stream = io.BytesIO()
    Image.fromarray(array.astype(np.uint8)).save(stream, format="PNG")
    return stream.getvalue()


def test_periodic_band_correction_reduces_measured_wave_and_ignores_clean_pages():
    y, x = np.mgrid[:600, :500]
    shift = 7 * np.sin(x / 75)
    image = 220 + 20 * np.sin(2 * np.pi * (y - shift) / 10)
    result = flatten_periodic_bands(png(image))
    assert result is not None
    corrected, metadata = result
    with Image.open(io.BytesIO(corrected)) as source:
        arr = np.array(source.convert("L"))
    assert arr[100:500].std(axis=1).mean() < image[100:500].std(axis=1).mean() / 4
    assert metadata["operation"] == "periodic_band_dewarp"
    assert flatten_periodic_bands(png(np.full((600, 500), 255))) is None
    assert flatten_periodic_bands(png(220 + 20 * np.sin(2 * np.pi * y / 10))) is None


def test_api_validates_explicit_recheck_fields_and_includes_them_in_cache(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    with TestClient(create_app(settings, service)) as client:
        content = pdf_bytes(VALID)
        good = client.post(
            "/v1/extractions",
            files={"file": ("native.pdf", content)},
            data={"verify_fields": ["purchase_order_ref"], "vlm": "false"},
        )
        assert good.status_code == 200
        assert good.json()["data"]["provenance"]["options"]["verify_fields"] == [
            "purchase_order_ref"
        ]
        bad = client.post(
            "/v1/extractions",
            files={"file": ("native.pdf", content)},
            data={"verify_fields": ["expected_order=PO-2031-9876"]},
        )
        assert bad.status_code == 422
    item = {"sha256": "abc", "kind": "invoice"}
    assert service.cache_key(item, ExtractOptions()) != service.cache_key(
        item, ExtractOptions(verify_fields=["purchase_order_ref"])
    )


def test_failed_focused_reader_preserves_evidence_and_does_not_poison_cache(settings):
    class OCR(NoOCR):
        def recognize(self, *args):
            return lines("Pedido: PO-2031-9876", "ocr", 0.99)

    class Visual:
        configured = True

        def transcribe(self, png, page, size):
            if size == (595, 842):
                return []
            raise TimeoutError("secret provider details must not reach the result")

    service = ExtractionService(settings, OCR(), Visual())
    for _ in range(2):
        item = service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf")
        result = service.extract(item, ExtractOptions())
        assert not result.cache_hit
        assert any(w["code"] == "FOCUSED_READER_ERROR" for w in result.warnings)
        assert result.fields["purchase_order_ref"].value is None
        assert result.fields["purchase_order_ref"].proposed_value == "PO-2031-9876"
        assert "secret provider details" not in result.model_dump_json()
