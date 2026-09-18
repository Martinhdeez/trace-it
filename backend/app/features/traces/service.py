from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.traces.model import Event


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
        Event(
            instance_id=instance_id,
            step=step,
            data=data,
            latency_ms=latency_ms,
            cost=cost,
        )
    )
