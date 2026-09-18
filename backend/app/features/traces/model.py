from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class Event(Base):
    """Trace of every step: what went in, what came out, how long, how much."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instance_id: Mapped[int | None] = mapped_column(ForeignKey("instances.id"), index=True)
    step: Mapped[str]
    data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    latency_ms: Mapped[int | None]
    cost: Mapped[Decimal | None]
    created_at: Mapped[created_at]
