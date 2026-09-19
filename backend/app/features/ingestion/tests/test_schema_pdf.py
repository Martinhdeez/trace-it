"""Process schemas change in a running service without touching invoice defaults."""

import io
import uuid

import pymupdf

from app.features.ingestion.extraction_plan import ExtractionField, ExtractionPlan
from app.features.ingestion.process_extraction import schema_symbols
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService

from .conftest import NoOCR, NoVLM, lines, pdf_bytes


def test_schema_cache_tracks_fields_but_reuses_reading_when_only_rules_change(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    item = service.ingest(
        io.BytesIO(pdf_bytes("Destination: London\nExpiry: 21/04/2027")), "case.pdf"
    )
    plan = ExtractionPlan(
        process_id=1,
        fields=[ExtractionField(name="destination", type="text")],
        rules=[{"id": 1, "hash": "old"}],
    )
    first = service.extract_schema(item, ExtractOptions(ocr=False, vlm=False), plan)
    assert first.fields["destination"].value == "London"
    assert set(first.fields) == {"destination"}
    assert not first.cache_hit
    plan.rules[0]["hash"] = "changed"
    repeat = service.extract_schema(
        {**item, "id": uuid.uuid4().hex},
        ExtractOptions(ocr=False, vlm=False),
        plan,
    )
    assert repeat.cache_hit
    assert repeat.data["extraction_plan"]["fingerprint"] == plan.fingerprint
    assert repeat.data["extraction_plan"]["rules"][0]["hash"] == "changed"
    assert service.get_result(first.id)["data"]["extraction_plan"]["rules"][0]["hash"] == "old"
    plan.fields.append(ExtractionField(name="expires_on", type="date", labels=["Expiry"]))
    updated = service.extract_schema(
        {**item, "id": uuid.uuid4().hex},
        ExtractOptions(ocr=False, vlm=False),
        plan,
    )
    assert not updated.cache_hit
    assert updated.fields["expires_on"].value == "2027-04-21"
    assert set(updated.fields) == {"destination", "expires_on"}


def test_generic_scan_receives_current_fields_and_uses_ocr_evidence(settings):
    class OCR(NoOCR):
        def recognize(self, *args):
            return lines("Employee: Ana\nHas receipt: false", method="ocr", confidence=0.99)

    service = ExtractionService(settings, OCR(), NoVLM())
    item = service.ingest(io.BytesIO(pdf_bytes("")), "travel.pdf")
    plan = ExtractionPlan(
        process_id=2,
        fields=[
            ExtractionField(name="employee", type="text"),
            ExtractionField(name="has_receipt", type="boolean"),
            ExtractionField(name="file_id", type="text", source="filename"),
            ExtractionField(name="external_status", type="text", source="none"),
            ExtractionField(name="invalid_flag", type="boolean", source="filename"),
        ],
    )
    result = service.extract_schema(item, ExtractOptions(vlm=False), plan)
    symbols = schema_symbols(result, plan.fields)
    assert symbols["employee"]["value"] == "Ana"
    assert symbols["has_receipt"]["value"] is False
    assert symbols["file_id"]["value"] == "travel.pdf"
    assert symbols["external_status"]["value"] is None
    assert symbols["invalid_flag"]["value"] is None
    assert {"code": "SCHEMA_INVALID_METADATA", "field": "invalid_flag"} in result.warnings
    assert result.metrics["ocr_calls"] == 1


def test_visual_reader_receives_dynamic_schema_but_cannot_verify_its_own_proposal(settings):
    class Vision:
        configured = True

        def transcribe(self, png, page, size, *, fields):
            assert [field["name"] for field in fields] == ["expiry"]
            return lines("Expiry: 21/04/2027", method="vlm")

    service = ExtractionService(settings, NoOCR(), Vision())
    item = service.ingest(io.BytesIO(pdf_bytes("")), "certificate.pdf")
    plan = ExtractionPlan(process_id=3, fields=[ExtractionField(name="expiry", type="date")])
    result = service.extract_schema(item, ExtractOptions(ocr=False, vlm=True), plan)
    assert result.fields["expiry"].value is None
    assert result.fields["expiry"].proposed_value == "2027-04-21"
    assert result.metrics["vlm_calls"] == 1


def test_transcript_only_schema_still_reads_scanned_pages(settings):
    class OCR(NoOCR):
        def recognize(self, *args):
            return lines("Certificate of attendance", method="ocr", confidence=0.99)

    service = ExtractionService(settings, OCR(), NoVLM())
    item = service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf")
    plan = ExtractionPlan(
        process_id=4,
        fields=[
            ExtractionField(name="free_text", type="text", source="text"),
        ],
    )
    result = service.extract_schema(item, ExtractOptions(vlm=False), plan)
    assert "Certificate of attendance" in result.fields["free_text"].value
    assert result.metrics["ocr_calls"] == 1


def test_transcript_reads_scanned_page_after_a_native_page(settings):
    class Vision:
        configured = True

        def transcribe(self, png, page, size, *, fields):
            assert page == 2 and fields == []
            return [line.model_copy(update={"page": 2}) for line in lines("Scanned annex", "vlm")]

    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((50, 50), "A native cover page with enough text to read without OCR.")
        document.new_page()
        content = document.tobytes()
    service = ExtractionService(settings, NoOCR(), Vision())
    item = service.ingest(io.BytesIO(content), "mixed.pdf")
    plan = ExtractionPlan(
        process_id=5,
        fields=[
            ExtractionField(name="free_text", type="text", source="text"),
        ],
    )
    result = service.extract_schema(item, ExtractOptions(ocr=False, vlm=True), plan)
    assert "native cover page" in result.fields["free_text"].value
    assert "Scanned annex" in result.fields["free_text"].value
    assert result.metrics["vlm_calls"] == 1


def test_visual_search_stops_after_a_proposal_without_promoting_it(settings):
    calls = []

    class Vision:
        configured = True

        def transcribe(self, png, page, size, *, fields):
            calls.append(page)
            return lines("Expiry: 21/04/2027", "vlm")

    with pymupdf.open() as document:
        document.new_page()
        document.new_page()
        content = document.tobytes()
    service = ExtractionService(settings, NoOCR(), Vision())
    item = service.ingest(io.BytesIO(content), "scan.pdf")
    plan = ExtractionPlan(process_id=6, fields=[ExtractionField(name="expiry", type="date")])
    result = service.extract_schema(item, ExtractOptions(ocr=False, vlm=True), plan)
    assert calls == [1]
    assert result.fields["expiry"].value is None
    assert result.fields["expiry"].proposed_value == "2027-04-21"
