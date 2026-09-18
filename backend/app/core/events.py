"""Trace of every step: what went in, what came out, how long, how much."""

from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instance_id: Mapped[int | None] = mapped_column(ForeignKey("instances.id"), index=True)
    step: Mapped[str]
    data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    latency_ms: Mapped[int | None]
    cost: Mapped[Decimal | None]
    created_at: Mapped[created_at]


def record(
    session: AsyncSession,
    step: str,
    *,
    instance_id: int | None = None,
    data: dict[str, Any] | None = None,
    latency_ms: int | None = None,
    cost: float | None = None,
) -> None:
    """Add a trace event to the session. It is saved with the caller's commit."""
    session.add(
        Event(instance_id=instance_id, step=step, data=data, latency_ms=latency_ms, cost=cost)
    )
