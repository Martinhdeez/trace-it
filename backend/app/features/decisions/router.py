import json

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from app.core.database import Session
from app.features.decisions import runs, service
from app.features.decisions.schemas import (
    EventOut,
    FindingOut,
    InstanceDetail,
    InstanceOut,
    ProcessSummary,
    ReprocessIn,
    ReprocessSummary,
    ResolveIn,
    RunDetail,
    RunIn,
    RunOut,
    RunSummary,
)
from app.features.users.dependencies import Manager

router = APIRouter(tags=["decisions"])


@router.post(
    "/processes/{process_id}/run",
    operation_id="runProcess",
    summary="Decide every pending instance with the active rules",
    description="Syncs the process's live sources first; a source that fails is down for "
    "this run and listed in `down_sources`, as is a source a rule reads that was never "
    "loaded (ADR 0028).",
    response_model_exclude_defaults=True,
)
async def run_process(
    process_id: int, session: Session, user: Manager, body: RunIn | None = None
) -> RunSummary:
    return await service.run(
        session,
        process_id,
        author=user.name,
        instance_ids=body.instance_ids if body else None,
        idempotency_key=f"user:{user.id}:{body.idempotency_key}"
        if body and body.idempotency_key
        else None,
    )


@router.post(
    "/processes/{process_id}/reprocess",
    operation_id="reprocessProcess",
    summary="Decide the decided instances again with the current rules and sources",
    description="After a source resync, a corrected datum or a rule adopted later. Only a "
    "decision that changes is written, as a new engine row; the history stays. An instance "
    "a person decided last or that awaits review is never replaced: a disagreement comes "
    "back in `conflicts`. `names` limits it to those instances. `dry_run=true` compares only "
    "engine outcomes, with no reviewer calls. New engine decisions receive optional reviews. "
    "Like a run, it syncs the live sources first, except a dry run (ADR 0028).",
    response_model_exclude_defaults=True,
)
async def reprocess_process(
    process_id: int,
    session: Session,
    user: Manager,
    body: ReprocessIn | None = None,
    dry_run: bool = False,
) -> ReprocessSummary:
    names = body.names if body else None
    return await service.reprocess(session, process_id, names, dry_run, author=user.name)


@router.get(
    "/processes/{process_id}/runs",
    operation_id="listRuns",
    summary="Run history, newest first: each run and reprocess with its outcome",
    description="One entry per stored execution: when, who, the process version and rules "
    "hash, the engine's outcome per decision type for every instance it evaluated, the "
    "escalations and their reason codes, `down_sources` and the `trace_id`. `by_decision` "
    "and `escalated` cover every evaluated instance, so a rerun of the same invoices "
    "compares with the run before it; `decided` counts only the decisions it appended.",
)
async def list_runs(
    process_id: int, session: Session, limit: int = Query(50, ge=1, le=500)
) -> list[RunOut]:
    return await runs.list_runs(session, process_id, limit)


@router.get(
    "/runs/{run_id}",
    operation_id="getRun",
    summary="One past run with the decisions it appended, read-only",
)
async def get_run(run_id: int, session: Session) -> RunDetail:
    return await runs.get_run(session, run_id)


@router.get(
    "/processes/{process_id}/summary",
    operation_id="getProcessSummary",
    summary="The numbers of a process page: instances, decisions, queue, rules, sources",
)
async def get_summary(process_id: int, session: Session) -> ProcessSummary:
    return await service.summary(session, process_id)


@router.get(
    "/processes/{process_id}/instances",
    operation_id="listInstances",
    summary="Instances with their latest decision, oldest first",
    description="`status` is PENDING or DECIDED; `decision` filters on the latest decision; "
    "`q` is a case-insensitive match on the name.",
)
async def list_instances(
    process_id: int,
    session: Session,
    status: str | None = None,
    decision: str | None = None,
    q: str | None = None,
) -> list[InstanceOut]:
    return await service.list_instances(session, process_id, status, decision, q)


@router.get(
    "/processes/{process_id}/events",
    operation_id="listEvents",
    summary="The trace of a process, newest first",
    description="Every recorded step (span, ADR 0018): `decision`, `resolution`, "
    "`ingest_document`, `upload_document`, `run_process`, `evaluate_rule`, `compile_rule`, "
    "`llm_run`, `normalize_norm`, `suggest_escalation`, `sync_source`, `export_outcomes`... "
    "A failed step has `status: error`. Filter with `step` and `instance_id`; "
    "`GET /traces/{trace_id}` gives the tree a step belongs to.",
)
async def list_events(
    process_id: int,
    session: Session,
    step: str | None = None,
    instance_id: int | None = None,
    limit: int = Query(200, ge=1, le=2000),
) -> list[EventOut]:
    return await service.list_events(session, process_id, step, instance_id, limit)


@router.get(
    "/processes/{process_id}/queue",
    operation_id="getQueue",
    summary="Instances waiting for a person: escalations and reviewer disagreements",
)
async def get_queue(
    process_id: int, session: Session, type: str | None = None
) -> list[InstanceOut]:
    return await service.queue(session, process_id, type)


@router.get(
    "/instances/{instance_id}",
    operation_id="getInstance",
    summary="An instance with its symbols, decision history and trace",
)
async def get_instance(instance_id: int, session: Session) -> InstanceDetail:
    return await service.get_instance(session, instance_id)


@router.post(
    "/instances/{instance_id}/resolve",
    operation_id="resolveInstance",
    summary="A person decides. Adds a decision, never edits the engine's",
    responses={409: {"description": "Not a decision type of this process"}},
)
async def resolve_instance(
    instance_id: int, body: ResolveIn, session: Session, user: Manager
) -> InstanceDetail:
    return await service.resolve(session, instance_id, body, user)


@router.get(
    "/processes/{process_id}/export",
    operation_id="exportOutcomes",
    summary="outcomes.jsonl, one line per instance",
    description="`file_id` and `result` come first on every line. `trace=true` adds a "
    "`trace_url`: the console screen with that case's trace. `full=true` writes the whole "
    "trace inline (`reason_code`, `reason`, `decided_by`, `decided_at`, `process_version`, "
    "`rules_hash`, `rules_fired`, `evidence`, `sources_read`, `trace_id`, `trace_url`), "
    "leaving out what has no data; a person's later resolution is then the exported one.",
    response_class=PlainTextResponse,
    responses={
        200: {
            "content": {"application/x-ndjson": {}},
            "headers": {
                "X-Duplicate-Names": {
                    "description": "JSON list of names shared by several instances; "
                    "only the most recent one is exported",
                    "schema": {"type": "string"},
                }
            },
        },
        409: {"description": "An instance has no exportable outcome or is awaiting human review"},
    },
)
async def export_outcomes(
    process_id: int, session: Session, trace: bool = False, full: bool = False
) -> PlainTextResponse:
    body, duplicates = await service.export(session, process_id, trace=trace, full=full)
    # JSON in ASCII: a header value cannot carry every character a file name can.
    headers = {"X-Duplicate-Names": json.dumps(duplicates)} if duplicates else None
    return PlainTextResponse(body, media_type="application/x-ndjson", headers=headers)


@router.get(
    "/processes/{process_id}/findings",
    operation_id="listFindings",
    summary="Past decisions a later rule says were wrong",
)
async def list_findings(process_id: int, session: Session) -> list[FindingOut]:
    return await service.list_findings(session, process_id)
