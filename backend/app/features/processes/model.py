from sqlalchemy import ForeignKey, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class Process(Base):
    """A folder of rules with its own decision history (docs/application-blueprint.md 3.8)."""

    __tablename__ = "processes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str] = mapped_column(default="")
    created_at: Mapped[created_at]


class Symbol(Base):
    """A named datum the rules use and extraction must fill."""

    __tablename__ = "symbols"

    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"), primary_key=True)
    name: Mapped[str] = mapped_column(primary_key=True)
    type: Mapped[str]
    description: Mapped[str] = mapped_column(default="")


class DecisionType(Base):
    """A possible outcome. Highest `priority` wins when several rules fire; the one marked
    `is_default` applies when none does. A decision of a type marked `requires_human` goes
    to the human queue for a manager to resolve. Names are free: each process defines
    its own types."""

    __tablename__ = "decision_types"

    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"), primary_key=True)
    name: Mapped[str] = mapped_column(primary_key=True)
    priority: Mapped[int]
    is_default: Mapped[bool] = mapped_column(default=False)
    requires_human: Mapped[bool] = mapped_column(default=False, server_default=false())
