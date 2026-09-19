"""A shared deadline for queueing, retries, and remote extraction work."""

import time
from contextlib import contextmanager
from contextvars import ContextVar

from .errors import ExtractionDeadlineExceeded

_deadline = ContextVar("extraction_deadline", default=None)


def remaining(limit):
    deadline = _deadline.get()
    seconds = min(limit, deadline - time.monotonic()) if deadline is not None else limit
    if seconds <= 0:
        raise ExtractionDeadlineExceeded("Extraction time budget exhausted; retry the document")
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
        raise ExtractionDeadlineExceeded(
            "Extraction queue time budget exhausted; retry the document"
        )
    try:
        yield
    finally:
        lock.release()
