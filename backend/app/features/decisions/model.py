from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at

ENGINE = "engine"  # the `author` of every decision the engine takes


class Decision(Base):
    """Append-only history. An instance's current decision is its latest row. The engine's
    rows carry the result of every rule; a person's carry their reason."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("instances.id"), index=True)
    decision: Mapped[str]
    results: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)  # per rule: RuleResult
    rules_hash: Mapped[str]  # hash of the rule set applied
    author: Mapped[str]  # ENGINE or a person's name
    reason: Mapped[str | None]
    created_at: Mapped[created_at]


class Finding(Base):
    """A past decision that a newer rule says was wrong. Never changes the past (ADR 0008)."""

    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("decisions.id"))
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("rules.id"))
    type: Mapped[str]  # kind of error; e.g. in the invoice process: wrongly_paid
    detail: Mapped[str | None]
    created_at: Mapped[created_at]
