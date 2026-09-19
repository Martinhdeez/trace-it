"""Quality gates for native layout; real PDF geometry, no OCR weights or network."""

import io
from dataclasses import replace

import pymupdf
import pytest

from app.features.ingestion.extraction_plan import ExtractionField, ExtractionPlan
from app.features.ingestion.pdf.layout import structured_text
from app.features.ingestion.pdf.locations import locate_document
from app.features.ingestion.pdf.native import native_pages
from app.features.ingestion.pdf.schema import extract_schema_pdf
from app.features.ingestion.schema_fields import SchemaFieldReader
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService

from .conftest import VALID, NoOCR, NoVLM, lines, pdf_bytes


def columns_pdf(rotation=0, heading=False):
    with pymupdf.open() as doc:
        page = doc.new_page()
        if heading:
            page.insert_text((40, 40), "Profile spanning both columns " * 3, fontsize=9)
        for column, x in enumerate((40, 320)):
            for row in range(5):
                page.insert_text(
                    (x, 85 + 18 * row),
                    f"Column {column} row {row} has original prose words.",
                    fontsize=9,
                )
        if heading:
            page.insert_text((40, 220), "Footer spanning both columns " * 3, fontsize=9)
        page.set_rotation(rotation)
        return doc.tobytes()


def table_pdf(rows, *, rotation=0, offset=False, side_note=False, merged=False):
    with pymupdf.open() as doc:
        page = doc.new_page()
        width, height = 120, 28
        x0, y0 = 60, 90
        for row in range(len(rows) + 1):
            page.draw_line((x0, y0 + height * row), (x0 + width * len(rows[0]), y0 + height * row))
        for column in range(len(rows[0]) + 1):
            start = y0 + height if merged and column == 1 else y0
            page.draw_line(
                (x0 + width * column, start), (x0 + width * column, y0 + height * len(rows))
            )
        for row, cells in enumerate(rows):
            for column, text in enumerate(cells):
                if text:
                    page.insert_text(
                        (x0 + 5 + width * column, y0 + 17 + height * row), text, fontsize=9
                    )
        if side_note:
            page.insert_text((445, 107), "SIDEBAR kept intact", fontsize=8)
        page.insert_text((60, 65), "Original table follows", fontsize=9)
        page.insert_text((60, y0 + height * len(rows) + 30), "Original footer", fontsize=9)
        if offset:
            page.set_cropbox(pymupdf.Rect(20, 20, 575, 800))
        page.set_rotation(rotation)
        return doc.tobytes()


def read(content, settings):
    return native_pages(content, settings)[0]["lines"]


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("heading", [False, True])
def test_short_columns_keep_paragraphs_and_every_original_line(settings, rotation, heading):
    result = read(columns_pdf(rotation, heading), settings)
    body = [line for line in result if line.text.startswith("Column")]
    assert [line.text.split()[:4] for line in body] == [
        ["Column", str(column), "row", str(row)] for column in range(2) for row in range(5)
    ]
    assert len({line.id for line in result}) == len(result) == (12 if heading else 10)
    if heading:
        assert result[0].text.startswith("Profile")
        assert result[-1].text.startswith("Footer")


def test_sparse_form_is_not_read_as_columns(settings):
    with pymupdf.open() as doc:
        page = doc.new_page()
        for row in range(5):
            page.insert_text((40, 60 + row * 20), f"Label {row}:")
            page.insert_text((320, 60 + row * 20), f"Value {row}")
        result = read(doc.tobytes(), settings)
    assert [line.text for line in result] == [
        text for row in range(5) for text in (f"Label {row}:", f"Value {row}")
    ]


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("offset", [False, True])
def test_table_keeps_columns_empty_cells_side_text_and_quotes(settings, rotation, offset):
    content = table_pdf(
        [["Region", "2024", "2025"], ["North", "1204", ""], ["South", "890", "774"]],
        rotation=rotation,
        offset=offset,
        side_note=True,
    )
    result = read(content, settings)
    text = structured_text(result)
    assert "| North | 1204 |  |" in text
    assert "| South | 890 | 774 |" in text
    assert text.count("774") == 1
    assert "SIDEBAR kept intact" in text
    assert text.index("Original table") < text.index("| Region") < text.index("Original footer")
    value = next(line for line in result if line.text == "774")
    assert (value.table.row, value.table.column) == (2, 2)
    assert value.raw == value.text and value.method == "native"


def test_table_failure_preserves_text_and_warns(settings, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("Optional table detection failed")

    monkeypatch.setattr(pymupdf.Page, "find_tables", fail)
    page = native_pages(table_pdf([["Expiry:", "21/04/2027"], ["Holder:", "Ana"]]), settings)[0]
    assert "21/04/2027" in [line.text for line in page["lines"]]
    assert all(line.table is None for line in page["lines"])
    assert page["warnings"] == ["NATIVE_TABLE_UNAVAILABLE"]


def test_merged_cells_remain_original_lines(settings):
    content = table_pdf([["Combined title", ""], ["Holder:", "Ana"]], merged=True)
    result = read(content, settings)
    assert all(line.table is None for line in result)
    assert "Combined title" in structured_text(result)
    assert "Ana" in structured_text(result)


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_local_table_field_retains_exact_value_location_and_cache(settings, rotation):
    content = table_pdf(
        [["Expiry:", "21/04/2027"], ["Holder:", "Ana Ruiz"]], rotation=rotation, offset=True
    )
    service = ExtractionService(settings, NoOCR(), NoVLM())
    item = service.ingest(io.BytesIO(content), "certificate.pdf")
    plan = ExtractionPlan(
        process_id=1,
        fields=[
            ExtractionField(name="expiry", type="date"),
            ExtractionField(name="holder", type="text"),
        ],
    )
    options = ExtractOptions(ocr=False, vlm=False)
    result = service.extract_schema(item, options, plan)
    assert result.fields["expiry"].value == "2027-04-21"
    assert result.fields["holder"].value == "Ana Ruiz"
    assert result.metrics["ocr_calls"] == result.metrics["vlm_calls"] == 0
    located = locate_document(content, result).model_dump()
    candidate = located["fields"]["expiry"][0]
    assert candidate["precision"] == "text"
    assert candidate["raw"] == "21/04/2027"
    assert all(0 <= coordinate <= 1 for box in candidate["boxes"] for coordinate in box)
    with pymupdf.open(stream=content, filetype="pdf") as document:
        page = document[0]
        box = page.search_for(candidate["raw"])[0] * page.rotation_matrix
        expected = [
            box.x0 / page.rect.width,
            box.y0 / page.rect.height,
            box.x1 / page.rect.width,
            box.y1 / page.rect.height,
        ]
    assert candidate["boxes"][0] == pytest.approx(expected, abs=0.002)
    cached = service.extract_schema(item, options, plan)
    assert cached.cache_hit
    assert cached.fields == result.fields
    assert cached.data["lines"] == result.data["lines"]


def test_header_without_delimiter_does_not_become_a_key_value_fact(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    item = service.ingest(
        io.BytesIO(table_pdf([["Region", "2025"], ["North", "1204"]])), "regions.pdf"
    )
    plan = ExtractionPlan(process_id=1, fields=[ExtractionField(name="region", type="text")])
    result = service.extract_schema(item, ExtractOptions(ocr=False, vlm=False), plan)
    assert result.fields["region"].value is None


def test_semantic_reader_receives_cells_but_returns_original_value_quote(settings, monkeypatch):
    settings = replace(settings, vlm_url="https://example.invalid/v1", vlm_model="test")
    result = read(table_pdf([["Region", "2024", "2025"], ["South", "890", "774"]]), settings)
    value = next(line for line in result if line.text == "774")

    def select(self, transcript, fields):
        entry = next(item for item in transcript if item["line_id"] == value.id)
        assert entry["table"]["column"] == 2
        assert entry["table"]["row"] == 1
        return {"south_2025": {"line_id": value.id, "quote": "774"}}

    monkeypatch.setattr(SchemaFieldReader, "_select", select)
    readings, _ = SchemaFieldReader(settings).read(
        result,
        [ExtractionField(name="south_2025", type="integer", description="South revenue in 2025")],
    )
    assert readings["south_2025"].value == "774"
    assert readings["south_2025"].candidates[0].evidence.locator == value.id


def test_spacing_warning_routes_missing_fields_to_ocr_without_rewriting_native(settings):
    broken = "Thisparagraphhaslostallofitswordspacing\nAnotherparagraphwithoutanywordspacing"
    content = pdf_bytes(broken)
    page = native_pages(content, settings)[0]
    assert page["suspect_spacing"]
    assert [line.raw for line in page["lines"]] == broken.splitlines()

    class OCR(NoOCR):
        def recognize(self, *args):
            return lines("Holder: Ana Ruiz", method="ocr", confidence=0.99)

    fields = [ExtractionField(name="holder", type="text")]
    readings, _, warnings, reports, metrics = extract_schema_pdf(
        content, ExtractOptions(vlm=False), settings, OCR(), NoVLM(), None, fields
    )
    assert readings["holder"].value == "Ana Ruiz"
    assert metrics["ocr_calls"] == 1 and reports[0]["ocr_needed"]
    assert any(warning["code"] == "NATIVE_SUSPECT_SPACING" for warning in warnings)


def test_healthy_identifiers_do_not_trigger_spacing_repair(settings):
    page = native_pages(pdf_bytes(VALID + "\nhttps://example.com/" + "a" * 70), settings)[0]
    assert not page["suspect_spacing"]


def test_unspaced_scripts_are_not_diagnosed_as_broken_words():
    from app.features.ingestion.pdf.layout import suspect_spacing

    assert not suspect_spacing(lines(("中文" * 25 + "\n") * 3))


def test_spacing_in_a_footnote_does_not_trigger_ocr_on_complete_fields(settings):
    from app.features.ingestion.pdf.extractor import extract_pdf

    content = pdf_bytes(
        VALID + "\nThisparagraphhaslostallofitswordspacing\nAnotherparagraphwithoutanywordspacing"
    )
    _, _, warnings, _, metrics = extract_pdf(
        content, ExtractOptions(vlm=False, jev=False), settings, NoOCR(), NoVLM()
    )
    assert metrics["ocr_calls"] == 0
    assert any(w["code"] == "NATIVE_SUSPECT_SPACING" for w in warnings)


def test_new_layout_code_invalidates_results_not_historical_evidence(settings, monkeypatch):
    from app.features.ingestion import service as module

    service = ExtractionService(settings, NoOCR(), NoVLM())
    item = {"kind": "invoice", "sha256": "same-bytes"}
    before = service.cache_key(item, ExtractOptions())
    original = module.file_identity
    monkeypatch.setattr(
        module,
        "file_identity",
        lambda path: "changed-layout" if path.name == "layout.py" else original(path),
    )
    assert service.cache_key(item, ExtractOptions()) != before
