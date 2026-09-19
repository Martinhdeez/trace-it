from datetime import datetime

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.database import Session
from app.features.traces import service
from app.features.traces.schemas import (
    AgentsMetrics,
    ExecutionMetrics,
    IngestionMetrics,
    InstanceTrace,
    Plane,
    PlaneHealth,
    ProcessMetrics,
    RuleTrace,
    SpanNode,
    SpanOut,
)

router = APIRouter(tags=["traces"])


@router.get(
    "/traces",
    operation_id="listSpans",
    summary="Recent spans, newest first",
    description="Every step the system took, as spans of the audit trail (ADR 0018). Filter by "
    "process, step name (`compile_rule`, `llm_run`, `run_process`, `evaluate_rule`, "
    "`sync_source`, `upload_document`...) or status (`ok`, `error`).",
)
async def list_spans(
    session: Session,
    process_id: int | None = None,
    name: str | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
) -> list[SpanOut]:
    return await service.list_spans(session, process_id, name, status, limit)


@router.get(
    "/traces/{trace_id}",
    operation_id="getTrace",
    summary="One trace as a tree of spans",
    responses={404: {"description": "No span has this trace id"}},
)
async def get_trace(trace_id: str, session: Session) -> list[SpanNode]:
    return await service.get_trace(session, trace_id)


@router.get(
    "/instances/{instance_id}/trace",
    operation_id="getInstanceTrace",
    summary="The journey of one instance: file, reading, symbols, decisions, people, export",
)
async def get_instance_trace(instance_id: int, session: Session) -> InstanceTrace:
    return await service.instance_trace(session, instance_id)


@router.get(
    "/rules/{rule_id}/trace",
    operation_id="getRuleTrace",
    summary="How a rule was produced (norm, tests, attempts, reviews, activation) and its "
    "runtime stats",
)
async def get_rule_trace(rule_id: int, session: Session) -> RuleTrace:
    return await service.rule_trace(session, rule_id)


@router.get(
    "/processes/{process_id}/metrics",
    operation_id="getProcessMetrics",
    summary="Aggregates of a process: runs, throughput, step durations, LLM tokens, outcomes",
    description="`steps` gives count, errors and p50/p95 duration per step type "
    "(`compile_rule` is the rule compile time, `evaluate_rule` one rule over a run); `llm` the "
    "calls, retries, errors and tokens by model and role. `providers` separates OCR provider "
    "attempts, network requests, journal replays, errors and reported tokens by provider, "
    "model and operation. Replayed tokens do not count as new usage. `since` keeps the spans "
    "and decisions from that moment on.",
)
async def get_process_metrics(
    process_id: int, session: Session, since: datetime | None = None
) -> ProcessMetrics:
    return await service.metrics(session, process_id, since)


PLANES_DOC = (
    "Three monitoring planes over the same spans (ADR 0018, `service.PLANES` maps every span "
    "name to one): `ingestion` (upload, store, extraction, native text, OCR, vision, "
    "workbook, source sync: files/s, pages, calls, cache hits, abstentions, provider "
    "attempts, network requests, replays and reported tokens), `agents` "
    "(normalizer, tester, compiler, reviewer and assistant LLM calls; compile, tests, "
    "impact, activation: tokens by model, role, rule, norm rule, use case and hour, "
    "fallbacks, truncations, compile success, norm to active), `execution` (runs, rules, "
    "decisions, reviews, people, exports: invoices/s, per-rule time, escalation causes, the "
    "human queue, time to resolution). Each has `steps` with count, errors, p50/p95. "
    "Provider token totals exclude journal replay and reflect reported usage, not billing. "
    "`since` keeps what happened from that moment on."
)
PlaneOut = IngestionMetrics | AgentsMetrics | ExecutionMetrics


@router.get(
    "/processes/{process_id}/metrics/{plane}",
    operation_id="getProcessPlaneMetrics",
    summary="One monitoring plane of a process: ingestion, agents or execution",
    description=PLANES_DOC,
)
async def get_process_plane_metrics(
    process_id: int, plane: Plane, session: Session, since: datetime | None = None
) -> PlaneOut:
    return await service.plane_metrics(session, plane, process_id, since)


@router.get(
    "/metrics/{plane}",
    operation_id="getPlaneMetrics",
    summary="One monitoring plane across every process",
    description=PLANES_DOC,
)
async def get_plane_metrics(
    plane: Plane, session: Session, since: datetime | None = None
) -> PlaneOut:
    return await service.plane_metrics(session, plane, None, since)


@router.get(
    "/health/planes",
    operation_id="getPlanesHealth",
    summary="Each plane now: ok, degraded or down",
    description="Over the last `TRACE_HEALTH_WINDOW_MINUTES`: `down` from "
    "`TRACE_HEALTH_DOWN_ERROR_RATE` of spans in error, `degraded` from "
    "`TRACE_HEALTH_DEGRADED_ERROR_RATE` or when the plane's p95 span duration passes "
    "`TRACE_HEALTH_P95_MS[plane]`. No spans in the window is `ok`.",
)
async def get_planes_health(session: Session) -> list[PlaneHealth]:
    return await service.health(session)


@router.get(
    "/events/stream",
    operation_id="streamEvents",
    summary="Every new span, live (server-sent events)",
    description="`text/event-stream`: one event per span as it is written, `event` is its "
    "plane, `id` its `events.id`, `data` a span as in `GET /traces`. `: ping` when nothing "
    "new came in the last second. Filter by `plane` and `process_id`; `after` replays from "
    "that id (default: only new spans).",
    response_class=StreamingResponse,
)
async def stream_events(
    plane: Plane | None = None, process_id: int | None = None, after: int | None = None
) -> StreamingResponse:
    return StreamingResponse(
        service.stream(plane, process_id, after),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
