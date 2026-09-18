from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class Source(Base):
    """A load of a source of truth (a spreadsheet, a download from an external system).
    Every load is a new row; the current one is the latest per `name`."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"))
    name: Mapped[str]  # defined by the process, e.g. suppliers, erp
    origin: Mapped[str]  # file hash, or "erp:<iso timestamp>"
    rows: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    loaded_at: Mapped[created_at]
