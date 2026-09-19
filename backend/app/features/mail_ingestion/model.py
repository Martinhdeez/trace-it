from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class MailAccount(Base):
    __tablename__ = "mail_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"), unique=True)
    host: Mapped[str]
    username: Mapped[str]
    folder: Mapped[str]
    token_hash: Mapped[str] = mapped_column(unique=True)
    state: Mapped[str] = mapped_column(default="uninitialized")
    uidvalidity: Mapped[int | None] = mapped_column(BigInteger)
    initial_uid: Mapped[int | None] = mapped_column(BigInteger)
    next_uid: Mapped[int | None] = mapped_column(BigInteger)
    last_poll_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failures: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None]
    created_at: Mapped[created_at]


class MailMessage(Base):
    __tablename__ = "mail_messages"
    __table_args__ = (UniqueConstraint("account_id", "uidvalidity", "uid"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("mail_accounts.id"), index=True)
    uidvalidity: Mapped[int] = mapped_column(BigInteger)
    uid: Mapped[int] = mapped_column(BigInteger)
    state: Mapped[str] = mapped_column(default="discovered")
    metadata_saved: Mapped[bool] = mapped_column(default=False)
    envelope: Mapped[dict | None] = mapped_column(JSONB)
    attempts: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None]
    retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[str | None]
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[created_at]


class MailAttachment(Base):
    __tablename__ = "mail_attachments"
    __table_args__ = (UniqueConstraint("message_id", "part"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("mail_messages.id"), index=True)
    part: Mapped[str]
    original_name: Mapped[str]
    safe_name: Mapped[str]
    encoding: Mapped[str]
    advertised_size: Mapped[int] = mapped_column(BigInteger)
    state: Mapped[str] = mapped_column(default="discovered")
    error: Mapped[str | None]
    file_hash: Mapped[str | None]
    instance_id: Mapped[int | None] = mapped_column(ForeignKey("instances.id"))
    execution_id: Mapped[int | None] = mapped_column(ForeignKey("executions.id"))
    decision_id: Mapped[int | None] = mapped_column(ForeignKey("decisions.id"))
    created_at: Mapped[created_at]


class RunOperation(Base):
    """A response committed in the same transaction as its decisions."""

    __tablename__ = "run_operations"
    __table_args__ = (UniqueConstraint("process_id", "key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"))
    key: Mapped[str]
    instance_ids: Mapped[list[int]] = mapped_column(JSONB)
    result: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[created_at]
