import io

import pytest
from fastapi.testclient import TestClient

from app.features.ingestion.application import create_app
from app.features.ingestion.pdf.invoice import parse_invoice
from app.features.ingestion.schemas import ExtractionResult, ExtractOptions
from app.features.ingestion.service import ExtractionService

from .conftest import VALID, NoOCR, NoVLM, lines, pdf_bytes


def test_legacy_workflow_fields_are_not_returned_by_the_extraction_api():
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
    assert "status" not in result.model_dump()
    assert "review" not in result.model_dump()


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


def test_single_reader_value_is_returned_with_its_provenance(settings):
    class OCR(NoOCR):
        def recognize(self, *args):
            return lines("NIF: B96233419", "ocr", 0.99)

    service = ExtractionService(settings, OCR(), NoVLM())
    with TestClient(create_app(settings, service)) as client:
        result = client.post("/v1/extractions", files={"file": ("scan.pdf", pdf_bytes(""))}).json()
    field = result["fields"]["supplier_tax_id"]
    assert field["value"] == "B96233419"
    assert field["selected_by"] == "primary"
    assert field["agreeing_readers"] == ["primary"]
    assert "status" not in result and "review" not in result
    assert result["fields"]["payment_iban"]["value"] is None


def test_low_confidence_is_preserved_as_metadata(settings):
    class OCR(NoOCR):
        def recognize(self, *args):
            return lines(VALID, "ocr", 0.99)

        def verify(self, *args):
            return lines(VALID, "ocr", 0.50)

    service = ExtractionService(settings, OCR(), NoVLM())
    result = service.extract(
        service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf"), ExtractOptions()
    )
    assert result.fields["payment_iban"].value == "ES4414650100951704302211"
    assert min(c.evidence.confidence for c in result.fields["payment_iban"].candidates) == 0.5


def test_unlocalized_illegibility_does_not_hide_readable_fields(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    document = pdf_bytes(VALID + "\n[ILLEGIBLE]")
    result = service.extract(service.ingest(io.BytesIO(document), "invoice.pdf"), ExtractOptions())
    assert result.fields["invoice_number"].value == "F26-1234"
    assert any(w["code"] == "UNREADABLE_REGION" for w in result.warnings)


def test_visual_disagreement_keeps_alternatives_and_returns_a_reading(settings):
    class VLM:
        def transcribe(self, *args):
            return lines(VALID.replace("9517", "8517"), "vlm")

    service = ExtractionService(settings, NoOCR(), VLM())
    document = pdf_bytes(VALID.replace("Pedido:", "reference:"))
    result = service.extract(
        service.ingest(io.BytesIO(document), "invoice.pdf"), ExtractOptions(vlm=True)
    )
    field = result.fields["payment_iban"]
    assert field.value == "ES4414650100951704302211"
    assert field.selected_by == "native"
    assert {c.value for c in field.candidates} == {
        "ES4414650100951704302211",
        "ES4414650100851704302211",
    }
    assert result.fields["purchase_order_ref"].value == "PO-2026-0703"
    assert result.fields["purchase_order_ref"].candidates[0].value == "PO-2026-0703"
    assert "review" not in result.model_dump()
