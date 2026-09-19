from datetime import datetime

from fastapi import APIRouter, Query

from app.core.database import Session
from app.features.traces import service
from app.features.traces.schemas import (
    InstanceTrace,
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
    "calls, retries, errors and tokens by model and role. Cost is counted in tokens. `since` "
    "keeps the spans and decisions from that moment on.",
)
async def get_process_metrics(
    process_id: int, session: Session, since: datetime | None = None
) -> ProcessMetrics:
    return await service.metrics(session, process_id, since)
