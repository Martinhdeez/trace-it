import json

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.core.database import Session
from app.features.decisions import service
from app.features.decisions.schemas import (
    FindingOut,
    InstanceDetail,
    InstanceOut,
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


@router.get("/processes/{process_id}/instances", operation_id="listInstances", summary="Instances")
async def list_instances(
    process_id: int, session: Session, status: str | None = None
) -> list[InstanceOut]:
    return await service.list_instances(session, process_id, status)


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
