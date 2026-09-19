"""Provider fallback must retain provenance and reject invented evidence."""

import io
import json
from dataclasses import replace

import httpx
import pytest

from app.features.ingestion.extraction_plan import ExtractionField
from app.features.ingestion.ocr import errors
from app.features.ingestion.ocr.errors import ProviderUnavailable
from app.features.ingestion.ocr.judge import TextJudge
from app.features.ingestion.ocr.vision import VisionFallback
from app.features.ingestion.pdf.committee import reconcile
from app.features.ingestion.schema_fields import SchemaFieldReader, read_schema_fields
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService

from .conftest import NoOCR, lines, pdf_bytes


@pytest.fixture(autouse=True)
def isolated_cooldown(monkeypatch):
    monkeypatch.setattr(errors, "_cooldown_until", {})


def mock_client(monkeypatch, respond):
    original = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs)
    )


@pytest.mark.parametrize("status", [429, 503])
def test_gemini_failure_falls_back_to_helm_image(settings, monkeypatch, status):
    requests = []

    def respond(request):
        requests.append(request.url.host)
        if request.url.host == "generativelanguage.googleapis.com":
            return httpx.Response(status)
        body = json.loads(request.content)
        assert body["model"] == "qwen3.6"
        assert body["reasoning_effort"] == "none"
        return httpx.Response(
            200,
            json={"choices": [{"finish_reason": "stop", "message": {"content": "Lote: 12345"}}]},
        )

    mock_client(monkeypatch, respond)
    model = VisionFallback(
        replace(
            settings,
            gemini_api_key="gemini-secret",
            helmcode_api_key="helm-secret",
            helmcode_vision_models=("qwen3.6",),
        )
    )
    result = model.transcribe(b"image", 1, (595, 842))
    assert result[0].raw == "Lote: 12345"
    assert "visual:helmcode:qwen3.6:" in result[0].id
    assert requests == ["generativelanguage.googleapis.com", "api.helmcode.com"]


def test_two_helm_models_have_distinct_visual_votes(settings, monkeypatch):
    def respond(request):
        return httpx.Response(
            200,
            json={"choices": [{"finish_reason": "stop", "message": {"content": "Lote: 12345"}}]},
        )

    mock_client(monkeypatch, respond)
    settings = replace(
        settings,
        helmcode_api_key="secret",
        vision_providers=("helmcode",),
        helmcode_vision_models=("qwen3.6", "qwen3.6", "gemma4"),
    )
    readers = VisionFallback(settings).transcribe_readers(b"image", 1, (595, 842))
    assert set(readers) == {"visual:helmcode:qwen3.6", "visual:helmcode:gemma4"}
    field = ExtractionField(name="lote", type="text", labels=["Lote"])
    reading, _ = read_schema_fields(
        [line for group in readers.values() for line in group], [field], 0.9
    )
    assert reading["lote"].value == "12345"
    single, _ = read_schema_fields(readers["visual:helmcode:qwen3.6"], [field], 0.9)
    assert single["lote"].value is None


def test_same_model_through_compatible_and_helm_counts_once(settings, monkeypatch):
    requested_models = []

    def respond(request):
        model = json.loads(request.content)["model"]
        requested_models.append(model)
        return httpx.Response(
            200,
            json={"choices": [{"finish_reason": "stop", "message": {"content": "Lote: 12345"}}]},
        )

    mock_client(monkeypatch, respond)
    configured = replace(
        settings,
        vlm_url="https://api.helmcode.com/v1",
        vlm_model="qwen3.6",
        helmcode_api_key="secret",
        helmcode_vision_models=("qwen3.6",),
    )
    readers = VisionFallback(configured).transcribe_readers(b"image", 1, (595, 842))
    assert set(readers) == {"visual:compatible:qwen3.6"}
    assert requested_models == ["qwen3.6"]
    field = ExtractionField(name="lote", type="text", labels=["Lote"])
    reading, _ = read_schema_fields(next(iter(readers.values())), [field], 0.9)
    assert reading["lote"].value is None

    with_second_model = replace(
        configured,
        data_dir=settings.data_dir / "second",
        helmcode_vision_models=("qwen3.6", "gemma4"),
    )
    readers = VisionFallback(with_second_model).transcribe_readers(b"image", 1, (595, 842))
    assert set(readers) == {"visual:compatible:qwen3.6", "visual:helmcode:gemma4"}
    assert requested_models == ["qwen3.6", "qwen3.6", "gemma4"]


def test_schema_two_provider_labels_for_same_model_do_not_verify():
    field = ExtractionField(name="lote", type="text", labels=["Lote"])
    duplicate = [
        lines("Lote: 12345", "vlm")[0].model_copy(update={"id": f"visual:{provider}:qwen3.6:p1:0"})
        for provider in ("compatible", "helmcode")
    ]
    reading, _ = read_schema_fields(duplicate, [field], 0.9)
    assert reading["lote"].value is None
    assert reading["lote"].proposed_value == "12345"


def test_successful_first_reader_never_calls_helm(settings, monkeypatch):
    hosts = []

    def respond(request):
        hosts.append(request.url.host)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {"parts": [{"text": "TOTAL 100,00 EUR"}]},
                    }
                ]
            },
        )

    mock_client(monkeypatch, respond)
    reader = VisionFallback(replace(settings, gemini_api_key="secret", helmcode_api_key="secret"))
    assert reader.transcribe(b"image", 1, (595, 842))
    assert hosts == ["generativelanguage.googleapis.com"]


def test_helm_text_judge_rejects_invented_candidate(settings, monkeypatch):
    def respond(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps({"answers": {"supplier_tax_id": "invented"}})
                        },
                    }
                ]
            },
        )

    mock_client(monkeypatch, respond)
    readers = {"primary": lines("NIF: B98120774", "ocr", 0.99)}
    fields, _, _ = reconcile(readers, settings.ocr_min_confidence)
    judge = TextJudge(replace(settings, helmcode_api_key="secret", text_providers=("helmcode",)))
    with pytest.raises(ProviderUnavailable):
        judge.select(readers, fields)


def test_helm_text_judge_valid_selection_replays(settings, monkeypatch):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps({"answers": {"supplier_tax_id": "B98120774"}})
                        },
                    }
                ]
            },
        )

    mock_client(monkeypatch, respond)
    readers = {"primary": lines("NIF: B98120774", "ocr", 0.99)}
    fields, _, _ = reconcile(readers, settings.ocr_min_confidence)
    judge = TextJudge(replace(settings, helmcode_api_key="secret", text_providers=("helmcode",)))
    first = judge.select(readers, fields)
    second = judge.select(readers, fields)
    assert first == second
    assert first["answers"]["supplier_tax_id"]["choice"] == "B98120774"
    assert first["role"] == "textual_recommendation_only"
    assert first["visual_vote"] is False
    assert len(calls) == 1


def test_all_visual_providers_down_does_not_cache_empty_api_result(settings, monkeypatch):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(503)

    mock_client(monkeypatch, respond)
    configured = replace(settings, gemini_api_key="secret", vision_providers=("gemini",))
    service = ExtractionService(configured, NoOCR(), VisionFallback(configured))
    item = service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf")
    options = ExtractOptions(mode="api", jev=False)
    first = service.extract(item, options)
    second = service.extract(item, options)
    assert any(warning["code"] == "VLM_ERROR" for warning in first.warnings)
    assert not first.cache_hit and not second.cache_hit
    assert calls  # The first attempt reached the mocked provider.


def test_helm_schema_quote_must_be_existing_substring(settings, monkeypatch):
    supplied = lines("Documento sin fecha")

    def respond(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {"fecha": {"line_id": supplied[0].id, "quote": "21/04/2026"}}
                            )
                        },
                    }
                ]
            },
        )

    mock_client(monkeypatch, respond)
    reader = SchemaFieldReader(
        replace(settings, helmcode_api_key="secret", vision_providers=("helmcode",))
    )
    result, warnings = reader.read(supplied, [ExtractionField(name="fecha", type="date")])
    assert result["fecha"].value is None
    assert warnings == [{"code": "SCHEMA_READER_ERROR"}]


def test_helm_schema_grounded_quote_uses_text_model(settings, monkeypatch):
    supplied = lines("Caduca el 21/04/2026")

    def respond(request):
        assert json.loads(request.content)["model"] == "glm5.3"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {"fecha": {"line_id": supplied[0].id, "quote": "21/04/2026"}}
                            )
                        },
                    }
                ]
            },
        )

    mock_client(monkeypatch, respond)
    reader = SchemaFieldReader(
        replace(
            settings,
            helmcode_api_key="secret",
            helmcode_text_model="glm5.3",
            vision_providers=("helmcode",),
        )
    )
    result, warnings = reader.read(supplied, [ExtractionField(name="fecha", type="date")])
    assert warnings == []
    assert result["fecha"].value == "2026-04-21"
