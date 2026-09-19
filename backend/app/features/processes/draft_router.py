from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from sqlalchemy import select

from app.core.database import Session
from app.features.processes import drafts
from app.features.processes.draft_schemas import (
    DraftOut,
    DraftStart,
    MessageIn,
    ReviewIn,
    RevisionIn,
)
from app.features.processes.model import DraftRevision, ProcessDraft
from app.features.users.dependencies import CurrentUser

router = APIRouter(prefix="/process-drafts", tags=["process discovery"])


@router.get("", operation_id="listProcessDrafts")
async def list_drafts(session: Session, user: CurrentUser) -> list[dict]:
    drafts.manager(user)
    rows = await session.execute(
        select(ProcessDraft, DraftRevision)
        .join(
            DraftRevision,
            (DraftRevision.draft_id == ProcessDraft.id)
            & (DraftRevision.number == ProcessDraft.revision),
        )
        .order_by(ProcessDraft.id.desc())
    )
    return [
        {
            "id": d.id,
            "name": r.data["plan"]["name"],
            "revision": d.revision,
            "process_id": d.process_id,
            "published_process_id": d.published_process_id,
        }
        for d, r in rows
    ]


@router.post("", operation_id="startProcessDraft", status_code=201)
async def start(body: DraftStart, session: Session, user: CurrentUser) -> DraftOut:
    return await drafts.start(session, body, user)


@router.get("/{draft_id}", operation_id="getProcessDraft")
async def get(draft_id: int, session: Session, user: CurrentUser) -> DraftOut:
    drafts.manager(user)
    return await drafts.output(session, draft_id)


@router.get("/{draft_id}/revisions", operation_id="getProcessDraftHistory")
async def history(draft_id: int, session: Session, user: CurrentUser) -> list[dict]:
    drafts.manager(user)
    await drafts.read(session, draft_id)
    rows = await session.scalars(
        select(DraftRevision)
        .where(DraftRevision.draft_id == draft_id)
        .order_by(DraftRevision.number)
    )
    return [
        {
            "revision": r.number,
            "author_id": r.author_id,
            "created_at": r.created_at,
            "plan": r.data["plan"],
            "reviews": r.data["reviews"],
            "messages": r.data["messages"],
        }
        for r in rows
    ]


@router.post("/{draft_id}/messages", operation_id="messageProcessDraft")
async def message(draft_id: int, body: MessageIn, session: Session, user: CurrentUser) -> DraftOut:
    return await drafts.message(session, draft_id, body, user)


@router.post("/{draft_id}/workbooks", operation_id="uploadDraftWorkbook")
async def workbook(
    draft_id: int,
    session: Session,
    user: CurrentUser,
    revision: Annotated[int, Form()],
    file: Annotated[UploadFile, File()],
) -> DraftOut:
    return await drafts.upload(
        session,
        draft_id,
        revision,
        file.filename or "workbook.xlsx",
        await file.read(20 * 1024 * 1024 + 1),
        user,
    )


@router.post("/{draft_id}/sources/{name}/sync", operation_id="syncDraftSource")
async def sync(
    draft_id: int, name: str, body: RevisionIn, session: Session, user: CurrentUser
) -> DraftOut:
    return await drafts.sync(session, draft_id, body.revision, name, user)


@router.post("/{draft_id}/reviews", operation_id="reviewDraftProposal")
async def review(draft_id: int, body: ReviewIn, session: Session, user: CurrentUser) -> DraftOut:
    return await drafts.review(session, draft_id, body, user)


@router.post("/{draft_id}/prepare", operation_id="prepareProcessDraft")
async def prepare(draft_id: int, body: RevisionIn, session: Session, user: CurrentUser) -> DraftOut:
    return await drafts.prepare(session, draft_id, body.revision, user)


@router.post("/{draft_id}/publish", operation_id="publishProcessDraft")
async def publish(draft_id: int, body: RevisionIn, session: Session, user: CurrentUser) -> DraftOut:
    return await drafts.publish(session, draft_id, body.revision, user)
