"""Safe provider availability state shared by the bounded fallback chains."""

import threading
import time


class ProviderUnavailable(RuntimeError):
    pass


_cooldown_until: dict[tuple[str, str, str], float] = {}
_cooldown_lock = threading.Lock()


def provider_on_cooldown(provider: str, model: str, namespace: str) -> bool:
    with _cooldown_lock:
        active = _cooldown_until.get((namespace, provider, model), 0) > time.monotonic()
    if active:
        from app.core import events

        trace = events.current()
        if trace is not None:
            trace.set(provider_cooldown_skips=trace.data.get("provider_cooldown_skips", 0) + 1)
    return active


def note_provider_failure(
    provider: str, model: str, namespace: str, exc: ProviderUnavailable
) -> None:
    status = getattr(exc, "http_status_code", None)
    if status not in {402, 429, 500, 502, 503, 504}:
        return
    requested = getattr(exc, "retry_after_s", None)
    seconds = max(5, min(float(requested), 60)) if isinstance(requested, (int, float)) else 15
    with _cooldown_lock:
        _cooldown_until[(namespace, provider, model)] = time.monotonic() + seconds
