from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, LargeBinary, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.database import Base, created_at
from app.features.ingestion.symbols import check_stored

INSTANCE_STATUSES = ("PENDING", "DECIDED")


class File(Base):
    """An ingested file. Immutable and identified by its content hash: a modified file is a
    new file (ADR 0008)."""

    __tablename__ = "files"

    hash: Mapped[str] = mapped_column(primary_key=True)  # sha256 hex
    name: Mapped[str]
    content: Mapped[bytes] = mapped_column(LargeBinary)
    text: Mapped[str | None]  # None for scans until OCR/vision has read them
    ingested_at: Mapped[created_at]


class Instance(Base):
    """One case the process decides. `name` identifies it in exports (the challenge's
    `outcomes.jsonl` calls it `file_id`). PENDING until the engine or a person decides it."""

    __tablename__ = "instances"
    __table_args__ = (
        UniqueConstraint("process_id", "name", "file_hash"),
        CheckConstraint(f"status in {INSTANCE_STATUSES}", name="status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"))
    file_hash: Mapped[str] = mapped_column(ForeignKey("files.hash"))
    name: Mapped[str]
    status: Mapped[str] = mapped_column(default="PENDING")
    # Extracted symbols: {name: {"value": ..., "origin": ...}}. Rule code gets them flattened.
    # None until extraction has run.
    symbols: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    @validates("symbols")
    def _check_symbols(self, _key: str, symbols: dict[str, Any] | None) -> dict[str, Any] | None:
        if symbols is not None:
            check_stored(symbols)
        return symbols
