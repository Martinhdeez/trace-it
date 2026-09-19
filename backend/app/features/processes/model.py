from typing import Any

from sqlalchemy import ForeignKey, String, false
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class Process(Base):
    """A configured decision process: its rules, decision types, symbols and history. It
    belongs to a use case, whose description (domain conventions) and agent configuration
    it shares with the use case's other processes."""

    __tablename__ = "processes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    use_case_id: Mapped[int] = mapped_column(ForeignKey("use_cases.id"), index=True)
    decision_review: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[created_at]


class Symbol(Base):
    """A named datum the rules use and extraction must fill."""

    __tablename__ = "symbols"

    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"), primary_key=True)
    name: Mapped[str] = mapped_column(primary_key=True)
    type: Mapped[str]
    description: Mapped[str] = mapped_column(default="")
    required: Mapped[bool] = mapped_column(default=False, server_default=false())


class DecisionType(Base):
    """A possible outcome. Highest `priority` wins when several rules fire; the one marked
    `is_default` applies when none does. A decision of a type marked `requires_human` goes
    to the human queue for a manager to resolve. Names are free: each process defines
    its own types."""

    __tablename__ = "decision_types"

    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"), primary_key=True)
    name: Mapped[str] = mapped_column(primary_key=True)
    priority: Mapped[int]
    is_default: Mapped[bool] = mapped_column(default=False)
    requires_human: Mapped[bool] = mapped_column(default=False, server_default=false())


class ProcessDraft(Base):
    __tablename__ = "process_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int | None] = mapped_column(ForeignKey("processes.id"))
    use_case_id: Mapped[int | None] = mapped_column(ForeignKey("use_cases.id"))
    revision: Mapped[int] = mapped_column(default=1)
    published_process_id: Mapped[int | None] = mapped_column(ForeignKey("processes.id"))
    created_at: Mapped[created_at]


class DraftRevision(Base):
    """Append-only proposal, materials and user answers at a revision."""

    __tablename__ = "draft_revisions"

    draft_id: Mapped[int] = mapped_column(ForeignKey("process_drafts.id"), primary_key=True)
    number: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[created_at]
