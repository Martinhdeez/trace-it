import hashlib
import json
from collections import Counter

import pytest

from app.core import events
from app.features.ingestion.pdf.extractor import extract_pdf
from app.features.ingestion.pdf.invoice import parse_invoice
from app.features.ingestion.schemas import INVOICE_FIELDS, ExtractOptions
from app.features.ingestion.tests.conftest import MATERIAL, VALID, NoOCR, NoVLM, lines, pdf_bytes


def test_deterministic_no_provider_calls(settings):
    fields, _, warnings, _, metrics = extract_pdf(
        pdf_bytes(VALID), ExtractOptions(vlm=True), settings, NoOCR(), NoVLM()
    )
    assert all(fields[k].status == "OBSERVED" for k in INVOICE_FIELDS)
    assert fields["supplier_tax_id"].value == "B98120774"
    assert metrics["ocr_calls"] == metrics["vlm_calls"] == 0
    assert not warnings


def test_preserve_wrong_arithmetic_dont_call_models(settings):
    fields, _, warnings, _, metrics = extract_pdf(
        pdf_bytes(VALID.replace("312,90", "300,00")),
        ExtractOptions(vlm=True),
        settings,
        NoOCR(),
        NoVLM(),
    )
    assert fields["vat_amount"].value == "300.00"
    assert {w["code"] for w in warnings} >= {"VAT_MISMATCH", "TOTAL_MISMATCH"}
    assert metrics["ocr_calls"] == metrics["vlm_calls"] == 0


def test_mixed_pdf_processes_scanned_page_after_complete_native(settings):
    import pymupdf

    class OCR(NoOCR):
        def recognize(self, *args):
            return lines("NIF: B12345678", "ocr", 0.99)

    with pymupdf.open(stream=pdf_bytes(VALID), filetype="pdf") as doc:
        doc.new_page()
        fields, _, _, pages, metrics = extract_pdf(
            doc.tobytes(), ExtractOptions(), settings, OCR(), NoVLM()
        )
    assert metrics["ocr_calls"] == 1
    assert fields["supplier_tax_id"].status == "AMBIGUOUS"
    assert pages[0]["method"] == "native" and pages[1]["method"] == "ocr"


@pytest.mark.integration
@pytest.mark.skipif(not MATERIAL.exists(), reason="Initialize official submodule")
def test_all_native_invoices(settings):
    from app.features.ingestion.pdf.native import native_pages

    count, invalid, missing_currency = 0, Counter(), 0
    for path in (MATERIAL / "facturas").glob("*.pdf"):
        pages = native_pages(path.read_bytes(), settings)
        text_lines = [line for page in pages for line in page["lines"]]
        if not text_lines:
            continue
        count += 1
        fields, _ = parse_invoice(text_lines)
        for key in INVOICE_FIELDS:
            if key == "currency" and fields[key].status == "MISSING":
                missing_currency += 1
                continue
            assert fields[key].status in {"OBSERVED", "INVALID"}, (path.name, key, fields[key])
            if fields[key].status == "INVALID":
                invalid[key] += 1
    assert count == 471
    assert invalid == {"issued_on": 3}
    assert missing_currency == 175  # No explicit currency in monetary fields (see currency audit).


@pytest.mark.integration
@pytest.mark.skipif(not MATERIAL.exists(), reason="Initialize official submodule")
def test_native_corpus_preserves_field_values_abstentions_and_candidates(settings):
    """Pin the pre-layout reader's evidence on the real corpus, not just non-empty fields.

    Captured from dev 7fccfa8 before the layout adaptation. Intentional future changes
    require the comparison tool and an explicit baseline update; this is not a claim
    that every original candidate is correct. Existing abstentions must stay abstentions.
    Geometry has separate tests and is excluded from this platform-independent digest.
    """
    from app.features.ingestion.pdf.native import native_pages

    readings = {}
    for path in sorted((MATERIAL / "facturas").glob("*.pdf")):
        pages = native_pages(path.read_bytes(), settings)
        fields, _ = parse_invoice([line for page in pages for line in page["lines"]])
        readings[path.name] = {
            name: {
                "value": field.value,
                "status": field.status,
                "candidates": [(c.raw, c.value, c.error) for c in field.candidates],
            }
            for name, field in fields.items()
        }
    assert len(readings) == 500
    digest = hashlib.sha256(json.dumps(readings, sort_keys=True, ensure_ascii=True).encode())
    assert digest.hexdigest() == "19fdcbae568f62313778721b10821364312bd592e3c334c6250cd8c46d96b3c1"


class BrokenOCR:
    def signature(self):
        return {"fake": True}

    def recognize(self, *args):
        raise RuntimeError("OCR weights missing")


def test_an_ocr_failure_is_an_error_span_and_a_warning(settings, monkeypatch):
    written = []
    monkeypatch.setattr(events, "_write", written.extend)
    with events.span("upload"):
        _, _, warnings, _, metrics = extract_pdf(
            pdf_bytes(""), ExtractOptions(vlm=False, jev=False), settings, BrokenOCR(), NoVLM()
        )
    assert {"code": "OCR_ERROR", "stage": "primary"}.items() <= warnings[0].items()
    [ocr] = [r for r in written if r["step"] == "ocr"]
    assert ocr["status"] == "error" and ocr["data"]["error"] == "RuntimeError: OCR weights missing"
    assert ocr["data"]["reader"] == "primary" and metrics["ocr_calls"] == 1
