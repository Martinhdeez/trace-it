"""Literal evidence and safety contracts for international and mixed invoices."""

import json
from pathlib import Path

import pymupdf
import pytest

from app.features.decisions.engine import Outcomes, decide
from app.features.ingestion.payment_verification import payment_symbols
from app.features.ingestion.pdf.extractor import extract_pdf
from app.features.ingestion.pdf.international import literal_date
from app.features.ingestion.pdf.invoice import parse_invoice
from app.features.ingestion.pdf.native import native_pages
from app.features.ingestion.readings import field_readings
from app.features.ingestion.schemas import ExtractionResult, ExtractOptions, FieldReading
from app.features.ingestion.symbols import scan, unverified

from .conftest import MATERIAL, NoOCR, NoVLM, lines


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("dos de enero de dos mil veintiséis", "2026-01-02"),
        ("the seventh of March, two thousand twenty-six", "2026-03-07"),
        ("03 Feb 2026", "2026-02-03"),
        ("dos de gener de dos mil vint-i-sis", "2026-01-02"),
        ("15 de fevereiro de 2026", "2026-02-15"),
        ("le trois janvier deux mille vingt-six", "2026-01-03"),
        ("sette agosto duemilaventisei", "2026-08-07"),
        ("am siebten März zweitausendsechsundzwanzig", "2026-03-07"),
        ("am fünfzehnten Juni zweitausendsechsundzwanzig", "2026-06-15"),
    ],
)
def test_literal_dates(raw, expected):
    assert literal_date(raw) == expected


@pytest.mark.parametrize("raw", ["next Friday", "March", "02/03", "as agreed", "_"])
def test_no_date_invention(raw):
    with pytest.raises(ValueError):
        literal_date(raw)


def test_foreign_account_and_issuer_are_complete_and_recipient_is_excluded():
    fields, _ = parse_invoice(
        lines(
            "NIF: 12.345.678/0001-95\n"
            "IBAN: BR97 0036 0305 0000 1000 9795 493C1\n"
            "Faturar a: Other customer NIF: A58231074"
        )
    )
    assert fields["supplier_tax_id"].value == "12345678/000195"
    assert fields["payment_iban"].value == "BR9700360305000010009795493C1"
    assert len(fields["payment_iban"].candidates) == 1


def test_customer_only_does_not_create_issuer():
    fields, _ = parse_invoice(lines("Faturar a: NIF: A58231074"))
    assert fields["supplier_tax_id"].value is None


@pytest.mark.parametrize("customer", ["A58231074", "B11111111", "DE912345678"])
def test_multiline_recipient_cannot_change_the_issuer(customer):
    fields, _ = parse_invoice(
        lines(
            "Tax ID: DE812345678\nBill to: Any customer\nTax ID: "
            + customer
            + "\nIBAN: DE89 3704 0044 0532 0130 00"
        )
    )
    assert fields["supplier_tax_id"].value == "DE812345678"


def test_conflicting_foreign_identifiers_are_not_resolved_by_line_order():
    for text in (
        "Tax ID: DE812345678\nTax ID: DE912345678",
        "Tax ID: DE912345678\nTax ID: DE812345678",
    ):
        fields, _ = parse_invoice(lines(text))
        assert fields["supplier_tax_id"].value is None
        assert fields["supplier_tax_id"].status == "AMBIGUOUS"


@pytest.mark.parametrize(
    "mark", ["strike", "curve", "annotation", "underline", "border", "overlay", "logo"]
)
def test_visual_amendments_distinguish_strikes_from_layout(settings, mark):
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 60), "TOTAL: 121.00 EUR", fontsize=12)
        bbox = page.search_for("TOTAL: 121.00 EUR")[0]
        middle = (bbox.y0 + bbox.y1) / 2
        if mark == "strike":
            page.draw_line((55, middle), (bbox.x1, middle))
        elif mark == "curve":
            page.draw_bezier((55, middle), (70, middle - 2), (90, middle + 2), (bbox.x1, middle))
        elif mark == "annotation":
            page.add_strikeout_annot(bbox)
        elif mark == "underline":
            page.draw_line((50, bbox.y1 + 2), (bbox.x1, bbox.y1 + 2))
        elif mark == "border":
            page.draw_rect(bbox + (-3, -3, 3, 3))
        else:
            pixmap = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 10, 10))
            pixmap.clear_with(128)
            area = bbox if mark == "overlay" else pymupdf.Rect(300, 20, 350, 50)
            page.insert_image(area, pixmap=pixmap)
        [page_data] = native_pages(doc.tobytes(), settings)
    assert bool(page_data["visual_risk"]["regions"]) == (
        mark in {"strike", "curve", "annotation", "overlay"}
    )


def test_explicit_jpy_grouping_and_actual_printed_arithmetic():
    fields, warnings = parse_invoice(
        lines("Base imponible: ¥ 773,000\nIVA (21%): ¥ 77,000\nTOTAL: ¥ 850,000 JPY")
    )
    assert fields["net_amount"].value == "773000.00"
    assert fields["vat_amount"].value == "77000.00"
    assert fields["gross_amount"].value == "850000.00"
    assert any(w["code"] == "VAT_MISMATCH" for w in warnings)


def test_mixed_unverified_field_does_not_become_a_whole_scan():
    result = ExtractionResult(
        id="x",
        file_id="x.pdf",
        sha256="x",
        kind="invoice",
        pipeline_version="test",
        metrics={"native_pages": 1},
        fields={"issued_on": FieldReading(value="2026-03-15", verification="unverified")},
    )
    symbols = payment_symbols(result, {"date"})
    assert scan(symbols) is None
    assert unverified(symbols) == ["date"]
    [verdict] = decide(
        [],
        Outcomes({"PAGAR": 1, "ESCALAR": 3}, "PAGAR", "ESCALAR", ("date",)),
        [(1, {"date": "2026-03-15"})],
        {},
        [],
        lambda *a: [],
        unverified={1: unverified(symbols)},
    )
    assert verdict.decision == "ESCALAR"
    assert verdict.reason == "UNVERIFIED_DATA: date"


@pytest.mark.integration
@pytest.mark.skipif(not (MATERIAL / "facturas_primin").is_dir(), reason="Batch 2 material required")
def test_crossed_out_amounts_never_survive_as_accepted_values(settings):
    content = (MATERIAL / "facturas_primin/e18_P001.pdf").read_bytes()
    fields, data, _, pages, _ = extract_pdf(
        content,
        ExtractOptions(mode="local", ocr=False, vlm=False, jev=False),
        settings,
        NoOCR(),
        NoVLM(),
    )
    readings = field_readings(fields, data)
    assert readings["gross_amount"].value is None
    assert readings["net_amount"].value is None
    assert readings["gross_amount"].selected_by is None
    assert readings["gross_amount"].agreeing_readers == []
    assert data["blocked_fields"]["gross_amount"] == "visible_amendment"
    assert pages[0]["visual_risk"]["regions"]


@pytest.mark.integration
@pytest.mark.skipif(not (MATERIAL / "facturas_primin").is_dir(), reason="Batch 2 material required")
def test_all_international_digital_fields(settings):
    reference = json.loads(
        (Path(__file__).parent / "fixtures/batch2-reviewed-fields.json").read_text(encoding="utf-8")
    )
    for case in reference:
        content = (MATERIAL / "facturas_primin" / case["file_id"]).read_bytes()
        fields, _ = parse_invoice(
            [line for p in native_pages(content, settings) for line in p["lines"]]
        )
        for name, expected in case["fields"].items():
            assert fields[name].value == expected, (case["file_id"], name, fields[name])


@pytest.mark.integration
@pytest.mark.skipif(not (MATERIAL / "facturas").is_dir(), reason="Original material required")
def test_no_new_visual_risk_on_original_corpus(settings):
    paths = list((MATERIAL / "facturas").glob("*.pdf"))
    assert len(paths) == 500
    for path in paths:
        for page in native_pages(path.read_bytes(), settings):
            risk = page["visual_risk"]
            assert not risk["fragmented"] and not risk["regions"], (path.name, risk)
