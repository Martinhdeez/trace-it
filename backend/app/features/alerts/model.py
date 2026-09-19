from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class Alert(Base):
    """A past decision that newer data or rules would decide otherwise (ADR 0026). A notice
    for the manager, never a change to the decision. What was detected is never edited; only
    the status moves forward (open -> acknowledged), each move an `ack_alert` span. It is
    resolved once the instance has a later decision (a resolution or a reprocess)."""

    __tablename__ = "alerts"
    # The same decision flagged towards the same outcome again says nothing new.
    __table_args__ = (UniqueConstraint("decision_id", "after"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"), index=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("instances.id"))
    decision_id: Mapped[int] = mapped_column(ForeignKey("decisions.id"))  # the one flagged
    before: Mapped[str]
    after: Mapped[str]  # what the engine would decide now
    trigger: Mapped[dict[str, Any]] = mapped_column(JSONB)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str]  # open or acknowledged; resolved is derived
    acknowledged_by: Mapped[str | None]
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None]
    created_at: Mapped[created_at]
