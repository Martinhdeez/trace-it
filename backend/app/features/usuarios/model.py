from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at

ROLES = ("responsable", "operador")


class Usuario(Base):
    """A person using the app. `responsable` resolves escalations and approves rules."""

    __tablename__ = "usuarios"
    __table_args__ = (CheckConstraint(f"rol in {ROLES}", name="rol"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str]
    email: Mapped[str] = mapped_column(String, unique=True)
    rol: Mapped[str] = mapped_column(default="operador")
    creado: Mapped[created_at]
