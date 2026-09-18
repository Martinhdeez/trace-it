from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class Decision(Base):
    """Append-only history. An instance's current decision is its latest row."""

    __tablename__ = "decisiones"

    id: Mapped[int] = mapped_column(primary_key=True)
    instancia_id: Mapped[int] = mapped_column(ForeignKey("instancias.id"), index=True)
    decision: Mapped[str]
    resultados: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB
    )  # per rule: id, hash, salta, motivo
    reglas_hash: Mapped[str]  # hash of the rule set applied
    autor: Mapped[str]  # "motor" or a person's name
    motivo: Mapped[str | None]
    creada: Mapped[created_at]


class Hallazgo(Base):
    """A past decision that a newer rule says was wrong. Never changes the past (P14)."""

    __tablename__ = "hallazgos"

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("decisiones.id"))
    regla_id: Mapped[int | None] = mapped_column(ForeignKey("reglas.id"))
    tipo: Mapped[str]  # kind of error; e.g. in the invoice process: pagada_indebidamente
    detalle: Mapped[str | None]
    creado: Mapped[created_at]
