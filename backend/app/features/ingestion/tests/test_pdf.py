from collections import Counter

import pytest

from app.features.ingestion.pdf.extractor import extract_pdf
from app.features.ingestion.pdf.invoice import parse_invoice
from app.features.ingestion.schemas import REQUIRED_INVOICE_FIELDS, ExtractOptions
from app.features.ingestion.tests.conftest import MATERIAL, VALID, NoOCR, NoVLM, lines, pdf_bytes


def test_deterministic_no_provider_calls(settings):
    fields, _, warnings, _, metrics = extract_pdf(
        pdf_bytes(VALID), ExtractOptions(vlm=True), settings, NoOCR(), NoVLM()
    )
    assert all(fields[k].status == "OBSERVED" for k in REQUIRED_INVOICE_FIELDS)
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
        for key in REQUIRED_INVOICE_FIELDS:
            if key == "currency" and fields[key].status == "MISSING":
                missing_currency += 1
                continue
            assert fields[key].status in {"OBSERVED", "INVALID"}, (path.name, key, fields[key])
            if fields[key].status == "INVALID":
                invalid[key] += 1
    assert count == 471
    assert invalid == {"issued_on": 3}
    assert missing_currency == 175  # No explicit currency in monetary fields (see currency audit).
