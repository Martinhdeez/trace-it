"""The span API (`core/events.py`), without a database: `_write` is captured."""

import asyncio

import logfire
import pytest
import requests
from sqlalchemy.exc import OperationalError

from app.core import events


def test_an_unreachable_database_is_not_retried_for_every_span(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts: list[int] = []

    def down():
        attempts.append(1)
        raise OperationalError("connect", {}, Exception("refused"))

    monkeypatch.setattr(events, "_engine", down)
    monkeypatch.setattr(events, "_unreachable_until", 0.0)
    for _ in range(3):
        with events.span("step"):
            pass
    assert len(attempts) == 1


@pytest.fixture
def written(monkeypatch: pytest.MonkeyPatch) -> list[list[dict]]:
    """Each local trace's rows, as `_write` would insert them."""
    batches: list[list[dict]] = []
    monkeypatch.setattr(events, "_write", batches.append)
    return batches


def leaf() -> None:
    with events.span("leaf"):
        pass


async def child(n: int) -> None:
    with events.span("child", n=n):
        await asyncio.sleep(0)
        await asyncio.to_thread(leaf)


async def test_children_nest_across_gather_and_threads(written: list) -> None:
    with events.span("root", process_id=3) as root:
        await asyncio.gather(child(1), child(2))

    [rows] = written  # one insert for the whole trace
    assert len(rows) == 5 and {r["trace_id"] for r in rows} == {root.trace_id}
    by_id = {r["span_id"]: r for r in rows}
    children = [r for r in rows if r["step"] == "child"]
    assert all(r["parent_id"] == root.span_id and r["process_id"] == 3 for r in children)
    leaves = [r for r in rows if r["step"] == "leaf"]
    assert sorted(by_id[r["parent_id"]]["data"]["n"] for r in leaves) == [1, 2]
    assert by_id[root.span_id]["parent_id"] is None
    assert by_id[root.span_id]["duration_ms"] >= 0

    # A background job continues the trace once the request's spans are written.
    with events.span("job", parent=root):
        pass
    [job] = written[1]
    assert (job["trace_id"], job["parent_id"], job["process_id"]) == (
        root.trace_id,
        root.span_id,
        3,
    )


def test_an_exception_marks_the_span_and_propagates(written: list) -> None:
    with pytest.raises(ValueError), events.span("fails", rule_id=1):
        raise ValueError("boom")

    [[row]] = written
    assert row["status"] == "error" and row["data"]["error"] == "ValueError: boom"
    assert row["rule_id"] == 1


def test_without_a_token_nothing_leaves_the_process(
    written: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LOGFIRE_TOKEN", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    sent: list = []
    monkeypatch.setattr(requests.Session, "send", lambda *args, **kwargs: sent.append(args))

    events.configure_observability()
    with events.span("probe") as span:
        pass
    logfire.force_flush()

    assert sent == []
    # Still real OpenTelemetry spans: our ids are theirs, so both layers show one tree.
    context = span.otel.get_span_context()
    assert context.is_valid and span.trace_id == f"{context.trace_id:032x}"
