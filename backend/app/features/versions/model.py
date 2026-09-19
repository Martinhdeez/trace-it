from typing import Any

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class ProcessVersion(Base):
    """Immutable published configuration. The process points to its current version."""

    __tablename__ = "process_versions"
    __table_args__ = (UniqueConstraint("process_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"), index=True)
    number: Mapped[int]
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("process_versions.id"))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    validation: Mapped[dict[str, Any]] = mapped_column(JSONB)
    content_hash: Mapped[str]
    author: Mapped[str]
    reason: Mapped[str]
    created_at: Mapped[created_at]


class ProcessDraft(Base):
    """One editable candidate per process. Publication consumes its validated revision."""

    __tablename__ = "process_drafts"

    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"), primary_key=True)
    base_version_id: Mapped[int | None] = mapped_column(ForeignKey("process_versions.id"))
    revision: Mapped[int]
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    author: Mapped[str]
    validation: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class Execution(Base):
    """Inputs shared by a batch, captured once for deterministic replay."""

    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"), index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("process_versions.id"))
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[created_at]
