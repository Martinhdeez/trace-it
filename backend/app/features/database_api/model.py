"""Immutable audit records for direct database writes, committed with the change."""

from typing import Any

from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class DatabaseApiChange(Base):
    __tablename__ = "database_api_changes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    table_name: Mapped[str]
    operation: Mapped[str]
    key: Mapped[dict[str, Any]] = mapped_column(JSONB)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reason: Mapped[str]
    actor: Mapped[str]
    created_at: Mapped[created_at]
