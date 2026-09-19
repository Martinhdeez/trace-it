from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.features.processes.schemas import DecisionReviewConfig, DecisionTypeIO, SymbolIO


class DraftIn(BaseModel):
    # Omitted fields retain the candidate; explicit null disables review.
    description: str | None = None
    decision_types: list[DecisionTypeIO] | None = None
    symbols: list[SymbolIO] | None = None
    decision_review: DecisionReviewConfig | None = None
    rule_ids: list[int] | None = None
    guidance: dict[str, str] | None = None
    restore_version_id: int | None = None
    refresh_agents: bool = False
    expected_revision: int | None = None


class PublishIn(BaseModel):
    revision: int
    validation_hash: str
    reason: str = Field(min_length=1, max_length=8000, pattern=r"\S")


class VersionOut(BaseModel):
    id: int
    process_id: int
    number: int
    parent_id: int | None
    snapshot: dict[str, Any]
    validation: dict[str, Any]
    content_hash: str
    author: str
    reason: str
    created_at: datetime


class DraftOut(BaseModel):
    process_id: int
    base_version_id: int | None
    revision: int
    snapshot: dict[str, Any]
    author: str
    validation: dict[str, Any] | None
