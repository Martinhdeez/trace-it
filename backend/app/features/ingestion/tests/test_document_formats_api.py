"""The process API persists, re-reads and serves all supported document formats."""

import os

import pytest

from .test_document_formats import InvoiceOCR, image_bytes, invoice_html
from .test_payment_api import load_sources
from .test_payment_api import payment_api as payment_api

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("TRACEPAY_TEST_POSTGRES") != "1", reason="Requires test PostgreSQL"
    ),
]


@pytest.mark.parametrize(
    "kind,mime", [("html", "text/html"), ("png", "image/png"), ("jpeg", "image/jpeg")]
)
async def test_upload_original_evidence_duplicate_and_reextract(payment_api, kind, mime):
    client, process_id, service, _ = payment_api
    service.ocr = InvoiceOCR()
    content = invoice_html() if kind == "html" else image_bytes(kind)
    endpoint = f"/processes/{process_id}/files"
    files = {"file": ("invoice." + kind, content, mime)}
    response = await client.post(endpoint, files=files, data={"mode": "local"})
    assert response.status_code == 201, response.text
    uploaded = response.json()
    assert uploaded["created"]
    assert uploaded["extraction"]["data"]["provenance"]["source_format"] == kind
    instance_id = uploaded["instance_id"]
    prefix = f"/instances/{instance_id}"
    original = await client.get(prefix + "/file")
    assert original.content == content
    assert original.headers["content-type"].split(";")[0] == mime
    if kind == "html":
        assert original.headers["content-disposition"].startswith("attachment;")
        assert "sandbox" in original.headers["content-security-policy"]
        assert original.headers["x-content-type-options"] == "nosniff"
        assert uploaded["symbols"]["total"]["value"] == "1802.90"
    page = await client.get(prefix + "/document/pages/1")
    assert page.status_code == 200, page.text[:100]
    assert page.content.startswith(b"\x89PNG")
    locations = await client.get(prefix + "/document/locations")
    assert locations.status_code == 200, locations.text
    assert len(locations.json()["pages"]) == 1
    duplicate = await client.post(endpoint, files=files, data={"mode": "local"})
    assert duplicate.status_code == 201, duplicate.text
    assert not duplicate.json()["created"]
    assert duplicate.json()["instance_id"] == instance_id
    reextracted = await client.post(prefix + "/extract", json={"mode": "local"})
    assert reextracted.status_code == 200, reextracted.text
    assert reextracted.json()["extraction"]["sha256"] == uploaded["file_hash"]


async def test_html_invoice_uses_existing_rules_without_ocr(payment_api):
    client, process_id, _, _ = payment_api
    assert (await load_sources(client, process_id)).status_code == 201
    uploaded = await client.post(
        f"/processes/{process_id}/files",
        files={"file": ("invoice.html", invoice_html(), "text/html")},
    )
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["extraction"]["metrics"]["ocr_calls"] == 0
    assert uploaded.json()["extraction"]["metrics"]["vlm_calls"] == 0
    run = await client.post(f"/processes/{process_id}/run")
    assert run.json() == {"decided": 1, "by_decision": {"PAGAR": 1}}, run.text


@pytest.mark.parametrize(
    "filename,content",
    [
        ("bad.jpg", b"\xff\xd8\xffbroken"),
        ("bad.png", b"\x89PNG\r\n\x1a\nbroken"),
        ("bad.html", b"not markup"),
    ],
)
async def test_invalid_documents_return_client_error(payment_api, filename, content):
    client, process_id, _, _ = payment_api
    response = await client.post(
        f"/processes/{process_id}/files", files={"file": (filename, content)}
    )
    assert response.status_code == 422, response.text
