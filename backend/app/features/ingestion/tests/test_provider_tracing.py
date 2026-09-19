import json
from dataclasses import replace

import httpx
import pytest

from app.core import events
from app.features.ingestion.ocr.errors import ProviderUnavailable
from app.features.ingestion.ocr.journal import recorded_call
from app.features.ingestion.ocr.judge import TextJudge
from app.features.ingestion.ocr.vision import VisionFallback
from app.features.ingestion.pdf.invoice import parse_invoice

from .conftest import lines


def test_gemini_provider_spans_distinguish_network_and_replay(settings, monkeypatch):
    rows, requests = [], []
    monkeypatch.setattr(events, "_write", rows.extend)

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"finishReason": "STOP", "content": {"parts": [{"text": "TOTAL 100,00 EUR"}]}}
                ],
                "usageMetadata": {
                    "promptTokenCount": 12,
                    "candidatesTokenCount": 4,
                    "totalTokenCount": 16,
                },
            },
        )

    original_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    model = VisionFallback(replace(settings, gemini_api_key="secret-key"))
    with events.span("vision"):
        for _ in range(2):
            assert model.transcribe(b"private-image", 1, (595, 842))[0].text == "TOTAL 100,00 EUR"

    assert len(requests) == 1
    provider = [row for row in rows if row["step"] == "provider_call"]
    assert len(provider) == 2
    assert [row["data"]["outcome"] for row in provider] == ["success", "replay"]
    assert [row["data"]["network_attempted"] for row in provider] == [True, False]
    assert [row["data"]["network_succeeded"] for row in provider] == [True, False]
    assert [row["data"]["journal_hit"] for row in provider] == [False, True]
    assert all(row["data"]["input_tokens"] == 12 for row in provider)
    assert all(row["data"]["output_tokens"] == 4 for row in provider)
    assert all(row["parent_id"] == rows[-1]["span_id"] for row in provider)
    trace = json.dumps(rows, default=str)
    assert "secret-key" not in trace
    assert "private-image" not in trace
    assert "TOTAL 100,00 EUR" not in trace


def test_provider_failure_and_uncertain_replay_have_sanitized_spans(tmp_path, monkeypatch):
    rows = []
    monkeypatch.setattr(events, "_write", rows.extend)
    calls = []

    def fail(mark_network_attempt):
        calls.append(True)
        mark_network_attempt()
        raise RuntimeError("private response with secret-key and invoice data")

    args = (tmp_path, {"request": "private invoice content"}, fail)
    for _ in range(2):
        with pytest.raises((ProviderUnavailable, RuntimeError)):
            recorded_call(*args, provider="gemini", model="gemini-test", operation="image")

    assert len(calls) == 1
    assert [row["status"] for row in rows] == ["error", "error"]
    assert [row["data"]["outcome"] for row in rows] == ["error", "blocked_uncertain"]
    assert [row["data"]["network_attempted"] for row in rows] == [True, False]
    assert [row["data"]["journal_hit"] for row in rows] == [False, True]
    trace = json.dumps(rows, default=str)
    assert "secret-key" not in trace
    assert "private invoice content" not in trace
    assert "private response" not in trace


def test_generic_vision_and_text_judge_calls_are_traced(settings, monkeypatch):
    rows = []
    monkeypatch.setattr(events, "_write", rows.extend)

    def respond(request):
        if request.url.host == "vision.example":
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "TOTAL 100,00 EUR"}}],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
                },
            )
        questions = json.loads(request.content)["questions"]
        return httpx.Response(
            200,
            json={
                "answers": {
                    name: {
                        "type": "choice",
                        "choice": next(value for value in question["criteria"] if value != "none"),
                        "probabilities": {
                            value: int(value != "none") for value in question["criteria"]
                        },
                        "confidence": 1,
                    }
                    for name, question in questions.items()
                },
                "usage": {"input_tokens": 11, "output_tokens": 2},
            },
        )

    original_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    vision = VisionFallback(
        replace(settings, vlm_url="https://vision.example/v1", vlm_model="vision-test")
    )
    judge = TextJudge(replace(settings, jev_api_key="judge-secret"))
    source = lines("TOTAL: 100,00 EUR", "ocr", 0.99)
    with events.span("extraction"):
        assert vision.transcribe(b"private-image", 1, (595, 842))
        assert judge.select({"primary": source}, parse_invoice(source)[0])["answers"]

    calls = [row["data"] for row in rows if row["step"] == "provider_call"]
    assert [(call["provider"], call["operation"]) for call in calls] == [
        ("vision", "image_transcription"),
        ("jev", "text_selection"),
    ]
    assert all(call["network_attempted"] and call["network_succeeded"] for call in calls)
    assert [call["input_tokens"] for call in calls] == [7, 11]
    assert [call["output_tokens"] for call in calls] == [3, 2]
    trace = json.dumps(rows, default=str)
    assert "judge-secret" not in trace
    assert "private-image" not in trace
    assert "TOTAL: 100,00 EUR" not in trace


@pytest.mark.parametrize(
    "provider,response,expected",
    [
        (
            "gemini",
            {
                "candidates": [{"finishReason": "MAX_TOKENS"}],
                "usageMetadata": {"promptTokenCount": 21, "candidatesTokenCount": 8},
            },
            (21, 8),
        ),
        (
            "vision",
            {
                "choices": [{"message": {"content": ""}}],
                "usage": {"prompt_tokens": 14, "completion_tokens": 2},
            },
            (14, 2),
        ),
    ],
)
def test_rejected_200_response_keeps_billed_usage(
    settings, monkeypatch, provider, response, expected
):
    rows = []
    monkeypatch.setattr(events, "_write", rows.extend)
    original_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response)),
            **kwargs,
        ),
    )
    configured = (
        replace(settings, gemini_api_key="secret-key")
        if provider == "gemini"
        else replace(settings, vlm_url="https://vision.example/v1", vlm_model="vision-test")
    )
    with pytest.raises(ProviderUnavailable):
        VisionFallback(configured).transcribe(b"private-image", 1, (595, 842))
    [call] = [row for row in rows if row["step"] == "provider_call"]
    assert call["status"] == "error"
    assert call["data"]["outcome"] == "error"
    assert call["data"]["network_attempted"] is True
    assert call["data"]["network_succeeded"] is False
    assert call["data"]["http_status_code"] == 200
    assert (call["data"]["input_tokens"], call["data"]["output_tokens"]) == expected
    assert "secret-key" not in json.dumps(rows, default=str)
    journal = settings.data_dir / "provider-journal" / provider
    [record] = journal.glob("*.json")
    assert json.loads(record.read_text())["state"] == "uncertain_or_failed"


def test_provider_http_failure_records_status_without_response_body(settings, monkeypatch):
    rows = []
    monkeypatch.setattr(events, "_write", rows.extend)
    original_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(429, text="private response body")
            ),
            **kwargs,
        ),
    )
    with pytest.raises(ProviderUnavailable):
        VisionFallback(replace(settings, gemini_api_key="secret-key")).transcribe(
            b"private-image", 1, (595, 842)
        )
    [call] = [row for row in rows if row["step"] == "provider_call"]
    assert call["data"]["http_status_code"] == 429
    assert call["data"]["network_attempted"] is True
    assert "input_tokens" not in call["data"]
    assert "private response body" not in json.dumps(rows, default=str)
