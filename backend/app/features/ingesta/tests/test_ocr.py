from dataclasses import replace
from pathlib import Path

import pytest

from app.features.ingesta.pdf.extractor import extract_pdf
from app.features.ingesta.schemas import REQUIRED_INVOICE_FIELDS, ExtractOptions
from app.features.ingesta.tests.conftest import MATERIAL, VALID, NoOCR, NoVLM, lines, pdf_bytes


@pytest.mark.parametrize("variant", ["agree", "disagree", "missing", "failure"])
def test_ocr_verification_controls_false_completeness(settings, variant):
    class OCR(NoOCR):
        calls = 0

        def recognize(self, *args):
            return lines(VALID, "ocr", 0.99)

        def verify(self, *args):
            self.calls += 1
            if variant == "failure":
                raise RuntimeError("provider unavailable")
            if variant == "missing":
                return lines(VALID.replace("IBAN:", "unreadable:"), "ocr", 0.99)
            return lines(VALID.replace("9517", "8517") if variant == "disagree" else VALID, "ocr", 0.99)

    engine = OCR()
    fields, data, warnings, _, metrics = extract_pdf(
        pdf_bytes(""), ExtractOptions(), settings, engine, NoVLM()
    )
    assert engine.calls == 1
    assert metrics["ocr_calls"] == 2 and metrics["ocr_verification_calls"] == 1
    expected = {
        "agree": "OBSERVED",
        "disagree": "AMBIGUOUS",
        "missing": "UNVERIFIED",
        "failure": "UNVERIFIED",
    }
    assert fields["payment_iban"].status == expected[variant]
    assert metrics["vlm_calls"] == 0
    if variant == "disagree":
        assert {c.value for c in fields["payment_iban"].candidates} == {
            "ES4414650100951704302211",
            "ES4414650100851704302211",
        }
    if variant == "failure":
        assert any(w["code"] == "OCR_ERROR" for w in warnings)


def test_second_ocr_is_not_called_for_already_incomplete_scan(settings):
    class OCR(NoOCR):
        def recognize(self, *args):
            return lines("NIF: B98120774", "ocr", 0.99)

        def verify(self, *args):
            raise AssertionError("Should not verify incomplete scans")

    _, _, _, _, metrics = extract_pdf(pdf_bytes(""), ExtractOptions(), settings, OCR(), NoVLM())
    assert metrics["ocr_verification_calls"] == 0


def test_ocr_success_skips_vlm(settings):
    class OCR(NoOCR):
        def recognize(self, *args):
            return lines(VALID, "ocr", 0.99)

    fields, _, _, _, metrics = extract_pdf(pdf_bytes(""), ExtractOptions(vlm=True), settings, OCR(), NoVLM())
    assert all(fields[k].status == "OBSERVED" for k in REQUIRED_INVOICE_FIELDS)
    assert metrics["ocr_calls"] == 1 and metrics["vlm_calls"] == 0


def test_vlm_proposals_remain_unverified(settings):
    class OCR(NoOCR):
        def recognize(self, *args):
            return []

    class VLM:
        def transcribe(self, *args):
            return lines(VALID, "vlm")

    fields, _, warnings, _, metrics = extract_pdf(
        pdf_bytes(""), ExtractOptions(vlm=True), settings, OCR(), VLM()
    )
    assert fields["payment_iban"].status == "UNVERIFIED"
    assert metrics["vlm_calls"] == 1


@pytest.mark.ocr
@pytest.mark.skipif(
    not (MATERIAL.parents[1] / ".models/manifest.json").exists(), reason="Download OCR weights first"
)
def test_real_local_ocr(settings):
    import pymupdf

    from app.features.ingesta.ocr.local import LocalOCR
    from app.features.ingesta.pdf.native import render

    native = pdf_bytes(VALID)
    raster = render(native, 1, settings)
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_image(page.rect, stream=raster)
        scanned = doc.tobytes()
    fields, _, warnings, _, metrics = extract_pdf(
        scanned,
        ExtractOptions(),
        settings,
        LocalOCR(replace(settings, model_dir=(MATERIAL.parents[1] / ".models"))),
        NoVLM(),
    )
    assert not any(w["code"] == "OCR_ERROR" for w in warnings)
    assert metrics["ocr_calls"] == 2 and metrics["ocr_verification_calls"] == 1
    assert fields["purchase_order_ref"].value == "PO-2026-0703"
    candidate = fields["purchase_order_ref"].candidates[0]
    assert 0 <= candidate.evidence.bbox[0] < candidate.evidence.bbox[2] <= 595


@pytest.mark.ocr
@pytest.mark.integration
@pytest.mark.skipif(
    not MATERIAL.exists() or not (MATERIAL.parents[1] / ".models/verify/manifest.json").exists(),
    reason="Requires official scans and both OCR models",
)
def test_shadow_and_vertical_stripe_regressions(settings):
    import json

    from app.features.ingesta.ocr.local import LocalOCR

    refs = {
        r["file_id"]: r
        for r in json.loads(
            (Path(__file__).parent / "fixtures/scans-reviewed.json").read_text(encoding="utf-8")
        )
    }
    engine = LocalOCR(replace(settings, model_dir=(MATERIAL.parents[1] / ".models")))
    for name, operation in (
        ("scan_025.pdf", "local_illumination_normalization"),
        ("scan_026.pdf", "vertical_background_subtraction"),
    ):
        content = (MATERIAL / "facturas" / name).read_bytes()
        fields, _, warnings, _, metrics = extract_pdf(content, ExtractOptions(), settings, engine, NoVLM())
        for key, expected in refs[name]["fields"].items():
            assert fields[key].value == expected, (name, key, fields[key])
            assert fields[key].status == "OBSERVED", (name, key, fields[key])
        assert operation in fields["supplier_tax_id"].candidates[0].evidence.preprocessing
        assert metrics["ocr_verification_calls"] == 1
        assert not any(w["code"] == "OCR_ERROR" for w in warnings)
