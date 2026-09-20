from fastapi import APIRouter
from sqlalchemy import select

from app.common.exceptions import NotFoundError, PermissionDeniedError
from app.core.database import Session
from app.features.users.dependencies import CurrentUser
from app.features.versions import execution, service
from app.features.versions.model import ProcessVersion
from app.features.versions.schemas import (
    DraftIn,
    ExecutionOut,
    PublishIn,
    ReplayOut,
    VersionDraftOut,
    VersionOut,
)

router = APIRouter(tags=["process versions"])


def manager(user):
    if user.role != "manager":
        raise PermissionDeniedError("Only a manager can prepare or publish process versions")


def out(schema, row):
    return schema.model_validate(row, from_attributes=True)


@router.get("/processes/{process_id}/versions", operation_id="listProcessVersions")
async def versions(process_id: int, session: Session) -> list[VersionOut]:
    await service.active(session, process_id, required=False)
    return [
        out(VersionOut, v)
        for v in await session.scalars(
            select(ProcessVersion)
            .where(ProcessVersion.process_id == process_id)
            .order_by(ProcessVersion.number.desc())
        )
    ]


@router.get("/process-versions/{version_id}", operation_id="getProcessVersion")
async def version(version_id: int, session: Session) -> VersionOut:
    row = await session.get(ProcessVersion, version_id)
    if row is None:
        raise NotFoundError("Process version does not exist")
    return out(VersionOut, row)


@router.get("/processes/{process_id}/draft", operation_id="getProcessDraft")
async def draft(process_id: int, session: Session, user: CurrentUser) -> VersionDraftOut:
    manager(user)
    return out(VersionDraftOut, await service.get_draft(session, process_id))


@router.post("/process-versions/{version_id}/backtest", operation_id="backtestProcessVersion")
async def backtest(version_id: int, session: Session, user: CurrentUser) -> dict:
    """Compare published rules with saved cases and the latest loaded source snapshots."""
    manager(user)
    row = await session.get(ProcessVersion, version_id)
    if row is None:
        raise NotFoundError("Process version does not exist")
    from app.core import events
    from app.features.versions import configuration

    inputs = await execution.capture(session, row.process_id)
    with events.span("backtest_process_version", process_id=row.process_id, author=user.name):
        report = await service.inspect(session, row.snapshot, inputs)
    result = {
        **report,
        "version_id": row.id,
        "snapshot_hash": row.content_hash,
        "inputs_hash": configuration.digest(inputs),
    }
    return {**result, "hash": configuration.digest(result)}


@router.put("/processes/{process_id}/draft", operation_id="editProcessDraft")
async def edit(
    process_id: int, body: DraftIn, session: Session, user: CurrentUser
) -> VersionDraftOut:
    manager(user)
    return out(VersionDraftOut, await service.edit(session, process_id, body, user.name))


@router.post("/processes/{process_id}/draft/validate", operation_id="validateProcessDraft")
async def validate(process_id: int, session: Session, user: CurrentUser) -> VersionDraftOut:
    manager(user)
    return out(VersionDraftOut, await service.validate(session, process_id, user.name))


@router.post(
    "/processes/{process_id}/draft/publish", status_code=201, operation_id="publishProcessDraft"
)
async def publish(
    process_id: int, body: PublishIn, session: Session, user: CurrentUser
) -> VersionOut:
    manager(user)
    return out(
        VersionOut,
        await service.publish(
            session, process_id, body.revision, body.validation_hash, user.name, body.reason
        ),
    )


@router.post("/decisions/{decision_id}/replay", operation_id="replayDecision")
async def replay(decision_id: int, session: Session, user: CurrentUser) -> ReplayOut:
    manager(user)
    return await execution.replay(session, decision_id)


@router.delete("/processes/{process_id}/draft", status_code=204, operation_id="discardProcessDraft")
async def discard(process_id: int, revision: int, session: Session, user: CurrentUser):
    from app.common.exceptions import ConflictError

    manager(user)
    await service.lock(session, process_id)
    draft = await service.get_draft(session, process_id)
    if draft.revision != revision:
        raise ConflictError("The draft changed; fetch it again")
    await session.delete(draft)
    await session.commit()


@router.get("/processes/{process_id}/execution", operation_id="getExecutionSettings")
async def execution_settings(process_id: int, session: Session, user: CurrentUser) -> ExecutionOut:
    """Editable values and preset previews; reading never creates a draft."""
    from app.features.processes import execution as choices
    from app.features.versions import configuration
    from app.features.versions.model import ProcessDraft

    manager(user)
    version = await service.active(session, process_id, required=False)
    draft = await session.get(ProcessDraft, process_id)
    snapshot = (
        draft.snapshot
        if draft
        else version.snapshot
        if version
        else (await configuration.workspace(session, process_id))
    )
    current = choices.read(snapshot)
    presets = {}
    for name in choices.PRESETS:
        try:
            presets[name] = {"settings": choices.preset(current, name).model_dump(mode="json")}
        except (ValueError, TypeError, KeyError) as error:
            presets[name] = {"error": str(error)}
    return {
        "settings": current.model_dump(mode="json"),
        "revision": draft.revision if draft else None,
        "version_id": version.id if version else None,
        "presets": presets,
        "decision_review": snapshot["process"].get("decision_review"),
    }
