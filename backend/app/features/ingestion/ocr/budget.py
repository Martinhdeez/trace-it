"""A shared deadline for queueing, retries, and remote extraction work."""

import time
from contextlib import contextmanager
from contextvars import ContextVar

from .errors import ProviderUnavailable

_deadline = ContextVar("extraction_deadline", default=None)


def remaining(limit):
    deadline = _deadline.get()
    seconds = min(limit, deadline - time.monotonic()) if deadline is not None else limit
    if seconds <= 0:
        raise ProviderUnavailable("Extraction time budget exhausted")
    return seconds


@contextmanager
def extraction_budget(seconds):
    existing = _deadline.get()
    deadline = time.monotonic() + seconds
    token = _deadline.set(min(existing, deadline) if existing is not None else deadline)
    try:
        yield
    finally:
        _deadline.reset(token)


@contextmanager
def acquired(lock, limit=600):
    if not lock.acquire(timeout=remaining(limit)):
        raise ProviderUnavailable("Extraction queue time budget exhausted")
    try:
        yield
    finally:
        lock.release()
