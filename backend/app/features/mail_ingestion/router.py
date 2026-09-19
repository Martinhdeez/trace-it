from typing import Annotated

from fastapi import APIRouter, Header, Query, Request
from sqlalchemy import select

from app.common.exceptions import ConflictError
from app.core import events
from app.core.database import Session
from app.features.ingestion import process_service
from app.features.ingestion.process_router import Service
from app.features.processes.model import Process
from app.features.users.dependencies import CurrentUser, Manager
from app.features.versions.service import lock

from . import service
from .auth import MailIdentity
from .config import MailSettings
from .model import MailAccount, MailMessage
from .schemas import (
    AttachmentOut,
    ClaimedMessage,
    DiscoverIn,
    GatheringSettings,
    InitializeIn,
    MailFailureIn,
    MailOverview,
    MailState,
    ManifestIn,
    MessageOut,
)

router = APIRouter(tags=["mail ingestion"])
ROOT = "/mail-ingestion/{process_id}"
Lease = Annotated[str, Header(alias="X-Mail-Lease", min_length=48, max_length=48)]


@router.get("/processes/{process_id}/gathering", operation_id="getProcessGathering")
async def gathering(process_id: int, session: Session, user: CurrentUser) -> GatheringSettings:
    process = await process_service.require_process(session, process_id)
    process = await session.get(Process, process_id)
    return GatheringSettings(email=process.gathering_email)


@router.put("/processes/{process_id}/gathering", operation_id="setProcessGathering")
async def set_gathering(
    process_id: int,
    body: GatheringSettings,
    session: Session,
    user: Manager,
) -> GatheringSettings:
    from sqlalchemy import text

    # One mailbox assignment, serialized across processes, including the empty state.
    await session.execute(text("SELECT pg_advisory_xact_lock(716293401)"))
    process = await lock(session, process_id)
    if body.email and await session.scalar(
        select(Process.id).where(
            Process.gathering_email == body.email,
            Process.id != process_id,
        )
    ):
        raise ConflictError("This gathering email is already assigned to another process")
    account = await session.scalar(select(MailAccount).where(MailAccount.process_id == process_id))
    if account and account.state == "active" and body.email != process.gathering_email:
        raise ConflictError("Stop and halt the mailbox integration before changing its assignment")
    before = process.gathering_email
    process.gathering_email = body.email
    events.record(
        session,
        "configure_mail_gathering",
        process_id=process_id,
        data={"author": user.name, "before": before, "email": body.email},
    )
    await session.commit()
    return body


@router.get(ROOT, operation_id="getMailState")
async def state(account: MailIdentity) -> MailState:
    return MailState.model_validate(account)


@router.post(ROOT + "/initialize", operation_id="initializeMailCursor")
async def initialize(body: InitializeIn, session: Session, account: MailIdentity) -> MailState:
    return await service.initialize(session, account, body)


@router.post(ROOT + "/discover", operation_id="discoverMailMessages")
async def discover(body: DiscoverIn, session: Session, account: MailIdentity) -> MailState:
    return await service.discover(session, account, body)


@router.post(ROOT + "/poll-failure", operation_id="recordMailPollFailure")
async def poll_failure(body: MailFailureIn, session: Session, account: MailIdentity) -> MailState:
    return await service.poll_failure(session, account, body)


@router.post(ROOT + "/claim", operation_id="claimMailMessage")
async def claim(
    session: Session,
    account: MailIdentity,
    ready_only: bool = False,
) -> ClaimedMessage | None:
    return await service.claim(session, account, ready_only)


@router.put(ROOT + "/messages/{message_id}/manifest", operation_id="saveMailManifest")
async def manifest(
    message_id: int,
    body: ManifestIn,
    session: Session,
    account: MailIdentity,
    lease: Lease,
) -> MessageOut:
    message = await service.leased(session, account, message_id, lease)
    return await service.manifest(session, account, message, body)


@router.put(
    ROOT + "/messages/{message_id}/attachments/{attachment_id}", operation_id="importMailPDF"
)
async def import_pdf(
    message_id: int,
    attachment_id: int,
    request: Request,
    session: Session,
    account: MailIdentity,
    lease: Lease,
    extraction: Service,
) -> AttachmentOut:
    message = await service.leased(session, account, message_id, lease)
    row = await service.attachment(session, message, attachment_id)
    if row.state != "discovered":
        return AttachmentOut.model_validate(row)
    content = bytearray()
    limit = MailSettings().max_pdf_bytes
    async for chunk in request.stream():
        if len(content) + len(chunk) > limit:
            row.state, row.error = "failed", "size_limit"
            await session.commit()
            return AttachmentOut.model_validate(row)
        content.extend(chunk)
    return await service.import_pdf(session, account, message, row, bytes(content), extraction)


@router.post(
    ROOT + "/messages/{message_id}/attachments/{attachment_id}/failure",
    operation_id="rejectMailAttachment",
)
async def reject(
    message_id: int,
    attachment_id: int,
    body: MailFailureIn,
    session: Session,
    account: MailIdentity,
    lease: Lease,
) -> AttachmentOut:
    message = await service.leased(session, account, message_id, lease)
    row = await service.attachment(session, message, attachment_id)
    if row.state == "discovered":
        row.state, row.error = "failed", body.error
    await session.commit()
    return AttachmentOut.model_validate(row)


@router.post(ROOT + "/messages/{message_id}/finish", operation_id="evaluateMailMessage")
async def finish(
    message_id: int,
    session: Session,
    account: MailIdentity,
    lease: Lease,
) -> MessageOut:
    message = await service.leased(session, account, message_id, lease)
    return await service.finish(session, account, message, lease)


@router.post(ROOT + "/messages/{message_id}/failure", operation_id="recordMailMessageFailure")
async def fail(
    message_id: int,
    body: MailFailureIn,
    session: Session,
    account: MailIdentity,
    lease: Lease,
) -> MessageOut:
    message = await service.leased(session, account, message_id, lease)
    return await service.fail_message(session, message, body)


@router.get("/processes/{process_id}/mail-ingestion", operation_id="getMailOverview")
async def overview(
    process_id: int,
    session: Session,
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> MailOverview:
    account = await session.scalar(select(MailAccount).where(MailAccount.process_id == process_id))
    messages = (
        []
        if account is None
        else await session.scalars(
            select(MailMessage)
            .where(MailMessage.account_id == account.id)
            .order_by(MailMessage.id.desc())
            .limit(limit)
        )
    )
    return MailOverview(
        account=MailState.model_validate(account) if account else None,
        messages=[await service.message_out(session, message) for message in messages],
    )
