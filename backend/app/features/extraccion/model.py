from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class Extraccion(Base):
    """One independent reading of an instance's symbols. Two per instance must agree (P20)."""

    __tablename__ = "extracciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    instancia_id: Mapped[int] = mapped_column(ForeignKey("instancias.id"))
    papel: Mapped[str]  # extractor_1, extractor_2
    modelo: Mapped[str]
    simbolos: Mapped[dict[str, Any]] = mapped_column(JSONB)
    coste: Mapped[Decimal | None]
    latencia_ms: Mapped[int | None]
    creada: Mapped[created_at]
