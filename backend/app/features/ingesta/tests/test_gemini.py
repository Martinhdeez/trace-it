import json

import httpx
import pytest

from app.features.ingesta.ocr.errors import ProviderUnavailable
from app.features.ingesta.ocr.gemini import generate, output_text
from app.features.ingesta.tools.compare_gemini_ocr import cached_call

RESPONSE = {
    "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "TOTAL 100,00 EUR"}]}}]
}


def test_gemini_keeps_key_out_of_payload_and_reuses_cached_response(tmp_path):
    calls = []

    def respond(request):
        calls.append(request)
        assert request.headers["x-goog-api-key"] == "secret-for-test"
        assert "secret-for-test" not in request.content.decode()
        assert "[ILLEGIBLE]" in request.content.decode()
        return httpx.Response(200, json=RESPONSE)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        for offline in (False, True):
            record = cached_call(
                client, "gemini-test", "secret-for-test", [b"png"], tmp_path, offline
            )
            assert output_text(record["response"]) == "TOTAL 100,00 EUR"
    assert len(calls) == 1
    assert "secret-for-test" not in next(tmp_path.glob("*.json")).read_text()


def test_gemini_timeout_is_journaled_without_automatic_resubmission(tmp_path):
    calls = []

    def fail(request):
        calls.append(request)
        raise httpx.ReadTimeout("timeout", request=request)

    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        with pytest.raises(httpx.ReadTimeout):
            cached_call(client, "gemini-test", "key", [b"png"], tmp_path, False)
        with pytest.raises(RuntimeError, match="incomplete"):
            cached_call(client, "gemini-test", "key", [b"png"], tmp_path, False)
    assert len(calls) == 1
    assert json.loads(next(tmp_path.glob("*.json")).read_text())["state"] == "uncertain_or_failed"


def test_gemini_rejects_truncated_output_and_redacts_provider_body():
    with pytest.raises(ProviderUnavailable):
        output_text({"candidates": [{"finishReason": "MAX_TOKENS"}]})
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(503, text="private-details")
            )
        ) as client,
        pytest.raises(ProviderUnavailable, match="HTTP 503") as error,
    ):
        generate(client, "gemini-test", "key", [b"png"])
    assert "private-details" not in str(error.value)
