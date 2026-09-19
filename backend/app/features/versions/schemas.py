from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.features.processes.execution import ExecutionSettings
from app.features.processes.schemas import DecisionReviewConfig, DecisionTypeIO, SymbolIn


class DraftIn(BaseModel):
    # Omitted fields retain the candidate; explicit null disables review.
    description: str | None = None
    decision_types: list[DecisionTypeIO] | None = None
    symbols: list[SymbolIn] | None = None
    acceptance_examples: list[dict[str, Any]] | None = None
    decision_review: DecisionReviewConfig | None = None
    rule_ids: list[int] | None = None
    guidance: dict[str, str] | None = None
    restore_version_id: int | None = None
    refresh_agents: bool = False
    execution: ExecutionSettings | None = None
    expected_revision: int | None = None


class PublishIn(BaseModel):
    revision: int
    validation_hash: str
    reason: str = Field(default="", max_length=8000)  # optional: the diff already says what changed


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


class VersionDraftOut(BaseModel):
    process_id: int
    base_version_id: int | None
    revision: int
    snapshot: dict[str, Any]
    author: str
    validation: dict[str, Any] | None


class PresetPreview(BaseModel):
    settings: ExecutionSettings | None = None
    error: str | None = None


class ExecutionOut(BaseModel):
    settings: ExecutionSettings
    revision: int | None
    version_id: int | None
    presets: dict[str, PresetPreview]
    decision_review: dict[str, Any] | None


class ReplayOut(BaseModel):
    decision_id: int
    version_id: int
    execution_id: int
    matches: bool
    decision: str
    reason: str | None
    results: list[dict[str, Any]]
