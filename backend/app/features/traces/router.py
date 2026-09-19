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
    "`sync_source`, `upload_document`...), status (`ok`, `error`), plane, time window "
    "(`since` <= start < `until`), rule, norm rule, use case, or a span's `model`, `role`, "
    "`agent` (the agents plane's `by_role` key), `provider` and `operation`. Every row of "
    "`/metrics/{plane}` carries its drill-down here as `traces`.",
)
async def list_spans(
    session: Session,
    process_id: int | None = None,
    name: str | None = None,
    status: str | None = None,
    plane: Plane | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    rule_id: int | None = None,
    norm_rule_id: int | None = None,
    use_case_id: int | None = None,
    model: str | None = None,
    role: str | None = None,
    agent: str | None = None,
    provider: str | None = None,
    operation: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
) -> list[SpanOut]:
    return await service.list_spans(
        session,
        process_id,
        name,
        status,
        limit,
        plane=plane,
        since=since,
        until=until,
        rule_id=rule_id,
        norm_rule_id=norm_rule_id,
        use_case_id=use_case_id,
        data={
            "model": model,
            "role": role,
            "agent": agent,
            "provider": provider,
            "operation": operation,
        },
    )


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
    "name to one), never mixed into one total (`docs/observability-dashboards.md`): "
    "`ingestion` (upload, store, extraction, native text, OCR, vision, workbook, source "
    "sync: files/s, pages, calls, cache hits, abstentions, and per provider the attempts, "
    "network requests, replays, tokens, `known_cost_usd` and `unpriced_requests`), `agents` "
    "(normalizer, tester, compiler, reviewer and assistant LLM calls; compile, tests, "
    "impact, activation: `total` and tokens and cost by model, role, rule, norm rule, use "
    "case and hour, fallbacks, truncations, compile success, norm to active), `execution` "
    "(runs, rules, decisions, reviews, people, exports: invoices/s, per-rule time, "
    "escalation causes, the human queue, time to resolution; 0 tokens by design). Each has "
    "`steps` with count, errors, p50/p95. Cost is USD where the model's price is known; "
    "`unpriced_requests` counts the rest, never read as 0. Every row's `traces` is its "
    "drill-down in `GET /traces`. Provider token totals exclude journal replay and reflect "
    "reported usage, not billing. `since` keeps what happened from that moment on."
)


def _plane_routes(plane: Plane, out: type) -> None:
    """`GET /metrics/{plane}` and `GET /processes/{id}/metrics/{plane}`, one typed response
    each, so the OpenAPI contract names every field of every plane."""
    name = plane.value.capitalize()

    async def of_process(process_id: int, session: Session, since: datetime | None = None):
        return await service.plane_metrics(session, plane, process_id, since)

    async def everywhere(session: Session, since: datetime | None = None):
        return await service.plane_metrics(session, plane, None, since)

    router.get(
        f"/processes/{{process_id}}/metrics/{plane.value}",
        operation_id=f"getProcess{name}Metrics",
        summary=f"The {plane.value} plane of a process",
        description=PLANES_DOC,
        response_model=out,
    )(of_process)
    router.get(
        f"/metrics/{plane.value}",
        operation_id=f"get{name}Metrics",
        summary=f"The {plane.value} plane across every process",
        description=PLANES_DOC,
        response_model=out,
    )(everywhere)


_plane_routes(Plane.ingestion, IngestionMetrics)
_plane_routes(Plane.agents, AgentsMetrics)
_plane_routes(Plane.execution, ExecutionMetrics)


@router.get(
    "/health/planes",
    operation_id="getPlanesHealth",
    summary="Each plane now: ok, degraded or down",
    description="Over the last `TRACE_HEALTH_WINDOW_MINUTES`: `down` from "
    "`TRACE_HEALTH_DOWN_ERROR_RATE` of spans in error, `degraded` from "
    "`TRACE_HEALTH_DEGRADED_ERROR_RATE` or when the plane's p95 span duration passes "
    "`TRACE_HEALTH_P95_MS[plane]`. No spans in the window, or fewer than "
    "`TRACE_HEALTH_MIN_SPANS` (reason `not enough data`), is `ok`.",
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
