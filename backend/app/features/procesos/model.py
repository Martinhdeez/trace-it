from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class Proceso(Base):
    """A folder of rules with its own decision history (docs/plano-aplicacion.md 3.8)."""

    __tablename__ = "procesos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String, unique=True)
    descripcion: Mapped[str] = mapped_column(default="")
    creado: Mapped[created_at]


class Simbolo(Base):
    """A named datum the rules use and extraction must fill."""

    __tablename__ = "simbolos"

    proceso_id: Mapped[int] = mapped_column(ForeignKey("procesos.id"), primary_key=True)
    nombre: Mapped[str] = mapped_column(primary_key=True)
    tipo: Mapped[str]
    descripcion: Mapped[str] = mapped_column(default="")


class TipoDecision(Base):
    """A possible outcome. Highest `prioridad` wins when several rules fire; the one marked
    `por_defecto` applies when none does."""

    __tablename__ = "tipos_decision"

    proceso_id: Mapped[int] = mapped_column(ForeignKey("procesos.id"), primary_key=True)
    nombre: Mapped[str] = mapped_column(primary_key=True)
    prioridad: Mapped[int]
    por_defecto: Mapped[bool] = mapped_column(default=False)
