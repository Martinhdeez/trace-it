from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from sqlalchemy import select

from app.core.database import Session
from app.features.processes import drafts
from app.features.processes.draft_schemas import (
    DiscoveryDraftOut,
    DiscoveryRevisionOut,
    DiscoverySessionSummary,
    DraftStart,
    ExecutionIn,
    MessageIn,
    ReviewIn,
    RevisionIn,
)
from app.features.processes.model import DiscoveryRevision, DiscoverySession
from app.features.users.dependencies import CurrentUser

router = APIRouter(prefix="/process-drafts", tags=["process discovery"])


@router.get("", operation_id="listDiscoverySessions")
async def list_drafts(session: Session, user: CurrentUser) -> list[DiscoverySessionSummary]:
    drafts.manager(user)
    rows = await session.execute(
        select(DiscoverySession, DiscoveryRevision)
        .join(
            DiscoveryRevision,
            (DiscoveryRevision.draft_id == DiscoverySession.id)
            & (DiscoveryRevision.number == DiscoverySession.revision),
        )
        .order_by(DiscoverySession.id.desc())
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


@router.post("", operation_id="startDiscoverySession", status_code=201)
async def start(body: DraftStart, session: Session, user: CurrentUser) -> DiscoveryDraftOut:
    return await drafts.start(session, body, user)


@router.get("/{draft_id}", operation_id="getDiscoverySession")
async def get(draft_id: int, session: Session, user: CurrentUser) -> DiscoveryDraftOut:
    drafts.manager(user)
    return await drafts.output(session, draft_id)


@router.get("/{draft_id}/revisions", operation_id="getDiscoverySessionHistory")
async def history(draft_id: int, session: Session, user: CurrentUser) -> list[DiscoveryRevisionOut]:
    drafts.manager(user)
    await drafts.read(session, draft_id)
    rows = await session.scalars(
        select(DiscoveryRevision)
        .where(DiscoveryRevision.draft_id == draft_id)
        .order_by(DiscoveryRevision.number)
    )
    return [
        {
            "revision": r.number,
            "author_id": r.author_id,
            "created_at": r.created_at,
            "plan": r.data["plan"],
            "reviews": r.data["reviews"],
            "messages": r.data["messages"],
            "preview": r.data.get("preview"),
            "published_rule_ids": r.data.get("published_rule_ids", []),
            "retired_rule_ids": r.data.get("retired_rule_ids", []),
        }
        for r in rows
    ]


@router.post("/{draft_id}/messages", operation_id="messageDiscoverySession")
async def message(
    draft_id: int, body: MessageIn, session: Session, user: CurrentUser
) -> DiscoveryDraftOut:
    return await drafts.message(session, draft_id, body, user)


@router.post("/{draft_id}/evidence", operation_id="uploadDraftEvidence")
@router.post(
    "/{draft_id}/workbooks",
    operation_id="uploadDraftWorkbook",
    deprecated=True,
)
async def evidence_asset(
    draft_id: int,
    session: Session,
    user: CurrentUser,
    revision: Annotated[int, Form()],
    file: Annotated[UploadFile, File()],
) -> DiscoveryDraftOut:
    return await drafts.upload(
        session,
        draft_id,
        revision,
        file.filename or "evidence.xlsx",
        await file.read(20 * 1024 * 1024 + 1),
        user,
    )


@router.post("/{draft_id}/sources/{name}/sync", operation_id="syncDraftSource")
async def sync(
    draft_id: int, name: str, body: RevisionIn, session: Session, user: CurrentUser
) -> DiscoveryDraftOut:
    return await drafts.sync(session, draft_id, body.revision, name, user)


@router.post("/{draft_id}/reviews", operation_id="reviewDraftProposal")
async def review(
    draft_id: int, body: ReviewIn, session: Session, user: CurrentUser
) -> DiscoveryDraftOut:
    return await drafts.review(session, draft_id, body, user)


@router.post("/{draft_id}/prepare", operation_id="prepareDiscoverySession")
async def prepare(
    draft_id: int, body: RevisionIn, session: Session, user: CurrentUser
) -> DiscoveryDraftOut:
    return await drafts.prepare(session, draft_id, body.revision, user)


@router.post("/{draft_id}/publish", operation_id="publishDiscoverySession")
async def publish(
    draft_id: int, body: RevisionIn, session: Session, user: CurrentUser
) -> DiscoveryDraftOut:
    return await drafts.publish(session, draft_id, body.revision, user)


@router.put("/{draft_id}/execution", operation_id="configureDiscoveryExecution")
async def configure_execution(
    draft_id: int, body: ExecutionIn, session: Session, user: CurrentUser
) -> DiscoveryDraftOut:
    return await drafts.configure_execution(session, draft_id, body, user)
