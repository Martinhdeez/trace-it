import hashlib
import io
import secrets
from datetime import UTC, datetime, timedelta

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert

from app.common.exceptions import ConflictError, NotFoundError
from app.features.decisions import service as decisions
from app.features.decisions.model import Decision
from app.features.ingestion import process_service
from app.features.ingestion.model import Instance
from app.features.ingestion.process_extraction import read_document
from app.features.ingestion.runtime import for_process
from app.features.ingestion.schemas import ExtractOptions
from app.features.versions.service import lock

from . import activity
from .config import MailSettings
from .documents import RejectedDocument, safe_name, validate_pdf
from .model import MailAccount, MailAttachment, MailMessage
from .schemas import AttachmentOut, MailState, MessageOut

TERMINAL = ("completed", "partial", "ignored", "failed")
MAX_ATTEMPTS = 6
LEASE_SECONDS = 300


def now():
    return datetime.now(UTC)


async def account_lock(session, account):
    return await session.scalar(
        select(MailAccount)
        .where(MailAccount.id == account.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def require_active(account):
    if (
        account.state != "active"
        or not account.uidvalidity
        or not account.initial_uid
        or not account.next_uid
        or account.next_uid < account.initial_uid
    ):
        raise ConflictError("Mailbox is not initialized and active; operator intervention required")


async def initialize(session, account, body):
    account = await account_lock(session, account)
    if account.state != "uninitialized":
        raise ConflictError("Mailbox already initialized; its cursor must never be reset")
    account.uidvalidity = body.uidvalidity
    account.initial_uid = account.next_uid = body.uidnext
    account.state = "active"
    await session.commit()
    return MailState.model_validate(account)


async def discover(session, account, body):
    account = await account_lock(session, account)
    require_active(account)
    if body.uidvalidity != account.uidvalidity:
        account.state, account.error = "halted", "uidvalidity_changed"
        await session.commit()
        raise ConflictError("UIDVALIDITY changed; operator intervention required")
    if body.expected_cursor != account.next_uid:
        raise ConflictError("Cursor changed; reload mailbox state")
    if not account.next_uid - 1 <= body.through_uid < account.next_uid + 100:
        raise ConflictError("Discovery range exceeds its bound")
    uids = sorted(set(body.uids))
    if any(uid < account.next_uid or uid > body.through_uid for uid in uids):
        raise ConflictError("UID lies outside the persisted discovery boundary")
    for uid in uids:
        await session.execute(
            insert(MailMessage)
            .values(
                account_id=account.id,
                uidvalidity=account.uidvalidity,
                uid=uid,
                state="discovered",
                metadata_saved=False,
                attempts=0,
            )
            .on_conflict_do_nothing()
        )
    # The cursor and *all* discovered work commit together.
    account.next_uid = body.through_uid + 1
    account.last_poll_at = now()
    account.failures, account.error, account.retry_at = 0, None, None
    await session.commit()
    return MailState.model_validate(account)


async def poll_failure(session, account, body):
    account = await account_lock(session, account)
    account.failures += 1
    account.error = body.error
    if (
        body.error in ("invalid_credentials", "uidvalidity_changed")
        or account.failures >= MAX_ATTEMPTS
    ):
        account.state = "halted"
    account.retry_at = now() + timedelta(seconds=min(3600, 60 * 2 ** min(account.failures, 6)))
    await session.commit()
    return MailState.model_validate(account)


async def attachments(session, message_id):
    return list(
        await session.scalars(
            select(MailAttachment)
            .where(MailAttachment.message_id == message_id)
            .order_by(MailAttachment.id)
        )
    )


async def message_out(session, message):
    result = MessageOut.model_validate(message)
    originals = {a.id: a for a in await attachments(session, message.id)}
    result.attachments = [AttachmentOut.model_validate(a) for a in originals.values()]
    account = await session.get(MailAccount, message.account_id)
    for part in result.attachments:
        part.can_retry = activity.retry_allowed(account, message, originals[part.id])
        if part.decision_id:
            decision = await session.get(Decision, part.decision_id)
            part.decision = decision.decision if decision else None
            if decision:
                part.reason = decision.reason
                # Keep the original mail outcome, but only invite review if the current
                # decision still requires it (a person may already have resolved the case).
                latest = await session.scalar(
                    select(Decision)
                    .where(Decision.instance_id == part.instance_id)
                    .order_by(Decision.id.desc())
                    .limit(1)
                )
                human = await decisions.historical_human_types(
                    session, account.process_id, [latest]
                )
                reviews = await decisions.decision_reviewer.for_decisions(session, [latest])
                part.requires_review = latest.decision in human[latest.id] or bool(
                    reviews.get(latest.id) and reviews[latest.id].requires_human
                )
    return result


async def claim(session, account, ready_only=False):
    require_active(account)
    message = await session.scalar(
        select(MailMessage)
        .where(
            MailMessage.account_id == account.id,
            MailMessage.state.not_in(TERMINAL),
            *(
                [
                    MailMessage.metadata_saved.is_(True),
                    ~select(MailAttachment.id)
                    .where(
                        MailAttachment.message_id == MailMessage.id,
                        MailAttachment.state.in_(("discovered", "reading")),
                    )
                    .exists(),
                ]
                if ready_only
                else []
            ),
            or_(MailMessage.retry_at.is_(None), MailMessage.retry_at <= now()),
            or_(MailMessage.lease_until.is_(None), MailMessage.lease_until <= now()),
        )
        .order_by(MailMessage.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if message is None:
        return None
    if message.attempts >= MAX_ATTEMPTS:
        message.state, message.error = "failed", "attempts_exhausted"
        await fail_unimported(session, message, "attempts_exhausted")
        activity.record(
            session, account, message, "failed", error=message.error, state=message.state
        )
        await session.commit()
        return None
    message.attempts += 1
    message.lease_token = secrets.token_hex(24)
    message.lease_until = now() + timedelta(seconds=LEASE_SECONDS)
    message.state, message.retry_at = "importing", None
    await session.commit()
    return {
        **(await message_out(session, message)).model_dump(),
        "lease_token": message.lease_token,
    }


async def leased(session, account, message_id, token):
    require_active(account)
    message = await session.scalar(
        select(MailMessage)
        .where(MailMessage.id == message_id, MailMessage.account_id == account.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if message is None:
        raise NotFoundError("Mail message does not belong to this account")
    if not token or token != message.lease_token:
        raise ConflictError("Mail lease was replaced; reload the work item")
    message.lease_until = now() + timedelta(seconds=LEASE_SECONDS)
    return message


async def manifest(session, account, message, body):
    limits = MailSettings()
    if message.metadata_saved:
        return await message_out(session, message)
    message.envelope = body.model_dump(exclude={"parts"})
    message.metadata_saved = True
    if body.size > limits.max_message_bytes or len(body.parts) > limits.max_pdfs_per_message:
        message.state, message.error = "failed", "size_limit"
    elif len({p.part for p in body.parts}) != len(body.parts):
        raise ConflictError("Repeated MIME part in manifest")
    else:
        for part in body.parts:
            session.add(
                MailAttachment(
                    message_id=message.id,
                    **part.model_dump(),
                    safe_name=safe_name(part.original_name, f"{message.id}-{part.part}"),
                )
            )
        message.state = "importing" if body.parts else "ignored"
    activity.record(
        session,
        account,
        message,
        "received",
        pdf_count=len(body.parts),
        state=message.state,
        error=message.error,
    )
    if message.state == "failed":
        activity.record(
            session, account, message, "failed", state=message.state, error=message.error
        )
    await session.commit()
    return await message_out(session, message)


async def attachment(session, message, attachment_id):
    row = await session.get(MailAttachment, attachment_id)
    if row is None or row.message_id != message.id:
        raise NotFoundError("Attachment does not belong to this message")
    return row


async def import_pdf(session, account, message, row, content, extraction_service):
    if row.state not in ("discovered", "reading"):
        return AttachmentOut.model_validate(row)
    try:
        await run_in_threadpool(validate_pdf, content, MailSettings().max_pdf_bytes)
    except RejectedDocument as error:
        row.state, row.error = "failed", str(error)
        activity.record(session, account, message, "attachment_failed", row, error=row.error)
        await session.commit()
        return AttachmentOut.model_validate(row)
    digest = hashlib.sha256(content).hexdigest()
    match = (
        select(Instance)
        .where(Instance.process_id == account.process_id, Instance.file_hash == digest)
        .order_by(Instance.id)
        .limit(1)
        .execution_options(populate_existing=True)
    )
    existing = await session.scalar(match)
    if existing is None:
        # Preserve parallel document reading: expensive extraction holds only this message's
        # lease row, never the process lock. Recheck duplicates under the lock before attaching.
        service, options = await for_process(
            session, account.process_id, extraction_service, ExtractOptions()
        )
        item = await run_in_threadpool(service.ingest, io.BytesIO(content), row.safe_name)
        result, symbols, context = await read_document(
            session, account.process_id, service, item, options
        )
    await lock(session, account.process_id)
    existing = await session.scalar(match)
    row.file_hash = digest
    if existing:
        owned = await session.scalar(
            select(MailAttachment.id)
            .where(
                MailAttachment.instance_id == existing.id,
                MailAttachment.state.in_(("imported", "completed")),
            )
            .limit(1)
        )
        row.instance_id = existing.id
        row.state = "duplicate"
        row.error = (
            "manual_pending_conflict"
            if existing.status == "PENDING" and not owned
            else "duplicate_content"
        )
        latest = await session.scalar(
            select(Decision)
            .where(Decision.instance_id == existing.id)
            .order_by(Decision.id.desc())
            .limit(1)
        )
        if latest:
            row.decision_id, row.execution_id = latest.id, latest.execution_id
    else:
        upload = await process_service.attach_document(
            session,
            account.process_id,
            None,
            content,
            result,
            symbols,
            {
                **context,
                "automation": "mail_ingestion",
                "mail_attachment_id": row.id,
                "mail_origin": {
                    "account": account.username,
                    "folder": account.folder,
                    "uidvalidity": message.uidvalidity,
                    "uid": message.uid,
                    "part": row.part,
                    "original_name": row.original_name,
                    **(message.envelope or {}),
                },
            },
            commit=False,
        )
        row.instance_id, row.state = upload["instance_id"], "imported"
    activity.record(
        session,
        account,
        message,
        "imported",
        row,
        instance_id=row.instance_id,
        state=row.state,
        error=row.error,
    )
    await session.commit()
    return AttachmentOut.model_validate(row)


async def finish(session, account, message, token):
    if message.state in TERMINAL:
        return await message_out(session, message)
    message_id = message.id
    rows = await attachments(session, message.id)
    if any(row.state in ("discovered", "reading") for row in rows):
        raise ConflictError("Import every candidate before evaluating this message")
    pending = [row for row in rows if row.state == "imported"]
    selected = [row.instance_id for row in pending]
    # No connector-controlled IDs: the backend derives ownership from its ledger.
    if selected:
        operation_key = f"mail-message:{message.id}"
        if any(row.state == "completed" for row in rows):
            operation_key += ":parts:" + ",".join(str(row.id) for row in pending)
        message.state = "evaluating"
        activity.record(session, account, message, "evaluating", instance_ids=selected)
        await session.commit()
        await decisions.run(
            session,
            account.process_id,
            author=f"mail_ingestion:{account.id}",
            instance_ids=selected,
            idempotency_key=operation_key,
        )
        await session.refresh(account)
        message = await leased(session, account, message_id, token)
        rows = await attachments(session, message.id)
        for row in rows:
            if row.state != "imported":
                continue
            decision = await session.scalar(
                select(Decision)
                .where(Decision.instance_id == row.instance_id)
                .order_by(Decision.id)
                .limit(1)
            )
            if decision is None:
                raise ConflictError("Imported instance has no decision; extraction requires review")
            row.state = "completed"
            row.completed_at = now()
            row.decision_id, row.execution_id = decision.id, decision.execution_id
            # Another MIME part/message may have found this owned instance while it was
            # still pending. Preserve that provenance and complete its result links too.
            await session.execute(
                update(MailAttachment)
                .where(
                    MailAttachment.instance_id == row.instance_id,
                    MailAttachment.state == "duplicate",
                    MailAttachment.decision_id.is_(None),
                )
                .values(decision_id=decision.id, execution_id=decision.execution_id)
            )
    failures = any(row.state == "failed" or row.error == "manual_pending_conflict" for row in rows)
    successes = any(row.state in ("completed", "duplicate") for row in rows)
    message.state = (
        ("partial" if successes else "failed") if failures else "completed" if rows else "ignored"
    )
    message.lease_until = None
    message.error = "attachment_failure" if failures else None
    result = await message_out(session, message)
    activity.record(
        session,
        account,
        message,
        "failed" if message.state == "failed" else "completed",
        state=message.state,
        error=message.error,
        attachment_count=len(rows),
        review_count=sum(
            p.requires_review or p.error == "manual_pending_conflict" for p in result.attachments
        ),
        failed_count=sum(p.state == "failed" for p in result.attachments),
    )
    await session.commit()
    return await message_out(session, message)


async def fail_unimported(session, message, error):
    for row in await attachments(session, message.id):
        if row.state in ("discovered", "reading"):
            row.state, row.error = "failed", error


async def fail_message(session, message, body):
    if message.state in TERMINAL:
        return await message_out(session, message)
    message.error = body.error
    message.state = "failed" if body.permanent or message.attempts >= MAX_ATTEMPTS else "retry_wait"
    message.retry_at = now() + timedelta(seconds=min(3600, 60 * 2 ** min(message.attempts, 6)))
    message.lease_until = None
    if message.state == "failed":
        await fail_unimported(session, message, body.error)
    account = await session.get(MailAccount, message.account_id)
    activity.record(
        session,
        account,
        message,
        "failed",
        error=body.error,
        state=message.state,
        retry_at=message.retry_at.isoformat(),
    )
    await session.commit()
    return await message_out(session, message)
