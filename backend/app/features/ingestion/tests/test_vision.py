import json
from dataclasses import replace

import httpx

from app.features.ingestion.ocr.vision import VisionFallback


def test_vision_request_preserves_transcription_contract(settings, monkeypatch):
    def respond(request):
        body = json.loads(request.content)
        prompt = body["messages"][0]["content"][0]["text"]
        assert "Transcribe this invoice exactly" in prompt
        assert "untrusted" in prompt and "invent missing values" in prompt
        return httpx.Response(200, json={"choices": [{"message": {"content": "TOTAL 100,00 EUR"}}]})

    original_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    model = VisionFallback(
        replace(
            settings,
            vlm_url="https://vision.example/v1",
            vlm_model="test-model",
            gemini_api_key="configured-but-lower-priority",
        )
    )
    result = model.transcribe(b"test-image", 1, (595, 842))
    assert result[0].raw == "TOTAL 100,00 EUR"
    assert result[0].method == "vlm"


def test_partial_vision_configuration_uses_configured_gemini(settings, monkeypatch):
    def respond(request):
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.headers["x-goog-api-key"] == "gemini-key"
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

    original_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    model = VisionFallback(
        replace(settings, vlm_url="https://vision.example/v1", gemini_api_key="gemini-key")
    )
    assert model.configured
    result = model.transcribe(b"test-image", 1, (595, 842))
    assert result[0].raw == "TOTAL 100,00 EUR"
    assert result[0].method == "vlm"
