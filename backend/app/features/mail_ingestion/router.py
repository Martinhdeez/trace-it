from typing import Annotated

from fastapi import APIRouter, Header, Query, Request
from sqlalchemy import select

from app.common.exceptions import ConflictError
from app.core import events
from app.core.database import Session
from app.core.events import Event
from app.features.ingestion import process_service
from app.features.ingestion.process_router import Service
from app.features.processes.model import Process
from app.features.users.dependencies import CurrentUser, Manager
from app.features.versions.service import lock

from . import activity, service
from .auth import MailIdentity
from .config import MailSettings
from .model import MailAccount, MailActivity, MailMessage
from .schemas import (
    ActivityOut,
    AttachmentOut,
    ClaimedMessage,
    DiscoverIn,
    GatheringSettings,
    HeartbeatIn,
    InitializeIn,
    LegacyMailAudit,
    MailActivityFeed,
    MailFailureIn,
    MailHistory,
    MailOverview,
    MailState,
    ManifestIn,
    MessageOut,
    ReadActivityIn,
    RetryAttachmentIn,
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


@router.post(ROOT + "/heartbeat", operation_id="heartbeatMailWorker")
async def heartbeat(body: HeartbeatIn, session: Session, account: MailIdentity) -> MailState:
    account.heartbeat_at, account.worker_phase = service.now(), body.phase
    await session.commit()
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
    if row.state not in ("discovered", "reading"):
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
    ROOT + "/messages/{message_id}/attachments/{attachment_id}/reading",
    operation_id="startMailAttachmentReading",
)
async def reading(
    message_id: int, attachment_id: int, session: Session, account: MailIdentity, lease: Lease
) -> AttachmentOut:
    message = await service.leased(session, account, message_id, lease)
    row = await service.attachment(session, message, attachment_id)
    if row.state == "discovered":
        row.state, row.reading_at = "reading", service.now()
        activity.record(session, account, message, "reading", row, original_name=row.original_name)
        await session.commit()
    return AttachmentOut.model_validate(row)


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
    if row.state in ("discovered", "reading"):
        row.state, row.error = "failed", body.error
        activity.record(session, account, message, "attachment_failed", row, error=row.error)
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
    before_id: int | None = Query(default=None, ge=1),
) -> MailOverview:
    await process_service.require_process(session, process_id)
    account = await session.scalar(select(MailAccount).where(MailAccount.process_id == process_id))
    messages = (
        []
        if account is None
        else await session.scalars(
            select(MailMessage)
            .where(MailMessage.account_id == account.id)
            .where(MailMessage.id < before_id if before_id else True)
            .order_by(MailMessage.id.desc())
            .limit(limit + 1)
        )
    )
    messages = list(messages)
    return MailOverview(
        account=MailState.model_validate(account) if account else None,
        messages=[await service.message_out(session, message) for message in messages[:limit]],
        next_before_id=messages[limit - 1].id if len(messages) > limit else None,
    )


@router.post(
    "/processes/{process_id}/mail-ingestion/attachments/{attachment_id}/retry",
    operation_id="retryMailAttachment",
)
async def retry_attachment(
    process_id: int, attachment_id: int, body: RetryAttachmentIn, session: Session, user: Manager
) -> MessageOut:
    return await activity.retry(session, process_id, attachment_id, body.expected_attempts, user)


@router.get("/processes/{process_id}/mail-ingestion/activity", operation_id="getMailActivity")
async def mail_activity(
    process_id: int,
    session: Session,
    user: CurrentUser,
    after_id: int | None = Query(default=None, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
) -> MailActivityFeed:
    await process_service.require_process(session, process_id)
    return await activity.feed(session, process_id, user.id, after_id, limit)


@router.post(
    "/processes/{process_id}/mail-ingestion/activity/read", operation_id="readMailActivity"
)
async def read_activity(
    process_id: int, body: ReadActivityIn, session: Session, user: CurrentUser
) -> MailActivityFeed:
    await process_service.require_process(session, process_id)
    return await activity.mark_read(session, process_id, user.id, body.through_id)


@router.get(
    "/processes/{process_id}/mail-ingestion/messages/{message_id}/history",
    operation_id="getMailMessageHistory",
)
async def history(
    process_id: int, message_id: int, session: Session, user: CurrentUser
) -> MailHistory:
    from app.common.exceptions import NotFoundError

    message = await session.scalar(
        select(MailMessage)
        .join(MailAccount)
        .where(MailMessage.id == message_id, MailAccount.process_id == process_id)
    )
    if message is None:
        raise NotFoundError("Message does not belong to this process")
    rows = await session.scalars(
        select(MailActivity)
        .where(MailActivity.message_id == message_id)
        .order_by(MailActivity.id)
        .limit(500)
    )
    old = await session.scalars(
        select(Event)
        .where(
            Event.process_id == process_id,
            Event.step == "mail_operator",
            Event.data["message_id"].as_integer() == message_id,
        )
        .order_by(Event.id)
        .limit(100)
    )
    return MailHistory(
        activities=[ActivityOut.model_validate(r) for r in rows],
        operator_audit=[
            LegacyMailAudit(id=e.id, created_at=e.created_at, data=e.data or {}) for e in old
        ],
    )
