"""Synthetic formats exercise real parsing/rendering with scripted OCR, without provider keys."""

import io
from dataclasses import replace
from html import escape

import pymupdf
import pytest
from PIL import Image

from app.features.ingestion.documents import as_pdf, safe_html
from app.features.ingestion.extraction_plan import ExtractionField, ExtractionPlan
from app.features.ingestion.pdf.locations import locate_document, render_page
from app.features.ingestion.pdf.native import native_pages
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService

from .conftest import VALID, NoOCR, NoVLM, lines, pdf_bytes


def image_bytes(kind="png"):
    with pymupdf.open(stream=pdf_bytes(VALID), filetype="pdf") as doc:
        return doc[0].get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes(kind)


def invoice_html():
    return (
        "<!doctype html><html><body>"
        + "".join(f"<p>{escape(line)}</p>" for line in VALID.splitlines())
        + "</body></html>"
    ).encode()


class InvoiceOCR(NoOCR):
    def recognize(self, png, page, size):
        assert png.startswith(b"\x89PNG")
        assert page == 1 and min(size) > 0
        return lines(VALID, method="ocr", confidence=0.99)


@pytest.mark.parametrize("kind,extension", [("png", "PNG"), ("jpeg", "jpg"), ("jpeg", "JPEG")])
def test_images_reuse_invoice_ocr_and_preserve_original_and_cache(settings, kind, extension):
    service = ExtractionService(settings, InvoiceOCR(), NoVLM())
    content = image_bytes(kind)
    item = service.ingest(io.BytesIO(content), "invoice." + extension)
    options = ExtractOptions(mode="local", focused_verification=False)
    result = service.extract(item, options)
    assert (
        result.fields["supplier_tax_id"].value or result.fields["supplier_tax_id"].proposed_value
    ) == "B98120774"
    assert result.fields["gross_amount"].value == "1802.90"
    assert result.metrics["ocr_calls"] == 1
    assert result.metrics["native_pages"] == 0
    assert result.data["provenance"]["source_format"] == kind
    assert (service.objects / result.sha256).read_bytes() == content
    assert render_page(content, 1).startswith(b"\x89PNG")
    assert len(locate_document(content, result).pages) == 1
    repeated = service.extract(service.ingest(io.BytesIO(content), "renamed." + extension), options)
    assert repeated.cache_hit
    assert repeated.metrics["ocr_calls_this_request"] == 0


@pytest.mark.parametrize("kind", ["png", "jpeg"])
def test_images_use_configured_api_readers(settings, kind):
    class Vision:
        configured = True
        independent_readers = 2

        def transcribe_readers(self, png, page, size):
            assert png.startswith(b"\x89PNG")
            return {
                reader: lines(VALID, method="vlm")
                for reader in ("visual:one:model-a", "visual:two:model-b")
            }

    service = ExtractionService(settings, NoOCR(), Vision())
    item = service.ingest(io.BytesIO(image_bytes(kind)), "invoice." + kind)
    result = service.extract(
        item, ExtractOptions(mode="api", focused_verification=False, jev=False)
    )
    assert result.metrics["ocr_calls"] == 0
    assert result.metrics["vlm_calls"] == 2
    assert result.fields["gross_amount"].value == "1802.90"


def test_html_invoice_reads_native_text_without_ocr_or_vision(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    content = invoice_html()
    result = service.extract(
        service.ingest(io.BytesIO(content), "invoice.HTML"), ExtractOptions(vlm=True)
    )
    assert result.fields["supplier_tax_id"].value == "B98120774"
    assert result.fields["gross_amount"].value == "1802.90"
    assert result.metrics["ocr_calls"] == result.metrics["vlm_calls"] == 0
    assert result.data["provenance"]["source_format"] == "html"
    locations = locate_document(content, result)
    assert any(loc.boxes for loc in locations.fields["gross_amount"])


def test_html_table_form_values_unicode_and_short_text(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    content = (
        '<meta charset="utf-8"><table><tr><td>Holder:</td><td>Ana Muñoz</td></tr>'
        "<tr><td>Expiry:</td><td>21/04/2027</td></tr></table>"
        '<p><label>City: <input value="León"></label></p>'
    ).encode()
    plan = ExtractionPlan(
        process_id=2,
        fields=[
            ExtractionField(name="holder", type="text"),
            ExtractionField(name="expiry", type="date"),
            ExtractionField(name="city", type="text"),
        ],
    )
    item = service.ingest(io.BytesIO(content), "certificate.htm")
    result = service.extract_schema(item, ExtractOptions(vlm=False), plan)
    assert {name: field.value for name, field in result.fields.items()} == {
        "holder": "Ana Muñoz",
        "expiry": "2027-04-21",
        "city": "León",
    }
    assert result.metrics["ocr_calls"] == result.metrics["vlm_calls"] == 0
    short = service.ingest(io.BytesIO(b"<p>Holder: Ana</p>"), "short.html")
    result = service.extract_schema(short, ExtractOptions(vlm=True), plan)
    assert result.fields["holder"].value == "Ana"
    assert result.metrics["ocr_calls"] == result.metrics["vlm_calls"] == 0


def test_html_ignores_active_content_and_never_embeds_resources(settings):
    content = b"""<html><head><script>alert(1)</script></head><body>
    <p onclick="evil()">Holder: Ana</p><script>Holder: Evil</script>
    <div hidden>Holder: Hidden</div><div style="display:none">Secret</div>
    <style>@import url(http://127.0.0.1/private);</style>
    <img src="file:///etc/passwd"><iframe src="http://127.0.0.1/private">Private</iframe>
    <object data="file:///etc/passwd"></object><input type="hidden" value="Hidden">
    </body></html>"""
    sanitized = safe_html(content)
    assert all(
        value not in sanitized
        for value in ("Evil", "Hidden", "Secret", "Private", "src=", "file:", "http:", "onclick")
    )
    text = "\n".join(
        line.text for page in native_pages(content, settings) for line in page["lines"]
    )
    assert text == "Holder: Ana"


def test_image_orientation_transparency_and_pixel_limit(settings):
    image = Image.new("RGBA", (80, 40), (0, 0, 0, 0))
    output = io.BytesIO()
    image.save(output, format="PNG")
    with pymupdf.open(stream=as_pdf(output.getvalue(), settings), filetype="pdf") as doc:
        assert doc[0].get_pixmap().pixel(0, 0) == (255, 255, 255)
    exif = Image.Exif()
    exif[274] = 6
    output = io.BytesIO()
    image.convert("RGB").save(output, format="JPEG", exif=exif)
    pages = native_pages(output.getvalue(), settings)
    assert pages[0]["size"][1] > pages[0]["size"][0]
    with pytest.raises(ValueError, match="pixel"):
        as_pdf(output.getvalue(), replace(settings, max_image_pixels=100))


@pytest.mark.parametrize(
    "filename,content",
    [
        ("fake.png", b"\x89PNG\r\n\x1a\nbroken"),
        ("fake.jpg", b"\xff\xd8\xffbroken"),
        ("fake.html", b"not html"),
        ("fake.gif", b"GIF89a"),
    ],
)
def test_malformed_uploads_are_rejected(settings, filename, content):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    with pytest.raises(ValueError):
        service.ingest(io.BytesIO(content), filename)
    assert not list(service.objects.iterdir())


def test_html_limits_and_declared_encoding(settings):
    html = '<meta charset="windows-1252"><p>Holder: Muñoz</p>'.encode("cp1252")
    assert "Muñoz" in safe_html(html)
    with pytest.raises(ValueError, match="page count"):
        as_pdf(b"<p>Holder: Ana</p>" * 1000, replace(settings, max_pages=1))
    with pytest.raises(ValueError, match="structure"):
        safe_html(b"<div>" * 300)


def test_html_invoice_table_keeps_labels_next_to_values(settings):
    pairs = [
        ("Factura:", "F26-1234"),
        ("Fecha:", "21/04/2026"),
        ("NIF:", "B98120774"),
        ("IBAN:", "ES44 1465 0100 9517 0430 2211"),
        ("Pedido:", "PO-2026-0703"),
        ("Base:", "1.490,00"),
        ("IVA (21%):", "312,90"),
        ("TOTAL:", "1.802,90 EUR"),
    ]
    content = (
        "<table>"
        + "".join(f"<tr><td>{label}</td><td>{value}</td></tr>" for label, value in pairs)
        + "</table>"
    ).encode()
    service = ExtractionService(settings, NoOCR(), NoVLM())
    result = service.extract(
        service.ingest(io.BytesIO(content), "table.html"), ExtractOptions(mode="local")
    )
    assert result.fields["invoice_number"].value == "F26-1234"
    assert result.fields["issued_on"].value == "2026-04-21"
    assert result.fields["supplier_tax_id"].value == "B98120774"
    assert result.fields["payment_iban"].value == "ES4414650100951704302211"
    assert result.fields["gross_amount"].value == "1802.90"
    assert result.metrics["ocr_calls"] == result.metrics["vlm_calls"] == 0
    locations = locate_document(content, result)
    assert all(
        any(loc.boxes for loc in locations.fields[name])
        for name in (
            "invoice_number",
            "issued_on",
            "supplier_tax_id",
            "payment_iban",
            "gross_amount",
        )
    )
