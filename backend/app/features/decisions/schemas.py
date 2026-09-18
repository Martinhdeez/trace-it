from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DecisionOut(BaseModel):
    id: int
    decision: str
    author: str  # "engine" or the person's name
    human_kind: str | None  # a person's decision: "resolution" or "review_correction"
    reason: str | None
    results: list[dict[str, Any]]  # per rule: rule_id, hash, fires, reason
    rules_hash: str
    created_at: datetime


class EventOut(BaseModel):
    step: str
    data: dict[str, Any] | None
    latency_ms: int | None
    created_at: datetime


class InstanceOut(BaseModel):
    id: int
    name: str = Field(examples=["factura_1217.pdf"])  # the exact file_id of the export
    status: str
    decision: str | None  # the latest decision, if any


class InstanceDetail(InstanceOut):
    file_hash: str
    symbols: dict[str, Any] | None
    decisions: list[DecisionOut]  # append-only history, oldest first
    events: list[EventOut]


class ResolveIn(BaseModel):
    decision: str = Field(examples=["NO_PAGAR"])  # must be a decision type of the process
    reason: str


class RunSummary(BaseModel):
    decided: int
    by_decision: dict[str, int] = Field(examples=[{"PAGAR": 431, "NO_PAGAR": 9, "ESCALAR": 60}])


class ChangeOut(BaseModel):
    instance_id: int
    name: str
    before: str
    after: str
    previous_author: str
    reason: str


class ImpactOut(BaseModel):
    """What a rule change would do to the decisions already taken."""

    unchanged: int
    changes: list[ChangeOut]  # the engine decided it and would now decide otherwise
    conflicts: list[ChangeOut]  # a person decided it and the rules would contradict them


class FindingOut(BaseModel):
    id: int
    decision_id: int
    rule_id: int | None
    type: str
    detail: str | None
    created_at: datetime
