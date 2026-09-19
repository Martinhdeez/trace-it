"""Content-addressed provider calls with no automatic retry after uncertain delivery."""

import hashlib
import json
import os
import time

from filelock import FileLock

from app.core import events
from app.features.ingestion.cache import count_reader

from .errors import ProviderUnavailable


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
    }
    return {
        name: usage[key]
        for name, keys in names.items()
        if (key := next((key for key in keys if key in usage), None)) is not None
        and type(usage[key]) is int
        and usage[key] >= 0
    }


def record_response(provider, status_code, payload=None):
    """Retain safe HTTP metadata even when a response fails validation."""
    trace = events.current()
    if (
        trace is not None
        and trace.step == "provider_call"
        and trace.data.get("provider") == provider
    ):
        if type(status_code) is int and 100 <= status_code <= 599:
            trace.set(http_status_code=status_code)
        trace.set(**_token_usage(provider, payload))


def recorded_call(
    directory, identity, call, *, provider=None, model=None, operation=None, reader=None
):
    reader = reader or {"gemini": "vlm", "vision": "vlm", "jev": "jev"}.get(provider)
    if reader:
        count_reader(reader + "_journal_calls")
    directory.mkdir(parents=True, exist_ok=True)
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    path = directory / f"{fingerprint}.json"
    if provider is None:
        return _recorded_call(path, identity, call, reader=reader)

    failure = None
    result = None
    with events.span(
        "provider_call",
        provider=provider,
        model=model,
        operation=operation,
        request_fingerprint=fingerprint,
        journal_hit=False,
        network_attempted=False,
        network_succeeded=False,
    ) as trace:
        try:
            result = _recorded_call(path, identity, call, trace, reader)
        except Exception as exc:
            failure = exc
            trace.status = "error"
            trace.set(error="Provider call unavailable", error_type=type(exc).__name__)
        else:
            trace.set(**_token_usage(provider, result))
    if failure is not None:
        if trace.data.get("outcome") == "blocked_uncertain":
            raise failure
        raise ProviderUnavailable(f"{provider} call unavailable") from None
    return result


def _recorded_call(path, identity, call, trace=None, reader=None):
    with FileLock(str(path) + ".lock", timeout=60):
        if path.exists():
            record = json.loads(path.read_text(encoding="utf-8"))
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

        def mark_network_attempt():
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
                trace.set(outcome="success", network_succeeded=trace.data["network_attempted"])
        except Exception as exc:
            record.update(state="uncertain_or_failed", error_type=type(exc).__name__)
            if trace is not None:
                trace.set(outcome="error")
            raise
        finally:
            record["seconds"] = round(time.perf_counter() - started, 3)
            temporary = path.with_suffix(".part")
            temporary.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            os.replace(temporary, path)
        return record["response"]
