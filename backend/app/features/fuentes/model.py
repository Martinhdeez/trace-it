from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class Fuente(Base):
    """A load of a source of truth (Excel sheet, ERP download). Every load is a new row;
    the current one is the latest per `nombre`."""

    __tablename__ = "fuentes"

    id: Mapped[int] = mapped_column(primary_key=True)
    proceso_id: Mapped[int] = mapped_column(ForeignKey("procesos.id"))
    nombre: Mapped[str]  # proveedores, pedidos, erp
    origen: Mapped[str]  # file hash, or "erp:<iso timestamp>"
    filas: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    cargada: Mapped[created_at]
