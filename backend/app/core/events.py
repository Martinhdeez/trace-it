"""The trace of every step (ADR 0018): what went in, what came out, how long, how many tokens.

Two layers see the same tree. The `events` table is the audit, the source of truth: one row
per span, with its trace, parent, duration, status, data and links to the instance, process,
rule and norm rule. Each span is also an OpenTelemetry span through the Logfire SDK, for live
monitoring (Logfire cloud with `LOGFIRE_TOKEN`, or any OTLP backend such as a local Phoenix
with `OTEL_EXPORTER_OTLP_ENDPOINT`; neither set, nothing leaves the process).

    with events.span("compile_rule", rule_id=7) as s:
        ...
        s.set(valid=True)

The current span lives in a context variable, so children attach to it by themselves across
`await`, `asyncio.gather` and `asyncio.to_thread`. A background job that outlives the request
continues its trace with `span(..., parent=...)`. A trace's rows are written together, in one
insert, when its outermost span in this context ends.
"""

import json
import logging
import os
import secrets
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import Any

import logfire
from opentelemetry import context as otel_context
from opentelemetry import trace as otel_trace
from sqlalchemy import BigInteger, DateTime, create_engine, insert
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.database import Base, created_at, engine

logger = logging.getLogger(__name__)

LINKS = ("instance_id", "process_id", "rule_id", "norm_rule_id")
INHERITED = ("process_id", "rule_id", "norm_rule_id")  # a child belongs to its parent's


class Event(Base):
    """One span. No foreign keys: the audit never blocks the transaction it describes."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    trace_id: Mapped[str] = mapped_column(index=True)
    span_id: Mapped[str]
    parent_id: Mapped[str | None]
    step: Mapped[str]  # the span's name
    status: Mapped[str]  # "ok" or "error"
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_ms: Mapped[int | None]
    data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    instance_id: Mapped[int | None] = mapped_column(index=True)
    process_id: Mapped[int | None] = mapped_column(index=True)
    rule_id: Mapped[int | None] = mapped_column(index=True)
    norm_rule_id: Mapped[int | None] = mapped_column(index=True)
    created_at: Mapped[created_at]


@dataclass
class Span:
    step: str
    trace_id: str
    span_id: str
    parent_id: str | None
    rows: list[dict[str, Any]]  # the local trace's finished spans, written together
    otel: Any  # the OpenTelemetry span
    logfire_span: Any
    links: dict[str, int | None] = field(default_factory=lambda: dict.fromkeys(LINKS))
    data: dict[str, Any] = field(default_factory=dict)
    status: str = "ok"
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def set(self, **values: Any) -> None:
        """Add data or links (`instance_id=`, `process_id=`, ...) to the span."""
        for key, value in values.items():
            (self.links if key in LINKS else self.data)[key] = value
        self.logfire_span.set_attributes({k: v for k, v in values.items() if v is not None})


_current: ContextVar[Span | None] = ContextVar("span", default=None)


def current() -> Span | None:
    return _current.get()


@contextmanager
def span(step: str, *, parent: Span | None = None, **values: Any) -> Iterator[Span]:
    """A span named `step` under the current one (or `parent`). Keyword arguments are its
    links and data. An exception marks it `error` with the message, and propagates."""
    inherited = _current.get()
    parent = parent or inherited
    attached = None
    if parent is not None and parent is not inherited:  # a job continuing another trace
        attached = otel_context.attach(otel_trace.set_span_in_context(parent.otel))
    try:
        with logfire.span(step) as lf:
            otel = otel_trace.get_current_span()
            ids = otel.get_span_context()
            s = Span(
                step,
                trace_id=parent.trace_id
                if parent
                else f"{ids.trace_id:032x}"
                if ids.is_valid
                else secrets.token_hex(16),
                span_id=f"{ids.span_id:016x}" if ids.is_valid else secrets.token_hex(8),
                parent_id=parent.span_id if parent else None,
                rows=inherited.rows if inherited else [],
                otel=otel,
                logfire_span=lf,
            )
            if parent:
                s.links.update({k: parent.links[k] for k in INHERITED})
            s.set(**values)
            token = _current.set(s)
            start = time.perf_counter()
            try:
                yield s
            except BaseException as e:
                s.status = "error"
                s.data["error"] = f"{type(e).__name__}: {e}"[:1000]
                raise
            finally:
                _current.reset(token)
                s.rows.append(_row(s, int((time.perf_counter() - start) * 1000)))
    finally:
        if attached is not None:
            otel_context.detach(attached)
        if inherited is None:
            _write(s.rows)


def _row(s: Span, duration_ms: int) -> dict[str, Any]:
    return {
        "trace_id": s.trace_id,
        "span_id": s.span_id,
        "parent_id": s.parent_id,
        "step": s.step,
        "status": s.status,
        "started_at": s.started_at,
        "duration_ms": duration_ms,
        "data": s.data or None,
        **s.links,
    }


@cache
def _engine():
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        json_serializer=lambda o: json.dumps(o, default=str, ensure_ascii=False),
    )


def _write(rows: list[dict[str, Any]]) -> None:
    """One insert per local trace. Losing the audit of a step must not fail the step."""
    # ponytail: a synchronous insert on the event loop (~ms per trace, not per span); a
    # queue and a writer thread if traces ever get hot.
    try:
        with _engine().begin() as connection:
            connection.execute(insert(Event), rows)
    except Exception:  # noqa: BLE001 - database down: the step itself already happened
        logger.exception("Could not write %d spans", len(rows))


def record(
    session: AsyncSession,
    step: str,
    *,
    process_id: int | None = None,
    instance_id: int | None = None,
    data: dict[str, Any] | None = None,
    duration_ms: int | None = None,
) -> None:
    """A point in the current trace, saved with the caller's commit: it belongs to the
    caller's transaction (a decision and its event are written together)."""
    parent = _current.get()
    links = {k: parent.links[k] for k in INHERITED} if parent else {}
    links["process_id"] = process_id or links.get("process_id")
    session.add(
        Event(
            trace_id=parent.trace_id if parent else secrets.token_hex(16),
            span_id=secrets.token_hex(8),
            parent_id=parent.span_id if parent else None,
            step=step,
            status="ok",
            started_at=datetime.now(UTC) - timedelta(milliseconds=duration_ms or 0),
            duration_ms=duration_ms,
            data=data,
            instance_id=instance_id,
            **links,
        )
    )


def configure_observability() -> None:
    """OpenTelemetry through the Logfire SDK. Sends to Logfire only with `LOGFIRE_TOKEN`, and
    to any OTLP backend named by `OTEL_EXPORTER_OTLP_ENDPOINT` (a local Phoenix)."""
    # A plain OTLP backend such as Phoenix takes traces only: it answers 405 to metrics and
    # logs. The standard variables still override this.
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        os.environ.setdefault("OTEL_METRICS_EXPORTER", "none")
        os.environ.setdefault("OTEL_LOGS_EXPORTER", "none")
    logfire.configure(
        send_to_logfire="if-token-present",
        service_name="trace-it",
        console=False,
        inspect_arguments=False,
    )
    logfire.instrument_pydantic_ai()
    logfire.instrument_httpx()
    logfire.instrument_sqlalchemy(engine=engine.sync_engine)
