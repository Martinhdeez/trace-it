"""Rate limits: bounded concurrency, backoff on refusals, fallback, and no duplicate delivery."""

import io
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import httpx
import pytest

from app.core import events
from app.features.ingestion.ocr import errors, journal
from app.features.ingestion.ocr.errors import ProviderUnavailable
from app.features.ingestion.ocr.vision import VisionFallback
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService

from .conftest import NoOCR, pdf_bytes

GEMINI = "generativelanguage.googleapis.com"
GEMINI_OK = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "TOTAL 1"}]}}]}
HELM_OK = {"choices": [{"finish_reason": "stop", "message": {"content": "Lote: 12345"}}]}


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setattr(errors, "_cooldown_until", {})
    monkeypatch.setenv("TRACEPAY_PROVIDER_RETRY_MAX_WAIT_S", "20")
    sleeps = []
    monkeypatch.setattr(journal, "_sleep", sleeps.append)
    rows = []
    monkeypatch.setattr(events, "_write", rows.extend)
    return sleeps, rows


def mock_client(monkeypatch, respond):
    original = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs)
    )


def provider_spans(rows):
    return [row["data"] for row in rows if row["step"] == "provider_call"]


def test_parallel_calls_respect_the_provider_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("TRACEPAY_VISION_MAX_CONCURRENCY", "2")
    active, peak, lock = 0, 0, threading.Lock()

    def call(mark_network_attempt):
        nonlocal active, peak
        mark_network_attempt()
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return {"ok": True}

    def one(index):
        return journal.recorded_call(
            tmp_path, {"n": index}, call, provider="stub", model="m", operation="image"
        )

    with ThreadPoolExecutor(8) as pool:
        assert list(pool.map(one, range(8))) == [{"ok": True}] * 8
    assert peak == 2


def test_rate_limit_with_retry_after_retries_then_succeeds(settings, monkeypatch, isolated):
    sleeps, rows = isolated
    hosts = []

    def respond(request):
        hosts.append(request.url.host)
        if len(hosts) == 1:
            return httpx.Response(429, headers={"Retry-After": "3"})
        return httpx.Response(200, json=GEMINI_OK)

    mock_client(monkeypatch, respond)
    reader = VisionFallback(replace(settings, gemini_api_key="secret", helmcode_api_key="secret"))
    assert reader.transcribe(b"image", 1, (595, 842))[0].text == "TOTAL 1"
    assert hosts == [GEMINI, GEMINI]
    assert sleeps == [3.0]
    first, second = provider_spans(rows)
    assert (first["http_status_code"], first["retry_after_s"], first["attempt"]) == (429, 3.0, 1)
    assert (second["attempt"], second["backoff_basis"], second["backoff_s"]) == (
        2,
        "retry_after",
        3.0,
    )
    assert second["outcome"] == "success" and second["provider"] == "gemini"


def test_persistent_rate_limit_falls_back_to_helmcode(settings, monkeypatch, isolated):
    sleeps, rows = isolated
    hosts = []

    def respond(request):
        hosts.append(request.url.host)
        if request.url.host == GEMINI:
            return httpx.Response(429)
        return httpx.Response(200, json=HELM_OK)

    mock_client(monkeypatch, respond)
    reader = VisionFallback(
        replace(
            settings,
            gemini_api_key="secret",
            helmcode_api_key="secret",
            helmcode_vision_models=("qwen3.6",),
        )
    )
    lines = reader.transcribe(b"image", 1, (595, 842))
    assert "visual:helmcode:qwen3.6:" in lines[0].id  # the provider that answered
    assert hosts.count(GEMINI) == len(sleeps) + 1 > 1 and hosts[-1] == "api.helmcode.com"
    assert sum(sleeps) <= 20
    assert all(span["backoff_basis"] == "exponential" for span in provider_spans(rows)[1:-1])
    assert provider_spans(rows)[-1]["fallback"] is True


def test_persistent_rate_limit_without_fallback_ends_null(settings, monkeypatch, isolated):
    sleeps, _ = isolated
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "4"})

    mock_client(monkeypatch, respond)
    configured = replace(settings, gemini_api_key="secret", vision_providers=("gemini",))
    service = ExtractionService(configured, NoOCR(), VisionFallback(configured))
    item = service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf")
    result = service.extract(item, ExtractOptions(mode="api", jev=False))
    assert any(warning["code"] == "VLM_ERROR" for warning in result.warnings)
    assert all(reading.value is None for reading in result.fields.values())  # -> MISSING_DATA
    assert sleeps == [4.0] * 5 and len(calls) == 6  # 20 s budget, then give up


def test_uncertain_delivery_is_never_resent(settings, monkeypatch, isolated):
    sleeps, _ = isolated
    hosts = []

    def respond(request):
        hosts.append(request.url.host)
        raise httpx.ReadTimeout("delivery uncertain")

    mock_client(monkeypatch, respond)
    reader = VisionFallback(replace(settings, gemini_api_key="secret"))
    for _ in range(2):
        with pytest.raises(ProviderUnavailable):
            reader.transcribe(b"image", 1, (595, 842))
        errors._cooldown_until.clear()
    assert hosts == [GEMINI] and sleeps == []
    record = json.loads(
        next((settings.data_dir / "provider-journal" / "gemini").glob("*.json")).read_text()
    )
    assert record["state"] == "uncertain_or_failed"


def test_retry_after_http_date_is_parsed():
    later = httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2099 07:28:00 GMT"})
    assert journal.retry_after(later) > 0
    assert journal.retry_after(httpx.Response(429, headers={"Retry-After": "7"})) == 7.0
    assert journal.retry_after(httpx.Response(429)) is None
