from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at

# What a person's decision is. `resolution` settles a case whose type requires a human and
# never changes the export (P4). `review_correction` settles an instance that was in
# REVIEW (our own doubt) and is exported when the engine has no decision for it.
HUMAN_KINDS = ("resolution", "review_correction")

ENGINE = "engine"  # the `author` of every decision the engine takes


class Decision(Base):
    """Append-only history. An instance's current decision is its latest row."""

    __tablename__ = "decisions"
    __table_args__ = (CheckConstraint(f"human_kind in {HUMAN_KINDS}", name="human_kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = mapped_column(ForeignKey("instances.id"), index=True)
    decision: Mapped[str]
    results: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB
    )  # per rule: rule_id, hash, fires, reason
    rules_hash: Mapped[str]  # hash of the rule set applied
    author: Mapped[str]  # ENGINE or a person's name
    human_kind: Mapped[str | None]  # one of HUMAN_KINDS; NULL for the engine
    reason: Mapped[str | None]
    created_at: Mapped[created_at]


class Finding(Base):
    """A past decision that a newer rule says was wrong. Never changes the past (P14)."""

    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("decisions.id"))
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("rules.id"))
    type: Mapped[str]  # kind of error; e.g. in the invoice process: wrongly_paid
    detail: Mapped[str | None]
    created_at: Mapped[created_at]
