from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MailState(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    protocol_version: int = 1
    id: int
    process_id: int
    host: str
    username: str
    folder: str
    state: str
    uidvalidity: int | None
    initial_uid: int | None
    next_uid: int | None
    last_poll_at: datetime | None
    retry_at: datetime | None
    error: str | None


class GatheringSettings(BaseModel):
    email: Literal["migration-test@j-aautomation.com"] | None = None


class InitializeIn(BaseModel):
    uidvalidity: int = Field(gt=0)
    uidnext: int = Field(gt=0)


class DiscoverIn(BaseModel):
    uidvalidity: int = Field(gt=0)
    expected_cursor: int = Field(gt=0)
    through_uid: int = Field(ge=0)
    uids: list[int] = Field(max_length=100)


class PartIn(BaseModel):
    part: str = Field(pattern=r"^[1-9][0-9]*(\.[1-9][0-9]*)*$", max_length=100)
    original_name: str = Field(max_length=512)
    encoding: str = Field(max_length=40)
    advertised_size: int = Field(ge=0)


class ManifestIn(BaseModel):
    sender: str = Field(default="", max_length=1000)
    subject: str = Field(default="", max_length=1000)
    message_id: str = Field(default="", max_length=1000)
    sent_at: str = Field(default="", max_length=100)
    internal_date: str = Field(default="", max_length=100)
    size: int = Field(ge=0)
    parts: list[PartIn] = Field(max_length=100)


class MailFailureIn(BaseModel):
    error: Literal[
        "imap_unavailable",
        "invalid_credentials",
        "uidvalidity_changed",
        "invalid_pdf",
        "size_limit",
        "invalid_mime",
        "message_missing",
        "infrastructure_error",
        "attempts_exhausted",
    ]
    permanent: bool = False


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    part: str
    original_name: str
    safe_name: str
    encoding: str
    advertised_size: int
    state: str
    error: str | None
    file_hash: str | None
    instance_id: int | None
    execution_id: int | None
    decision_id: int | None
    decision: str | None = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    uid: int
    uidvalidity: int
    state: str
    metadata_saved: bool
    envelope: dict | None
    attempts: int
    error: str | None
    retry_at: datetime | None
    created_at: datetime
    attachments: list[AttachmentOut] = []


class ClaimedMessage(MessageOut):
    lease_token: str


class MailOverview(BaseModel):
    account: MailState | None
    messages: list[MessageOut]
