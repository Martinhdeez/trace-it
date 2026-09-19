import json

import pytest

from app.core import events
from app.features.ingestion.ocr.errors import ProviderUnavailable
from app.features.ingestion.ocr.journal import record_response, recorded_call
from app.features.ingestion.ocr.pricing import cost_snapshot


def test_gemini_thoughts_and_cache_are_billed_without_double_counting():
    usage = {"input_tokens": 100, "output_tokens": 20, "cached_tokens": 40, "reasoning_tokens": 5}
    result = cost_snapshot("gemini", "gemini-3.1-flash-lite", usage)
    assert result["cost_status"] == "known"
    assert result["cost_usd"] == pytest.approx((60 * 0.25 + 40 * 0.025 + 25 * 1.5) / 1e6)


def test_helmcode_unknown_included_and_metered(monkeypatch):
    usage = {"input_tokens": 100, "output_tokens": 20, "reasoning_tokens": 5}
    assert cost_snapshot("helmcode", "qwen3.6", usage)["cost_status"] == "unknown"
    monkeypatch.setenv("TRACEPAY_HELMCODE_BILLING_MODE", "included")
    assert cost_snapshot("helmcode", "qwen3.6", usage)["cost_usd"] == 0
    monkeypatch.setenv("TRACEPAY_HELMCODE_BILLING_MODE", "metered")
    monkeypatch.setenv("TRACEPAY_HELMCODE_INPUT_USD_PER_M", "1")
    monkeypatch.setenv("TRACEPAY_HELMCODE_OUTPUT_USD_PER_M", "2")
    result = cost_snapshot("helmcode", "qwen3.6", usage)
    assert result["cost_usd"] == pytest.approx(140 / 1e6)
    assert cost_snapshot("vision", "custom", usage)["cost_status"] == "unknown"


def test_failed_200_journals_usage_cost_and_safe_error_metadata(tmp_path, monkeypatch):
    rows = []
    monkeypatch.setattr(events, "_write", rows.extend)

    def fail(mark_network_attempt):
        mark_network_attempt()
        record_response(
            "gemini",
            200,
            {
                "usageMetadata": {
                    "promptTokenCount": 100,
                    "candidatesTokenCount": 20,
                    "thoughtsTokenCount": 5,
                    "cachedContentTokenCount": 40,
                }
            },
        )
        raise ValueError("private invoice text")

    with pytest.raises(ProviderUnavailable) as raised:
        recorded_call(
            tmp_path,
            {"id": 1},
            fail,
            provider="gemini",
            model="gemini-3.1-flash-lite",
            operation="image_transcription",
        )
    assert raised.value.http_status_code == 200
    [record_path] = tmp_path.glob("*.json")
    journal = json.loads(record_path.read_text())
    telemetry = journal["telemetry"]
    assert telemetry["cost_status"] == "known"
    assert telemetry["reasoning_tokens"] == 5
    assert telemetry["cached_tokens"] == 40
    assert "private invoice text" not in json.dumps(journal)
    assert rows[0]["data"]["output_tokens"] == 20


def test_http_failure_without_usage_remains_unknown(tmp_path, monkeypatch):
    rows = []
    monkeypatch.setattr(events, "_write", rows.extend)

    def fail(mark_network_attempt):
        mark_network_attempt()
        record_response("helmcode", 503, retry_after_s=2)
        raise RuntimeError("private provider response")

    with pytest.raises(ProviderUnavailable) as raised:
        recorded_call(
            tmp_path,
            {"id": 2},
            fail,
            provider="helmcode",
            model="qwen3.6",
            operation="text_selection",
        )
    assert (raised.value.http_status_code, raised.value.retry_after_s) == (503, 2)
    assert rows[0]["data"]["cost_status"] == "unknown"
    assert "input_tokens" not in rows[0]["data"]
    [record_path] = tmp_path.glob("*.json")
    assert json.loads(record_path.read_text())["telemetry"]["http_status_code"] == 503
