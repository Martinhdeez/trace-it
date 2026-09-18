from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at

RULE_TYPES = ("requirement", "prohibition")
RULE_STATUSES = ("draft", "rejected", "active", "retired")


class Rule(Base):
    """A rule as text plus the two independently generated implementations (P9)."""

    __tablename__ = "rules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["process_id", "decision"], ["decision_types.process_id", "decision_types.name"]
        ),
        CheckConstraint(f"type in {RULE_TYPES}", name="type"),
        CheckConstraint(f"status in {RULE_STATUSES}", name="status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"))
    text: Mapped[str]
    type: Mapped[str]
    decision: Mapped[str]  # outcome produced when the rule fires
    code_a: Mapped[str | None]
    code_b: Mapped[str | None]
    tests_a: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    tests_b: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    hash: Mapped[str | None]  # sha256 of text + code_a + code_b
    status: Mapped[str] = mapped_column(default="draft")
    report: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # validation report
    created_at: Mapped[created_at]
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
