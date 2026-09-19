"""Schema PDF readings must carry their evidence into decision scan gates."""

import io
from types import SimpleNamespace

import pymupdf

from app.features.decisions.engine import Outcomes, decide
from app.features.ingestion.extraction_plan import ExtractionField, ExtractionPlan
from app.features.ingestion.process_extraction import schema_symbols
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService
from app.features.ingestion.symbols import flatten_symbols, scan

from .conftest import NoOCR, NoVLM, lines, pdf_bytes


class EmployeeOCR(NoOCR):
    def recognize(self, *args):
        return lines("Employee: Ana", method="ocr", confidence=0.99)


def verdict(symbols, *, required=(), reject=False):
    rules = [
        SimpleNamespace(
            id=1,
            hash="rule-hash",
            code="def evaluate(instance, sources, others): pass",
            report=None,
            decision="REJECT",
            text="Reject Ana",
        )
    ]
    outcomes = Outcomes(
        priorities={"ACCEPT": 0, "REVIEW": 1, "REJECT": 2},
        default="ACCEPT",
        escalate="REVIEW",
        required=required,
    )

    def run(_code, instances, _sources, _population):
        return [
            {"fires": reject and values["employee"] == "Ana", "reason": "EMPLOYEE_REJECTED"}
            for _, values in instances
        ]

    [decision] = decide(
        rules,
        outcomes,
        [(1, flatten_symbols(symbols))],
        {},
        [],
        run,
        {1: unconfirmed} if (unconfirmed := scan(symbols)) is not None else {},
    )
    return decision


def test_accepted_ocr_value_reaches_engine_but_required_field_needs_review(settings):
    service = ExtractionService(settings, EmployeeOCR(), NoVLM())
    item = service.ingest(io.BytesIO(pdf_bytes("")), "travel.pdf")
    field = ExtractionField(name="employee", type="text")
    result = service.extract_schema(
        item,
        ExtractOptions(vlm=False, secondary_ocr=False),
        ExtractionPlan(process_id=1, fields=[field]),
    )
    symbols = schema_symbols(result, [field])

    assert result.data["schema_fields"]["employee"]["verification"] == "extracted"
    assert symbols["employee"] == {
        "value": "Ana",
        "origin": f"scan:{result.id}:extracted",
    }
    assert scan(symbols) == ["employee"]
    required = verdict(symbols, required=("employee",))
    assert (required.decision, required.reason) == ("REVIEW", "UNVERIFIED_DATA: employee")
    assert verdict(symbols).decision == "ACCEPT"
    rejected = verdict(symbols, reject=True)
    assert (rejected.decision, rejected.reason) == ("REVIEW", "SCAN_REVIEW: EMPLOYEE_REJECTED")


def test_native_schema_value_can_be_used_directly_by_rejection_rule(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    item = service.ingest(io.BytesIO(pdf_bytes("Employee: Ana")), "travel.pdf")
    field = ExtractionField(name="employee", type="text")
    result = service.extract_schema(
        item,
        ExtractOptions(ocr=False, vlm=False),
        ExtractionPlan(process_id=2, fields=[field]),
    )
    symbols = schema_symbols(result, [field])

    assert symbols["employee"] == {"value": "Ana", "origin": f"document:{result.id}"}
    assert scan(symbols) is None
    rejected = verdict(symbols, required=("employee",), reject=True)
    assert (rejected.decision, rejected.reason) == ("REJECT", "EMPLOYEE_REJECTED")


def test_ocr_field_on_mixed_pdf_uses_its_own_evidence(settings):
    class PageOCR(EmployeeOCR):
        def recognize(self, _image, page, _size):
            return [
                line.model_copy(update={"page": page})
                for line in lines("Employee: Ana", method="ocr", confidence=0.99)
            ]

    with pymupdf.open() as document:
        cover = document.new_page()
        cover.insert_text(
            (50, 50), "This native cover page contains enough text for direct reading."
        )
        document.new_page()
        content = document.tobytes()
    service = ExtractionService(settings, PageOCR(), NoVLM())
    item = service.ingest(io.BytesIO(content), "mixed.pdf")
    field = ExtractionField(name="employee", type="text")
    result = service.extract_schema(
        item,
        ExtractOptions(vlm=False, secondary_ocr=False),
        ExtractionPlan(process_id=4, fields=[field]),
    )
    symbols = schema_symbols(result, [field])

    assert result.metrics["native_pages"] == 1
    assert symbols["employee"]["origin"] == f"scan:{result.id}:extracted"
    assert verdict(symbols, required=("employee",)).reason == "UNVERIFIED_DATA: employee"


def test_scan_metadata_stays_document_origin_and_invoice_extension_is_scanned(settings):
    service = ExtractionService(settings, EmployeeOCR(), NoVLM())
    item = service.ingest(io.BytesIO(pdf_bytes("")), "travel.pdf")
    field = ExtractionField(name="employee", type="text")
    filename = ExtractionField(name="file_id", type="text", source="filename")
    plan = ExtractionPlan(process_id=3, fields=[field, filename])
    options = ExtractOptions(vlm=False, secondary_ocr=False)
    base = service.extract(item, options)
    extended = service.extract_schema(item, options, plan, [field, filename], base)
    symbols = schema_symbols(extended, [field, filename])

    assert symbols["employee"] == {
        "value": "Ana",
        "origin": f"scan:{extended.id}:extracted",
    }
    assert symbols["file_id"] == {
        "value": "travel.pdf",
        "origin": f"document:{extended.id}",
    }
    assert scan(symbols) == ["employee"]
