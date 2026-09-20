from urllib.parse import parse_qs, urlsplit

from app.core.config import settings
from app.features.decisions.outcomes_file import trace_url


def test_document_link_preserves_unicode_and_reserved_characters(monkeypatch):
    monkeypatch.setattr(settings, "console_base_url", "https://demo.example/nexia/trace-it/")
    name = "factura á + #&?.pdf"
    link = urlsplit(trace_url(5, name))
    assert link.scheme == "https"
    assert link.netloc == "demo.example"
    assert link.path == "/nexia/trace-it/processes/5/review"
    assert parse_qs(link.query) == {"file": [name]}
    assert link.fragment == ""


def test_same_filename_in_different_batches_stays_process_scoped():
    assert trace_url(1, "invoice.pdf") != trace_url(5, "invoice.pdf")
