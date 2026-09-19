"""One contract for everything an agent proposes to a manager (docs/api.md, Proposals)."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class ManagerProposal(Base):
    """What an agent proposed and, once, how the manager settled it. The content never
    changes; only the settlement fields are written, one time (status leaves `open`)."""

    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"), index=True)
    instance_id: Mapped[int | None] = mapped_column(ForeignKey("instances.id"))
    channel: Mapped[str]  # escalation, chat, learning
    kind: Mapped[str]  # decision, rule, context, input, source
    summary: Mapped[str]
    rationale: Mapped[str]
    evidence: Mapped[list[str]] = mapped_column(JSONB)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)  # what accepting it applies
    status: Mapped[str] = mapped_column(default="open")  # accepted, rejected, superseded
    author: Mapped[str]  # the agent role that proposed it
    created_at: Mapped[created_at]
    resolved_by: Mapped[str | None]
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # what settling it did
