from fastapi import APIRouter
from sqlalchemy import select

from app.common.exceptions import NotFoundError, PermissionDeniedError
from app.core.database import Session
from app.features.users.dependencies import CurrentUser
from app.features.versions import execution, service
from app.features.versions.model import ProcessVersion
from app.features.versions.schemas import DraftIn, DraftOut, PublishIn, VersionOut

router = APIRouter(tags=["process versions"])


def manager(user):
    if user.role != "manager":
        raise PermissionDeniedError("Only a manager can prepare or publish process versions")


def out(schema, row):
    return schema.model_validate(row, from_attributes=True)


@router.get("/processes/{process_id}/versions")
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


@router.get("/process-versions/{version_id}")
async def version(version_id: int, session: Session) -> VersionOut:
    row = await session.get(ProcessVersion, version_id)
    if row is None:
        raise NotFoundError("Process version does not exist")
    return out(VersionOut, row)


@router.get("/processes/{process_id}/draft")
async def draft(process_id: int, session: Session, user: CurrentUser) -> DraftOut:
    manager(user)
    return out(DraftOut, await service.get_draft(session, process_id))


@router.put("/processes/{process_id}/draft")
async def edit(process_id: int, body: DraftIn, session: Session, user: CurrentUser) -> DraftOut:
    manager(user)
    return out(DraftOut, await service.edit(session, process_id, body, user.name))


@router.post("/processes/{process_id}/draft/validate")
async def validate(process_id: int, session: Session, user: CurrentUser) -> DraftOut:
    manager(user)
    return out(DraftOut, await service.validate(session, process_id))


@router.post("/processes/{process_id}/draft/publish", status_code=201)
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


@router.post("/decisions/{decision_id}/replay")
async def replay(decision_id: int, session: Session, user: CurrentUser) -> dict:
    manager(user)
    return await execution.replay(session, decision_id)


@router.delete("/processes/{process_id}/draft", status_code=204)
async def discard(process_id: int, revision: int, session: Session, user: CurrentUser):
    from app.common.exceptions import ConflictError

    manager(user)
    await service.lock(session, process_id)
    draft = await service.get_draft(session, process_id)
    if draft.revision != revision:
        raise ConflictError("The draft changed; fetch it again")
    await session.delete(draft)
    await session.commit()
