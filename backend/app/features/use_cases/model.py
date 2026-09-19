from typing import Any

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class UseCase(Base):
    """What the application is used for (e.g. invoice payment). It holds what every process
    of that use case shares: the domain conventions (`description`) and how its agents are
    configured. A process is one set of rules inside a use case."""

    __tablename__ = "use_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str] = mapped_column(default="")
    created_at: Mapped[created_at]


class AgentConfig(Base):
    """One version of how an agent role works in a use case (ADR 0011). Append-only: a
    change is a new version; rolling back activates an older one. At most one active
    version per role."""

    __tablename__ = "agent_configs"
    __table_args__ = (
        UniqueConstraint("use_case_id", "role", "version"),
        Index(
            "uq_agent_configs_active",
            "use_case_id",
            "role",
            unique=True,
            postgresql_where=text("active"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    use_case_id: Mapped[int] = mapped_column(ForeignKey("use_cases.id"), index=True)
    role: Mapped[str]
    version: Mapped[int]
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)  # an AgentSettings
    active: Mapped[bool] = mapped_column(default=False)
    author: Mapped[str]
    note: Mapped[str | None]
    created_at: Mapped[created_at]
