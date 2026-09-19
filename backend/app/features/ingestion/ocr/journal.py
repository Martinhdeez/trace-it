"""Content-addressed provider calls with no automatic retry after uncertain delivery."""

import hashlib
import json
import os
import random
import threading
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from filelock import FileLock

from app.core import events
from app.features.ingestion.cache import count_reader

from .errors import ProviderUnavailable
from .pricing import cost_snapshot


def _token_usage(provider, response):
    if not isinstance(response, dict):
        return {}
    usage = response.get("usageMetadata" if provider == "gemini" else "usage")
    if not isinstance(usage, dict):
        return {}
    names = {
        "input_tokens": ("promptTokenCount", "prompt_tokens", "input_tokens"),
        "output_tokens": ("candidatesTokenCount", "completion_tokens", "output_tokens"),
        "total_tokens": ("totalTokenCount", "total_tokens"),
        "cached_tokens": ("cachedContentTokenCount", "cached_tokens"),
        "reasoning_tokens": ("thoughtsTokenCount", "reasoning_tokens"),
    }
    tokens = {
        name: usage[key]
        for name, keys in names.items()
        if (key := next((key for key in keys if key in usage), None)) is not None
        and type(usage[key]) is int
        and usage[key] >= 0
    }
    if provider != "gemini":
        details = usage.get("completion_tokens_details")
        if isinstance(details, dict) and type(details.get("reasoning_tokens")) is int:
            tokens["reasoning_tokens"] = max(0, details["reasoning_tokens"])
        details = usage.get("prompt_tokens_details")
        if not isinstance(details, dict):
            details = usage.get("input_tokens_details")
        if isinstance(details, dict) and type(details.get("cached_tokens")) is int:
            tokens["cached_tokens"] = max(0, details["cached_tokens"])
    if "total_tokens" not in tokens and "input_tokens" in tokens and "output_tokens" in tokens:
        tokens["total_tokens"] = tokens["input_tokens"] + tokens["output_tokens"]
        if provider == "gemini":
            tokens["total_tokens"] += tokens.get("reasoning_tokens", 0)
    return tokens


# Refusals worth waiting for: rate limit (quota) and service unavailable. Other refusals
# (bad key, bad request) fail at once; an uncertain delivery is never retried.
RETRYABLE = {429, 503}
_slots: dict[str, threading.BoundedSemaphore] = {}
_slots_lock = threading.Lock()
_sleep = time.sleep  # tests replace it


def _slot(provider):
    """One process-wide concurrency limit per remote provider."""
    with _slots_lock:
        if provider not in _slots:
            limit = int(os.getenv("TRACEPAY_VISION_MAX_CONCURRENCY", "3"))
            _slots[provider] = threading.BoundedSemaphore(max(1, limit))
        return _slots[provider]


def retry_after(response):
    """Seconds from a `Retry-After` header (delta or HTTP date), else None."""
    value = response.headers.get("retry-after")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        return max(0.0, (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds())
    except (TypeError, ValueError):
        return None


def _backoff(exc, attempt):
    if exc.retry_after_s is not None:
        return max(1.0, exc.retry_after_s), "retry_after"
    return min(2 ** (attempt - 1), 16) * random.uniform(0.5, 1.5), "exponential"


def record_response(provider, status_code, payload=None, *, retry_after_s=None):
    """Retain safe HTTP metadata even when a response fails validation."""
    trace = events.current()
    if (
        trace is not None
        and trace.step == "provider_call"
        and trace.data.get("provider") == provider
    ):
        if type(status_code) is int and 100 <= status_code <= 599:
            trace.set(http_status_code=status_code)
        if type(retry_after_s) in (int, float) and 0 <= retry_after_s <= 3600:
            trace.set(retry_after_s=float(retry_after_s))
        usage = _token_usage(provider, payload)
        trace.set(**usage)
        trace.set(**cost_snapshot(provider, trace.data.get("model"), usage))


def recorded_call(
    directory,
    identity,
    call,
    *,
    provider=None,
    model=None,
    operation=None,
    reader=None,
    fallback=False,
    force=False,
):
    reader = reader or (
        "schema"
        if operation == "schema_selection"
        else "vlm"
        if provider == "helmcode" and operation == "image_transcription"
        else "jev"
        if provider == "helmcode" and operation == "text_selection"
        else {"gemini": "vlm", "vision": "vlm", "jev": "jev"}.get(provider)
    )
    if reader:
        count_reader(reader + "_journal_calls")
    directory.mkdir(parents=True, exist_ok=True)
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    path = directory / f"{fingerprint}.json"
    if provider is None:
        return _recorded_call(path, identity, call, reader=reader, force=force)

    # A 429/503 was refused, not delivered, so the journal lets the same request go again:
    # wait (Retry-After, else exponential with jitter) within a total budget, then give up
    # and let the caller's fallback chain take over. Each attempt is its own provider_call.
    budget = float(os.getenv("TRACEPAY_PROVIDER_RETRY_MAX_WAIT_S", "2"))
    waited, retry = 0.0, {}
    for attempt in range(1, 100):
        try:
            return _attempt(
                path,
                identity,
                call,
                (provider, model, operation, fallback, fingerprint),
                reader,
                force,
                {"attempt": attempt, **retry},
            )
        except ProviderUnavailable as exc:
            if exc.http_status_code not in RETRYABLE or exc.journal_blocked:
                raise
            wait, basis = _backoff(exc, attempt)
            if waited + wait > budget:
                raise
            _sleep(wait)
            waited += wait
            retry = {"backoff_s": round(wait, 3), "backoff_basis": basis, "waited_s": waited}
    raise ProviderUnavailable(f"{provider} call unavailable")


def _attempt(path, identity, call, span, reader, force, retry):
    provider, model, operation, fallback, fingerprint = span
    failure = None
    result = None
    with events.span(
        "provider_call",
        provider=provider,
        model=model,
        operation=operation,
        fallback=fallback,
        request_fingerprint=fingerprint,
        journal_hit=False,
        network_attempted=False,
        network_succeeded=False,
        **retry,
    ) as trace:

        def limited(mark_network_attempt):
            queued = time.perf_counter()
            with _slot(provider):
                trace.set(slot_wait_ms=round((time.perf_counter() - queued) * 1000))
                return call(mark_network_attempt)

        try:
            result = _recorded_call(path, identity, limited, trace, reader, force)
        except Exception as exc:
            failure = exc
            trace.status = "error"
            trace.set(error="Provider call unavailable", error_type=type(exc).__name__)
    if failure is not None:
        unavailable = ProviderUnavailable(f"{provider} call unavailable")
        unavailable.http_status_code = trace.data.get("http_status_code")
        unavailable.retry_after_s = trace.data.get("retry_after_s")
        unavailable.journal_blocked = trace.data.get("outcome") == "blocked_uncertain"
        raise unavailable from None
    return result


def _recorded_call(path, identity, call, trace=None, reader=None, force=False):
    with FileLock(str(path) + ".lock", timeout=60):
        exists = path.exists() and not force
        record = json.loads(path.read_text(encoding="utf-8")) if exists else None
        if record is not None and record["state"] != "refused":  # refused: call again
            if trace is not None:
                trace.set(journal_hit=True)
            if record["state"] != "complete":
                if trace is not None:
                    trace.set(outcome="blocked_uncertain")
                raise RuntimeError("Provider delivery uncertain; inspect the request journal")
            if reader:
                count_reader(reader + "_cache_hits")
            if trace is not None:
                trace.set(outcome="replay")
            return record["response"]
        record = {"identity": identity, "state": "started", "started_at": time.time()}
        path.write_text(json.dumps(record), encoding="utf-8")
        started = time.perf_counter()
        network_started = None

        def mark_network_attempt():
            nonlocal network_started
            if network_started is None:
                network_started = time.perf_counter()
            if reader and (trace is None or not trace.data["network_attempted"]):
                count_reader(reader + "_requests")
            if trace is not None:
                trace.set(network_attempted=True)

        try:
            if trace is None:
                mark_network_attempt()
            record["response"] = call(mark_network_attempt) if trace else call()
            record["state"] = "complete"
            if trace is not None:
                trace.set(
                    outcome="forced" if force else "success",
                    network_succeeded=trace.data["network_attempted"],
                )
                if trace.data["network_attempted"]:
                    usage = _token_usage(trace.data["provider"], record["response"])
                    trace.set(**usage)
                    if "cost_status" not in trace.data:
                        trace.set(
                            **cost_snapshot(trace.data["provider"], trace.data["model"], usage)
                        )
        except Exception as exc:
            # The provider answered and refused (429 rate limit, 503, a bad key): nothing was
            # delivered, so the next call may try again. A timeout, a dropped connection or a
            # 2xx whose body failed validation stays uncertain and blocks until inspected.
            status = trace.data.get("http_status_code") if trace is not None else None
            refused = status is not None and (400 <= status < 500 or status == 503)
            record.update(
                state="refused" if refused else "uncertain_or_failed",
                error_type=type(exc).__name__,
                **({"http_status_code": status} if refused else {}),
            )
            if trace is not None:
                trace.set(outcome="error")
            raise
        finally:
            record["seconds"] = round(time.perf_counter() - started, 3)
            if trace is not None:
                if network_started is not None:
                    trace.set(
                        network_latency_ms=round((time.perf_counter() - network_started) * 1000)
                    )
                if trace.data["network_attempted"] and "cost_status" not in trace.data:
                    trace.set(**cost_snapshot(trace.data["provider"], trace.data["model"], {}))
                safe_fields = (
                    "http_status_code",
                    "retry_after_s",
                    "input_tokens",
                    "output_tokens",
                    "total_tokens",
                    "cached_tokens",
                    "reasoning_tokens",
                    "cost_status",
                    "cost_basis",
                    "cost_usd",
                    "input_usd_per_m",
                    "output_usd_per_m",
                    "cache_usd_per_m",
                    "network_latency_ms",
                    "network_attempted",
                    "network_succeeded",
                )
                record["telemetry"] = {
                    key: trace.data[key] for key in safe_fields if key in trace.data
                }
            temporary = path.with_suffix(".part")
            temporary.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            os.replace(temporary, path)
        return record["response"]
