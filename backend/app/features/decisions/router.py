import json

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from app.core.database import Session
from app.features.decisions import service
from app.features.decisions.schemas import (
    EventOut,
    FindingOut,
    InstanceDetail,
    InstanceOut,
    ProcessSummary,
    ReprocessIn,
    ReprocessSummary,
    ResolveIn,
    RunSummary,
)
from app.features.users.dependencies import CurrentUser

router = APIRouter(tags=["decisions"])


@router.post(
    "/processes/{process_id}/run",
    operation_id="runProcess",
    summary="Decide every pending instance with the active rules",
)
async def run_process(process_id: int, session: Session) -> RunSummary:
    return await service.run(session, process_id)


@router.post(
    "/processes/{process_id}/reprocess",
    operation_id="reprocessProcess",
    summary="Decide the decided instances again with the current rules and sources",
    description="After a source resync, a corrected datum or a rule adopted later. Only a "
    "decision that changes is written, as a new engine row; the history stays. An instance "
    "a person decided last is never re-decided: a disagreement comes back in `conflicts`. "
    "`names` limits it to those instances; `dry_run=true` only reports.",
)
async def reprocess_process(
    process_id: int, session: Session, body: ReprocessIn | None = None, dry_run: bool = False
) -> ReprocessSummary:
    return await service.reprocess(session, process_id, body.names if body else None, dry_run)


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
    description="Every recorded step: `decision`, `resolution`, `ingest_document`, "
    "`compile_rule`, `normalize_norm`, `suggest_escalation`, `sync_source`, "
    "`sync_source_failed`. "
    "Filter with `step` and `instance_id`.",
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
    summary="Instances waiting for a person (by default, the escalated ones)",
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
    instance_id: int, body: ResolveIn, session: Session, user: CurrentUser
) -> InstanceDetail:
    return await service.resolve(session, instance_id, body, user)


@router.get(
    "/processes/{process_id}/export",
    operation_id="exportOutcomes",
    summary="outcomes.jsonl, one line per instance",
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
        409: {"description": "Some instance has no decision yet"},
    },
)
async def export_outcomes(process_id: int, session: Session) -> PlainTextResponse:
    body, duplicates = await service.export(session, process_id)
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
