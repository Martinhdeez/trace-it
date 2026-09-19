"""Durable mail stages, per-user notification receipts and guarded manual retries."""

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert

from app.common.exceptions import ConflictError, NotFoundError
from app.core import events
from app.features.versions.service import lock

from .model import MailAccount, MailActivity, MailActivityRead, MailAttachment, MailMessage
from .schemas import ActivityOut, MailActivityFeed

RETRYABLE = ("invalid_pdf", "infrastructure_error", "operator_retry_failed")


def record(session, account, message, kind, attachment=None, **data):
    session.add(
        MailActivity(
            process_id=account.process_id,
            message_id=message.id,
            attachment_id=attachment.id if attachment else None,
            kind=kind,
            data={"subject": (message.envelope or {}).get("subject", ""), **data},
        )
    )


def retry_allowed(account, message, row):
    from .service import MAX_ATTEMPTS, now

    return bool(
        account.state == "active"
        and account.initial_uid
        and account.next_uid
        and message.uidvalidity == account.uidvalidity
        and account.initial_uid <= message.uid < account.next_uid
        and message.state in ("failed", "partial")
        and message.attempts < MAX_ATTEMPTS
        and (message.lease_until is None or message.lease_until <= now())
        and row.state == "failed"
        and row.error in RETRYABLE
        and row.instance_id is None
        and row.decision_id is None
        and row.execution_id is None
    )


async def retry(session, process_id, attachment_id, expected_attempts, user):
    from . import service

    # Match worker lock order: message before process. Never hold a process lock while
    # waiting on extraction's message lock.
    message = await session.scalar(
        select(MailMessage)
        .join(MailAccount, MailAccount.id == MailMessage.account_id)
        .join(MailAttachment, MailAttachment.message_id == MailMessage.id)
        .where(MailAccount.process_id == process_id, MailAttachment.id == attachment_id)
        .with_for_update(of=MailMessage)
    )
    if message is None:
        raise NotFoundError("Attachment does not belong to this process")
    account = await session.get(MailAccount, message.account_id)
    row = await session.get(MailAttachment, attachment_id, with_for_update=True)
    await lock(session, process_id)
    account = await service.account_lock(session, account)
    if message.attempts != expected_attempts or not retry_allowed(account, message, row):
        raise ConflictError("This attachment cannot be retried in its current state")
    record(
        session,
        account,
        message,
        "retry_requested",
        row,
        author=user.name,
        previous_error=row.error,
        previous_message_error=message.error,
        previous_attempts=message.attempts,
        original_name=row.original_name,
    )
    events.record(
        session,
        "mail_operator",
        process_id=process_id,
        data={
            "action": "retry_attachment",
            "message_id": message.id,
            "attachment_id": row.id,
            "author": user.name,
            "previous_error": row.error,
            "previous_attempts": message.attempts,
        },
    )
    # Preserve UID boundaries, attempt budget, original identity, other attachments and
    # decisions. Revoke the previous lease so stale worker requests cannot overwrite this.
    row.state, row.error, row.completed_at = "discovered", None, None
    message.state, message.error, message.retry_at = "retry_wait", None, None
    message.lease_token, message.lease_until = None, None
    await session.commit()
    return await service.message_out(session, message)


async def feed(session, process_id, user_id, after_id=None, limit=100):
    scope = MailActivity.process_id == process_id
    latest = await session.scalar(select(func.max(MailActivity.id)).where(scope)) or 0
    receipt = await session.get(MailActivityRead, (process_id, user_id))
    through = receipt.through_id if receipt else latest
    query = select(MailActivity).where(scope)
    if after_id is not None:
        query = query.where(MailActivity.id > after_id).order_by(MailActivity.id)
    else:
        query = query.order_by(MailActivity.id.desc())
    rows = list(await session.scalars(query.limit(limit + 1)))
    unread = await session.scalar(
        select(func.count())
        .select_from(MailActivity)
        .where(
            scope,
            MailActivity.id > through,
            or_(
                MailActivity.kind.in_(("completed", "failed", "retry_requested")),
                and_(
                    MailActivity.kind == "received", MailActivity.data["pdf_count"].as_integer() > 0
                ),
            ),
        )
    )
    return MailActivityFeed(
        items=[ActivityOut.model_validate(r) for r in rows[:limit]],
        latest_id=latest,
        through_id=through,
        initialized=receipt is not None,
        unread=unread,
        has_more=len(rows) > limit,
    )


async def mark_read(session, process_id, user_id, through_id):
    latest = (
        await session.scalar(
            select(func.max(MailActivity.id)).where(MailActivity.process_id == process_id)
        )
        or 0
    )
    if through_id > latest:
        raise ConflictError("Cannot acknowledge future mail activity")
    statement = insert(MailActivityRead).values(
        process_id=process_id, user_id=user_id, through_id=through_id
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[MailActivityRead.process_id, MailActivityRead.user_id],
            set_={
                "through_id": func.greatest(
                    MailActivityRead.through_id, statement.excluded.through_id
                )
            },
        )
    )
    await session.commit()
    return await feed(session, process_id, user_id)
