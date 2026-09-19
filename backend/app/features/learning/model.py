"""Learning artifacts are append-only. Only a manager's adoption affects the process."""

from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, created_at


class Analysis(Base):
    __tablename__ = "learning_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("processes.id"), index=True)
    author: Mapped[str]
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    reasoning: Mapped[str]
    created_at: Mapped[created_at]


class Proposal(Base):
    __tablename__ = "norm_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("learning_analyses.id"), index=True)
    kind: Mapped[str]  # deterministic or guidance
    text: Mapped[str]
    reasoning: Mapped[str]
    evidence: Mapped[list[str]] = mapped_column(JSONB)
    counterexamples: Mapped[list[str]] = mapped_column(JSONB)
    limitations: Mapped[str]
    created_at: Mapped[created_at]


class Validation(Base):
    __tablename__ = "norm_validations"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("norm_proposals.id"), index=True)
    author: Mapped[str]
    baseline: Mapped[str]
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    report: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[created_at]


class Adoption(Base):
    """One terminal manager resolution, including the exact published process snapshot."""

    __tablename__ = "norm_adoptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("norm_proposals.id"), unique=True)
    validation_id: Mapped[int | None] = mapped_column(ForeignKey("norm_validations.id"))
    approved: Mapped[bool]
    author: Mapped[str]
    reason: Mapped[str]
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[created_at]
