import io
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from fastapi.testclient import TestClient

from app.features.ingestion.application import create_app
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService

from .conftest import VALID, NoOCR, NoVLM, pdf_bytes


def test_concurrent_duplicate_uploads_extract_once(settings):
    from .conftest import lines

    class OCR(NoOCR):
        calls = 0

        def recognize(self, *args):
            self.calls += 1
            time.sleep(0.03)
            return lines(VALID, "ocr", 0.99)

    ocr = OCR()
    service = ExtractionService(settings, ocr, NoVLM())
    content = pdf_bytes("")

    def run(index):
        item = service.ingest(io.BytesIO(content), f"{index}.pdf")
        return service.extract(item, ExtractOptions())

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, range(8)))
    assert ocr.calls == 1
    assert sum(r.cache_hit for r in results) == 7
    assert len({r.file_id for r in results}) == 8


def test_provider_failure_can_retry_without_poisoned_cache(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    content = pdf_bytes("")
    for _ in range(2):
        result = service.extract(service.ingest(io.BytesIO(content), "scan.pdf"), ExtractOptions())
        assert "status" not in result.model_dump()
        assert result.cache_hit is False
        assert any(w["code"] == "OCR_ERROR" for w in result.warnings)


def test_upload_limit_cleans_temporary_files(settings):
    service = ExtractionService(replace(settings, max_file_bytes=10), NoOCR(), NoVLM())
    with TestClient(create_app(service.settings, service)) as client:
        response = client.post("/v1/extractions", files={"file": ("large.pdf", pdf_bytes(VALID))})
        assert response.status_code == 422
        assert not list(service.objects.iterdir())


def test_upload_cache_identity_and_get(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    with TestClient(create_app(settings, service)) as client:
        content = pdf_bytes(VALID)
        first = client.post(
            "/v1/extractions", files={"file": ("á.pdf", content, "application/pdf")}
        )
        assert first.status_code == 200, first.text
        data = first.json()
        assert "status" not in data and "review" not in data
        assert data["cache_hit"] is False
        second = client.post("/v1/extractions", files={"file": ("another.pdf", content)}).json()
        assert second["cache_hit"] is True
        assert second["file_id"] == "another.pdf"
        assert second["id"] != data["id"]
        assert second["data"]["provenance"]["cached_from_extraction_id"] == data["id"]
        assert second["metrics"]["ocr_calls_this_request"] == 0
        assert client.get("/v1/extractions/" + data["id"]).json()["file_id"] == "á.pdf"
        assert client.get("/v1/extractions/not-found").status_code == 404


def test_extraction_trace_links_cached_evidence_without_new_reader_calls(settings, monkeypatch):
    from app.core import events

    written = []
    monkeypatch.setattr(events, "_write", written.extend)
    service = ExtractionService(settings, NoOCR(), NoVLM())
    content = pdf_bytes(VALID)
    options = ExtractOptions(ocr=False, vlm=False, jev=False)
    first = service.extract(service.ingest(io.BytesIO(content), "invoice.pdf"), options)
    second = service.extract(service.ingest(io.BytesIO(content), "invoice.pdf"), options)
    spans = [row for row in written if row["step"] == "extraction"]
    assert [row["data"]["extraction_id"] for row in spans] == [first.id, second.id]
    replay = spans[1]["data"]
    assert replay["cache_hit"] is True
    assert replay["cached_from_extraction_id"] == first.id
    assert replay["options"] == options.normalized(settings).model_dump()
    assert replay["pipeline_version"] == second.pipeline_version
    assert replay["ocr_calls_this_request"] == replay["vlm_calls_this_request"] == 0
    assert replay["jev_calls_this_request"] == 0
    assert not any(row["step"] == "provider_call" for row in written)
    assert "cached_from_extraction_id" not in first.data["provenance"]


def test_bad_uploads(settings):
    with TestClient(create_app(settings, ExtractionService(settings, NoOCR(), NoVLM()))) as client:
        for name, content in [
            ("empty.pdf", b""),
            ("fake.pdf", b"hello"),
            ("bad.pdf", b"%PDF-broken"),
        ]:
            assert (
                client.post("/v1/extractions", files={"file": (name, content)}).status_code == 422
            )


def test_internal_error_is_not_blame_on_document(settings, monkeypatch):
    service = ExtractionService(settings, NoOCR(), NoVLM())

    def fail(*args):
        raise RuntimeError("sensitive internal details")

    monkeypatch.setattr(service, "extract", fail)
    with TestClient(create_app(settings, service)) as client:
        response = client.post("/v1/extractions", files={"file": ("valid.pdf", pdf_bytes(VALID))})
        assert response.status_code == 500
        assert "sensitive" not in response.text


def test_zip_disguised_as_xlsx_is_rejected(settings):
    import zipfile

    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("anything.txt", "not a workbook")
    with TestClient(create_app(settings, ExtractionService(settings, NoOCR(), NoVLM()))) as client:
        response = client.post("/v1/extractions", files={"file": ("bad.xlsx", stream.getvalue())})
        assert response.status_code == 422


def test_api_does_not_ask_for_currency(settings):
    with TestClient(create_app(settings, ExtractionService(settings, NoOCR(), NoVLM()))) as client:
        schema = client.get("/openapi.json").json()
        for path in ("/v1/extractions", "/v1/batches"):
            ref = schema["paths"][path]["post"]["requestBody"]["content"]["multipart/form-data"][
                "schema"
            ]["$ref"]
            assert (
                "currency"
                not in schema["components"]["schemas"][ref.rsplit("/", 1)[-1]]["properties"]
            )


def test_batch_persists_and_runs(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    with TestClient(create_app(settings, service)) as client:
        response = client.post(
            "/v1/batches",
            files=[
                ("files", ("one.pdf", pdf_bytes(VALID))),
                ("files", ("two.pdf", pdf_bytes(VALID))),
            ],
        )
        assert response.status_code == 202, response.text
        for _ in range(100):
            batch = client.get(response.json()["status_url"]).json()
            if batch["finished"]:
                break
            time.sleep(0.02)
        assert batch["counts"]["COMPLETED"] == 2
        assert batch["counts"]["FAILED"] == 0


def test_recovery_of_interrupted_job(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    item = service.ingest(io.BytesIO(pdf_bytes(VALID)), "recover.pdf")
    service.store.submit_batch("batch", [item], ExtractOptions(), 100)
    assert service.store.claim()["id"] == item["id"]
    with TestClient(create_app(settings, service)) as client:
        for _ in range(100):
            batch = client.get("/v1/batches/batch").json()
            if batch["finished"]:
                break
            time.sleep(0.02)
        assert batch["counts"]["COMPLETED"] == 1
