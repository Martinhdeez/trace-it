import io
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.features.ingestion.application import create_app
from app.features.ingestion.config import Settings
from app.features.ingestion.extraction_plan import ExtractionField, ExtractionPlan
from app.features.ingestion.pdf.committee import reconcile
from app.features.ingestion.schemas import ExtractOptions, FieldReading
from app.features.ingestion.service import ExtractionService

from .conftest import VALID, NoOCR, lines, pdf_bytes


class ForbiddenLocal:
    def signature(self):
        raise AssertionError("API mode must not inspect OCR models")

    def recognize(self, *args):
        raise AssertionError("API mode must not run local OCR")

    def verify(self, *args):
        raise AssertionError("API mode must not run local OCR")


class TwoVisuals:
    configured = True

    def __init__(self, texts):
        self.texts = texts
        self.calls = 0

    def signature(self):
        return {"chain": list(self.texts)}

    def transcribe_readers(self, *args, **kwargs):
        self.calls += 1
        return {f"visual:fake:{model}": lines(text, "vlm") for model, text in self.texts.items()}


class ForbiddenVisual:
    configured = True

    def transcribe(self, *args, **kwargs):
        raise AssertionError("Local mode must not call a visual API")

    def signature(self):
        raise AssertionError("Local mode must not inspect visual API")


class ForbiddenJudge:
    configured = True

    def select(self, *args):
        raise AssertionError("Mode must not run text judge")

    def signature(self):
        raise AssertionError("Mode must not inspect text judge")


def test_default_api_reads_without_local_models_or_an_explicit_request_mode(settings, monkeypatch):
    monkeypatch.delenv("TRACEPAY_OCR_MODE", raising=False)
    configured = replace(settings, ocr_mode=Settings().ocr_mode)
    service = ExtractionService(
        configured, ForbiddenLocal(), TwoVisuals({"a": VALID, "b": VALID}), ForbiddenJudge()
    )
    result = service.extract(
        service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf"), ExtractOptions(jev=False)
    )
    assert result.data["provenance"]["options"]["mode"] == "api"
    assert result.metrics["ocr_calls"] == 0
    assert result.metrics["vlm_calls"] > 0
    assert result.fields["supplier_tax_id"].value == "B98120774"
    assert result.fields["supplier_tax_id"].verification == "verified"


@pytest.mark.parametrize("mode", ["local", "hybrid", "api"])
def test_explicit_server_mode_is_preserved(monkeypatch, mode):
    monkeypatch.setenv("TRACEPAY_OCR_MODE", mode)
    assert ExtractOptions().normalized(Settings()).mode == mode


def test_api_mode_never_inspects_local_models_and_two_visuals_verify(settings):
    visual = TwoVisuals({"a": VALID, "b": VALID})
    service = ExtractionService(settings, ForbiddenLocal(), visual, ForbiddenJudge())
    item = service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf")
    caller = ExtractOptions(mode="api", jev=False)
    result = service.extract(item, caller)
    assert caller.ocr is True  # normalization does not mutate the caller
    assert result.data["provenance"]["options"]["ocr"] is False
    assert result.metrics["ocr_calls"] == result.metrics["jev_calls"] == 0
    assert result.fields["supplier_tax_id"].value == "B98120774"
    assert result.fields["supplier_tax_id"].verification == "verified"
    assert result.fields["supplier_tax_id"].agreeing_readers == ["visual:fake:a", "visual:fake:b"]
    assert visual.calls >= 1


def test_api_one_visual_or_conflict_remains_unverified(settings):
    for texts in (
        {"a": VALID},
        {"a": VALID, "b": VALID.replace("B98120774", "B12345678")},
        {"a": VALID, "b": VALID.replace("B98120774", "B98[ILLEGIBLE]774")},
    ):
        service = ExtractionService(settings, ForbiddenLocal(), TwoVisuals(texts), ForbiddenJudge())
        item = service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf")
        result = service.extract(item, ExtractOptions(mode="api", jev=False))
        assert result.fields["supplier_tax_id"].value is None
        assert result.fields["supplier_tax_id"].verification != "verified"
        if len(texts) == 1:
            assert result.fields["gross_amount"].value is None
            assert result.fields["gross_amount"].proposed_value == "1802.90"


def test_local_mode_ignores_configured_remote_keys(settings):
    settings = replace(settings, gemini_api_key="test", jev_api_key="test")
    service = ExtractionService(settings, NoOCR(), ForbiddenVisual(), ForbiddenJudge())
    result = service.extract(
        service.ingest(io.BytesIO(pdf_bytes(VALID)), "native.pdf"),
        ExtractOptions(mode="local"),
    )
    assert result.fields["supplier_tax_id"].value == "B98120774"
    assert result.metrics["vlm_calls"] == result.metrics["jev_calls"] == 0


def test_mode_changes_cache_identity_without_changing_default(settings):
    service = ExtractionService(settings, NoOCR(), TwoVisuals({"a": VALID}), ForbiddenJudge())
    item = {"sha256": "same", "kind": "invoice"}
    assert ExtractOptions().normalized(settings).mode == "hybrid"
    assert service.cache_key(item, ExtractOptions(mode="local", jev=False)) != service.cache_key(
        item, ExtractOptions(mode="api", jev=False)
    )
    content = pdf_bytes(VALID)
    local = service.extract(
        service.ingest(io.BytesIO(content), "same.pdf"),
        ExtractOptions(mode="local", jev=False),
    )
    api = service.extract(
        service.ingest(io.BytesIO(content), "same.pdf"),
        ExtractOptions(mode="api", jev=False),
    )
    repeated = service.extract(
        service.ingest(io.BytesIO(content), "same.pdf"),
        ExtractOptions(mode="api", jev=False),
    )
    assert not local.cache_hit and not api.cache_hit and repeated.cache_hit


def test_http_mode_forms_batch_and_public_config(settings):
    service = ExtractionService(
        settings, ForbiddenLocal(), TwoVisuals({"a": VALID}), ForbiddenJudge()
    )
    with TestClient(create_app(settings, service)) as client:
        config = client.get("/v1/ocr/config")
        assert config.status_code == 200
        assert config.json()["mode"] == "hybrid"
        assert "api_key" not in str(config.json())
        response = client.post(
            "/v1/extractions",
            data={"mode": "api", "jev": "false"},
            files={"file": ("scan.pdf", pdf_bytes(""), "application/pdf")},
        )
        assert response.status_code == 200, response.text
        assert response.json()["data"]["provenance"]["options"]["mode"] == "api"
        batch = client.post(
            "/v1/batches",
            data={"mode": "api", "jev": "false"},
            files=[("files", ("batch.pdf", pdf_bytes(""), "application/pdf"))],
        )
        assert batch.status_code == 202, batch.text


def test_schema_api_requires_distinct_visual_readers(settings):
    plan = ExtractionPlan(process_id=1, fields=[ExtractionField(name="expiry", type="date")])
    for texts, expected in (
        ({"a": "Expiry: 21/04/2027"}, None),
        ({"a": "Expiry: 21/04/2027", "b": "Expiry: 21/04/2027"}, "2027-04-21"),
    ):
        service = ExtractionService(settings, ForbiddenLocal(), TwoVisuals(texts))
        item = service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf")
        result = service.extract_schema(item, ExtractOptions(mode="api"), plan)
        assert result.fields["expiry"].value == expected
        assert result.metrics["ocr_calls"] == 0


def test_same_model_through_two_providers_never_counts_twice(settings):
    text = "NIF: B98120774"
    readers = {
        "visual:compatible:qwen3.6": lines(text, "vlm"),
        "visual:helmcode:qwen3.6": lines(text, "vlm"),
    }
    fields, _, _ = reconcile(readers, settings.ocr_min_confidence)
    assert fields["supplier_tax_id"].value is None

    class DuplicateModelVisual(TwoVisuals):
        def transcribe_readers(self, *args, **kwargs):
            self.calls += 1
            return readers

    service = ExtractionService(
        settings, ForbiddenLocal(), DuplicateModelVisual({"same": text}), ForbiddenJudge()
    )
    result = service.extract(
        service.ingest(io.BytesIO(pdf_bytes("")), "same-model.pdf"),
        ExtractOptions(mode="api", jev=False),
    )
    assert result.fields["supplier_tax_id"].value is None
    assert result.data["provenance"]["visual_model"] is None
    assert len(result.data["provenance"]["visual_models"]) == 2


def test_provenance_records_fallback_without_useless_text_judgment(settings):
    class Judge:
        configured = True

        def signature(self):
            return {"chain": ["jev", "helmcode-text"]}

        def select(self, readers, pending):
            return {"model": "helmcode-text", "answers": {}}

    visual = TwoVisuals({"fallback": VALID})
    service = ExtractionService(settings, ForbiddenLocal(), visual, Judge())
    result = service.extract(
        service.ingest(io.BytesIO(pdf_bytes("")), "fallback.pdf"),
        ExtractOptions(mode="api"),
    )
    provenance = result.data["provenance"]
    assert provenance["visual_model"] == "fallback"
    assert provenance["visual_models"] == [{"provider": "fake", "model": "fallback"}]
    assert provenance["text_judge_model"] is None
    assert result.metrics["jev_calls_this_request"] == 0


def test_api_schema_can_map_an_exact_quote_from_native_narrative(settings):
    class QuoteMapper:
        configured = True
        calls = 0

        def read(self, transcript, fields):
            self.calls += 1
            assert [field.name for field in fields] == ["expiry"]
            quote = "21/04/2027"
            assert any(quote in line.text and line.method == "native" for line in transcript)
            return {"expiry": FieldReading(value="2027-04-21", verification="verified")}, []

    mapper = QuoteMapper()
    service = ExtractionService(
        settings, ForbiddenLocal(), TwoVisuals({"a": ""}), field_reader=mapper
    )
    item = service.ingest(
        io.BytesIO(pdf_bytes("The certificate remains valid until 21/04/2027 under policy terms.")),
        "certificate.pdf",
    )
    plan = ExtractionPlan(process_id=1, fields=[ExtractionField(name="expiry", type="date")])
    result = service.extract_schema(item, ExtractOptions(mode="api"), plan)
    assert result.fields["expiry"].value == "2027-04-21"
    assert result.metrics["ocr_calls"] == result.metrics["vlm_calls"] == 0
    assert mapper.calls == 1
