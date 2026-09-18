from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at

TIPOS_REGLA = ("requisito", "prohibicion")
ESTADOS_REGLA = ("borrador", "rechazada", "activa", "retirada")


class Regla(Base):
    """A rule as text plus the two independently generated implementations (P9)."""

    __tablename__ = "reglas"
    __table_args__ = (
        ForeignKeyConstraint(
            ["proceso_id", "decision"], ["tipos_decision.proceso_id", "tipos_decision.nombre"]
        ),
        CheckConstraint(f"tipo in {TIPOS_REGLA}", name="tipo"),
        CheckConstraint(f"estado in {ESTADOS_REGLA}", name="estado"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    proceso_id: Mapped[int] = mapped_column(ForeignKey("procesos.id"))
    texto: Mapped[str]
    tipo: Mapped[str]
    decision: Mapped[str]  # outcome produced when the rule fires
    codigo_a: Mapped[str | None]
    codigo_b: Mapped[str | None]
    tests_a: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    tests_b: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    hash: Mapped[str | None]  # sha256 of texto + codigo_a + codigo_b
    estado: Mapped[str] = mapped_column(default="borrador")
    informe: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # validation report
    creada: Mapped[created_at]
    activada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
