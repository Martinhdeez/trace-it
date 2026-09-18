from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class Extraction(Base):
    """One independent reading of an instance's symbols. Two per instance must agree (P20)."""

    __tablename__ = "extractions"

    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("instances.id"))
    role: Mapped[str]  # extractor_1, extractor_2
    model: Mapped[str]
    symbols: Mapped[dict[str, Any]] = mapped_column(JSONB)
    cost: Mapped[Decimal | None]
    latency_ms: Mapped[int | None]
    created_at: Mapped[created_at]
