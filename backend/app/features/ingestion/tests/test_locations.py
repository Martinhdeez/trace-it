import hashlib
import io

import pymupdf
import pytest
from PIL import Image

from app.common.exceptions import NotFoundError
from app.common.extraction import Candidate, Evidence, TextLine, TextSpan
from app.features.ingestion.pdf.locations import locate_document, render_page
from app.features.ingestion.schemas import ExtractionResult, FieldReading


def document(*texts, rotation=0):
    with pymupdf.open() as pdf:
        for text in texts:
            page = pdf.new_page(width=500, height=700)
            page.insert_text((40, 60), text, fontsize=12)
            page.set_rotation(rotation)
        return pdf.tobytes()


def result(content, raw, *, page=1, method="native", bbox=None, lines=None):
    return ExtractionResult(
        id="reading",
        file_id="document.pdf",
        sha256=hashlib.sha256(content).hexdigest(),
        kind="invoice",
        pipeline_version="test",
        fields={
            "new_rule_field": FieldReading(
                value=raw,
                candidates=[
                    Candidate(
                        raw=raw,
                        value=raw,
                        evidence=Evidence(
                            locator="source",
                            text=raw,
                            method=method,
                            page=page,
                            bbox=bbox,
                        ),
                    )
                ],
            )
        },
        data={"lines": [line.model_dump() for line in (lines or [])]},
    )


def first(locations):
    return locations.fields["new_rule_field"][0]


@pytest.mark.parametrize("value", ["A7", "A very long company name with variable width"])
@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_native_value_fits_glyphs_and_page_rotation(value, rotation):
    content = document("Holder: " + value, rotation=rotation)
    reading = result(content, value)
    before = reading.model_dump()
    location = first(locate_document(content, reading))
    assert location.precision == "text"
    with pymupdf.open(stream=content, filetype="pdf") as pdf:
        page = pdf[0]
        expected = page.search_for(value)[0] * page.rotation_matrix
        box = location.boxes[0]
        actual = pymupdf.Rect(
            box[0] * page.rect.width,
            box[1] * page.rect.height,
            box[2] * page.rect.width,
            box[3] * page.rect.height,
        )
        assert list(actual) == pytest.approx(list(expected), abs=0.01)
    assert reading.model_dump() == before


def test_multiline_value_splits_rectangles_and_uses_saved_page():
    content = document("Unrelated first page", "Address: First Street\nSecond line of address")
    location = first(
        locate_document(
            content,
            result(
                content,
                "First Street Second line of address",
                page=2,
            ),
        )
    )
    assert location.page == 2
    assert location.precision == "text"
    assert len(location.boxes) == 2
    assert location.boxes[0][1] < location.boxes[1][1]


def test_repeated_amount_uses_evidence_anchor_and_never_arbitrary_first_match():
    content = document("Net: 100.00\nTotal: 100.00")
    assert first(locate_document(content, result(content, "100.00"))).precision == "page"
    with pymupdf.open(stream=content, filetype="pdf") as pdf:
        anchor = list(pdf[0].search_for("Total: 100.00")[0])
    location = first(locate_document(content, result(content, "100.00", bbox=anchor)))
    assert location.precision == "text"
    assert len(location.boxes) == 1
    assert location.boxes[0][1] == pytest.approx(anchor[1] / 700)


def test_ocr_word_boxes_exclude_other_fields_on_same_line():
    content = document("")
    line = TextLine(
        id="source",
        page=1,
        raw="Holder: Maria Long Name Total: 100",
        text="",
        method="ocr",
        bbox=[10, 20, 400, 40],
        spans=[
            TextSpan(text="Holder:", bbox=[10, 20, 40, 40]),
            TextSpan(text="Maria", bbox=[50, 20, 80, 40]),
            TextSpan(text="Long", bbox=[85, 20, 110, 40]),
            TextSpan(text="Name", bbox=[115, 20, 150, 40]),
            TextSpan(text="Total:", bbox=[300, 20, 330, 40]),
            TextSpan(text="100", bbox=[350, 20, 400, 40]),
        ],
    )
    location = first(
        locate_document(
            content,
            result(
                content,
                "Maria Long Name",
                method="ocr",
                bbox=line.bbox,
                lines=[line],
            ),
        )
    )
    assert location.precision == "ocr"
    x0, y0, x1, y1 = location.boxes[0]
    assert 40 / 500 < x0 < 50 / 500
    assert 150 / 500 < x1 < 155 / 500
    assert 15 / 700 < y0 < 20 / 700
    assert 40 / 700 < y1 < 45 / 700


def test_legacy_scan_without_geometry_is_page_only_not_a_fake_rectangle():
    content = document("")
    location = first(
        locate_document(
            content,
            result(
                content,
                "Unknown",
                method="vlm",
                bbox=[0, 0, 500, 700],
            ),
        )
    )
    assert location.precision == "page"
    assert location.boxes == []


@pytest.mark.parametrize(
    "raw,text", [("100", "1100"), ("100", "100.00"), ("ABC", "XABCD"), ("A7", "XA7Z")]
)
def test_partial_identifier_is_not_a_precise_match(raw, text):
    content = document(text)
    location = first(locate_document(content, result(content, raw)))
    assert location.precision == "page"
    assert not location.boxes


@pytest.mark.parametrize("raw", ["524,98", "EUR"])
def test_amount_and_currency_with_spaces_omitted_by_ocr(raw):
    content = document("")
    text = "TOTAL524,98EUR"
    line = TextLine(
        id="source",
        page=1,
        raw=text,
        text=text,
        method="ocr",
        bbox=[10, 20, 10 + len(text) * 10, 30],
        spans=[
            TextSpan(text=char, bbox=[10 + i * 10, 20, 20 + i * 10, 30])
            for i, char in enumerate(text)
        ],
    )
    location = first(
        locate_document(
            content,
            result(
                content,
                raw,
                method="ocr",
                lines=[line],
                bbox=line.bbox,
            ),
        )
    )
    assert location.precision == "ocr"
    assert len(location.boxes) == 1
    # The label must never be included in the amount/currency rectangle.
    assert location.boxes[0][0] > 50 / 500


def test_new_schema_field_and_normalized_date_keep_original_quote(settings):
    from app.features.ingestion.extraction_plan import ExtractionField, ExtractionPlan
    from app.features.ingestion.schemas import ExtractOptions
    from app.features.ingestion.service import ExtractionService
    from app.features.ingestion.tests.conftest import NoOCR, NoVLM

    content = document("Holder: Ana\nExpiry: 21/04/2027")
    service = ExtractionService(settings, NoOCR(), NoVLM())
    item = service.ingest(io.BytesIO(content), "certificate.pdf")
    plan = ExtractionPlan(process_id=1, fields=[ExtractionField(name="holder", type="text")])
    service.extract_schema(item, ExtractOptions(ocr=False, vlm=False), plan)
    plan.fields.append(ExtractionField(name="new_expiry_rule", type="date", labels=["Expiry"]))
    reading = service.extract_schema(item, ExtractOptions(ocr=False, vlm=False), plan)
    assert reading.fields["new_expiry_rule"].value == "2027-04-21"
    location = locate_document(content, reading).fields["new_expiry_rule"][0]
    assert location.raw == "21/04/2027"
    assert location.precision == "text"
    assert location.boxes


def test_geometry_ocr_is_bounded_per_page_and_does_not_change_values(settings):
    content = document("")
    reading = result(content, "ABC", method="vlm", bbox=[0, 0, 500, 700])
    reading.fields["second_rule"] = reading.fields["new_rule_field"].model_copy(deep=True)

    class OCR:
        calls = 0

        def recognize(self, *args):
            self.calls += 1
            return [
                TextLine(
                    id="local",
                    page=1,
                    raw="ABC",
                    text="ABC",
                    bbox=[20, 30, 60, 45],
                    spans=[TextSpan(text="ABC", bbox=[20, 30, 60, 45])],
                )
            ]

    ocr = OCR()
    before = reading.model_dump()
    locations = locate_document(content, reading, ocr, settings)
    assert ocr.calls == 1
    assert first(locations).precision == "ocr"
    assert reading.model_dump() == before


def test_render_original_page_and_reject_out_of_bounds():
    content = document("First", "Second", rotation=90)
    with Image.open(io.BytesIO(render_page(content, 2))) as image:
        assert image.width / image.height == pytest.approx(700 / 500)
    for page in (0, -1, 3):
        with pytest.raises(NotFoundError):
            render_page(content, page)
