from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at

RULE_TYPES = ("requirement", "prohibition")
# compiling: its code is being written in the background. blocked: it needs data the process
# does not have, or its compilation failed, so it is enforced by escalating every instance
# (ADR 0004, 0016, 0020).
RULE_STATUSES = ("compiling", "draft", "active", "blocked", "retired")
ENFORCED = ("active", "blocked")  # the statuses the engine runs


class NormRule(Base):
    """One sentence of the client's norm, exactly as written (ADR 0017). The unit the client
    owns: its atomic checks are `Rule`s, each with one code and one decision."""

    __tablename__ = "norm_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"))
    number: Mapped[int]  # its position in the norm
    text: Mapped[str]
    # statements of the sentence that are not checkable conditions, as the normalizer read them
    policies: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[created_at]


class Rule(Base):
    """A rule as text plus the code that runs for it (ADR 0003). The compiler writes the
    code with two blind agents and keeps the second one's work in `report` as evidence
    (ADR 0004); a hand-written rule arrives with its code and no report to speak of."""

    __tablename__ = "rules"
    __table_args__ = (
        CheckConstraint(f"type in {RULE_TYPES}", name="type"),
        CheckConstraint(f"status in {RULE_STATUSES}", name="status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"))
    norm_rule_id: Mapped[int | None] = mapped_column(ForeignKey("norm_rules.id"))
    text: Mapped[str]
    type: Mapped[str]
    decision: Mapped[str]  # outcome produced when the rule fires
    code: Mapped[str | None]  # defines evaluate(instance, sources, others)
    tests: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    hash: Mapped[str | None]  # sha256 of text + code
    status: Mapped[str] = mapped_column(default="draft")
    report: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # validation report
    created_at: Mapped[created_at]
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
