from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, LargeBinary, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at

ESTADOS_INSTANCIA = ("PENDIENTE", "REVISION", "DECIDIDA")


class Fichero(Base):
    """An ingested file. Immutable and identified by its content hash: a modified file is a
    new file (P16)."""

    __tablename__ = "ficheros"

    hash: Mapped[str] = mapped_column(primary_key=True)  # sha256 hex
    nombre: Mapped[str]
    contenido: Mapped[bytes] = mapped_column(LargeBinary)
    texto: Mapped[str | None]  # None for scans until OCR/vision has read them
    ingerido: Mapped[created_at]


class Instancia(Base):
    """One case the process decides. `nombre` is the exact `file_id` of the export."""

    __tablename__ = "instancias"
    __table_args__ = (
        UniqueConstraint("proceso_id", "nombre", "fichero_hash"),
        CheckConstraint(f"estado in {ESTADOS_INSTANCIA}", name="estado"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    proceso_id: Mapped[int] = mapped_column(ForeignKey("procesos.id"))
    fichero_hash: Mapped[str] = mapped_column(ForeignKey("ficheros.hash"))
    nombre: Mapped[str]
    estado: Mapped[str] = mapped_column(default="PENDIENTE")
    motivo_revision: Mapped[str | None]
    # Agreed symbols: {nombre: {"valor": ..., "origen": ...}}
    simbolos: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
