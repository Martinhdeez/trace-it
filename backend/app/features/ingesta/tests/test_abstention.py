import io

import pytest
from fastapi.testclient import TestClient

from app.features.ingesta.application import create_app
from app.features.ingesta.pdf.invoice import parse_invoice
from app.features.ingesta.schemas import ExtractionResult, ExtractOptions
from app.features.ingesta.service import ExtractionService

from .conftest import VALID, NoOCR, NoVLM, lines, pdf_bytes


def test_legacy_results_require_reextraction_instead_of_defaulting_to_safe():
    result = ExtractionResult.model_validate(
        {
            "id": "old-id",
            "file_id": "old.pdf",
            "sha256": "old-hash",
            "kind": "invoice",
            "status": "COMPLETE",
            "pipeline_version": "invoice-v1.7.1+xlsx-v1.3",
        }
    )
    assert result.review.required and result.status == "NEEDS_REVIEW"
    assert result.review.reasons == ["LEGACY_RESULT_REEXTRACT"]


@pytest.mark.parametrize(
    "text,field",
    [
        ("NIF: B9623341[ILLEGIBLE]", "supplier_tax_id"),
        ("IBAN: ES18 0081 5290 6700 0123 4567?", "payment_iban"),
        ("Factura: F26-123?", "invoice_number"),
        ("TOTAL: 100,00? EUR", "gross_amount"),
    ],
)
def test_partial_or_uncertain_text_is_preserved_without_usable_value(text, field):
    fields, warnings = parse_invoice(lines(text, "vlm"))
    assert fields[field].value is None
    assert fields[field].status == "UNVERIFIED"
    assert any(c.raw == text and c.error == "UNREADABLE_TEXT" for c in fields[field].candidates)
    assert any(w["code"] == "UNREADABLE_FIELD" and w["field"] == field for w in warnings)


def test_high_confidence_without_corroboration_is_still_only_a_candidate(settings):
    class OCR(NoOCR):
        def recognize(self, *args):
            return lines("NIF: B96233419", "ocr", 0.99)

    service = ExtractionService(settings, OCR(), NoVLM())
    with TestClient(create_app(settings, service)) as client:
        result = client.post("/v1/extractions", files={"file": ("scan.pdf", pdf_bytes(""))}).json()
    field = result["fields"]["supplier_tax_id"]
    assert field["value"] is None and field["candidates"][0]["value"] == "B96233419"
    assert result["status"] == "NEEDS_REVIEW"
    assert result["review"]["required"] is True
    assert result["review"]["action"] == "HUMAN_REVIEW"
    assert "supplier_tax_id" in result["review"]["fields"]


def test_low_confidence_agreement_does_not_validate_ocr(settings):
    class OCR(NoOCR):
        def recognize(self, *args):
            return lines(VALID, "ocr", 0.99)

        def verify(self, *args):
            return lines(VALID, "ocr", 0.50)

    service = ExtractionService(settings, OCR(), NoVLM())
    result = service.extract(
        service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf"), ExtractOptions()
    )
    assert result.fields["payment_iban"].value is None
    assert result.review.required


def test_unlocalized_illegible_region_blocks_an_otherwise_complete_document(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    document = pdf_bytes(VALID + "\n[ILLEGIBLE]")
    result = service.extract(service.ingest(io.BytesIO(document), "invoice.pdf"), ExtractOptions())
    assert result.review.required
    assert "UNREADABLE_REGION" in result.review.reasons


def test_visual_disagreement_is_preserved_without_selecting_a_plausible_value(settings):
    class VLM:
        def transcribe(self, *args):
            return lines(VALID.replace("9517", "8517"), "vlm")

    service = ExtractionService(settings, NoOCR(), VLM())
    document = pdf_bytes(VALID.replace("Pedido:", "reference:"))
    result = service.extract(
        service.ingest(io.BytesIO(document), "invoice.pdf"), ExtractOptions(vlm=True)
    )
    field = result.fields["payment_iban"]
    assert field.status == "AMBIGUOUS" and field.value is None
    assert {c.value for c in field.candidates} == {
        "ES4414650100951704302211",
        "ES4414650100851704302211",
    }
    assert result.fields["purchase_order_ref"].value is None
    assert result.fields["purchase_order_ref"].candidates[0].value == "PO-2026-0703"
    assert result.review.action == "HUMAN_REVIEW"
