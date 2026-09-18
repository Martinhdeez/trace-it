from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class Evento(Base):
    """Trace of every step: what went in, what came out, how long, how much."""

    __tablename__ = "eventos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instancia_id: Mapped[int | None] = mapped_column(ForeignKey("instancias.id"), index=True)
    paso: Mapped[str]
    datos: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    latencia_ms: Mapped[int | None]
    coste: Mapped[Decimal | None]
    creado: Mapped[created_at]
