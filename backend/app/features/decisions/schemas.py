from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DecisionOut(BaseModel):
    version_id: int | None = None
    execution_id: int | None = None
    id: int
    decision: str
    author: str  # "engine" or the person's name
    reason: str | None
    results: list[dict[str, Any]]  # per rule: rule_id, hash, fires, reason
    rules_hash: str
    created_at: datetime


class EventOut(BaseModel):
    id: int
    trace_id: str  # `GET /traces/{trace_id}`: the tree this step belongs to
    instance_id: int | None
    rule_id: int | None = None  # a rule's step: saved, compiled, activated, retired
    step: str = Field(examples=["decision", "resolution", "compile_rule", "sync_source"])
    status: str  # "ok" or "error"
    data: dict[str, Any] | None
    duration_ms: int | None
    created_at: datetime


class InstanceOut(BaseModel):
    id: int
    name: str = Field(examples=["factura_1217.pdf"])  # the exact file_id of the export
    status: str
    # The latest decision, if any: what it was, who took it and why.
    decision: str | None
    author: str | None = None  # "engine" or the person's name
    reason: str | None = None
    decided_at: datetime | None = None
    review_pending: bool = False
    # The symbols as plain values ({name: value}), so a list can sort and show them.
    values: dict[str, Any] | None = None


class DecisionReviewOut(BaseModel):
    id: int
    decision_id: int
    status: str
    recommendation: str | None
    reasoning: str | None
    evidence: list[str]
    requires_human: bool
    snapshot: dict[str, Any]
    model: str | None
    error: str | None
    created_at: datetime


class InstanceDetail(InstanceOut):
    file_hash: str
    symbols: dict[str, Any] | None
    decisions: list[DecisionOut]  # append-only history, oldest first
    events: list[EventOut]
    reviews: list[DecisionReviewOut] = []


class ResolveIn(BaseModel):
    decision: str = Field(examples=["NO_PAGAR"])  # must be a decision type of the process
    reason: str
    # The assistant's open proposal this answers (POST /instances/{id}/proposal): it is
    # accepted if the decision is the proposed one, rejected otherwise.
    proposal_id: int | None = None


class RuleSummary(BaseModel):
    id: int
    text: str
    type: str
    decision: str
    status: str
    fires: int  # instances whose latest engine decision has this rule firing


class SourceSummary(BaseModel):
    id: int
    name: str = Field(examples=["suppliers", "erp"])
    origin: str
    rows: int
    loaded_at: datetime


class ProcessSummary(BaseModel):
    """Everything a process page shows in one call."""

    id: int
    name: str
    instances: int
    by_status: dict[str, int] = Field(examples=[{"PENDING": 0, "DECIDED": 500}])
    by_decision: dict[str, int] = Field(examples=[{"PAGAR": 433, "NO_PAGAR": 36, "ESCALAR": 31}])
    # Sources whose pre-run sync failed or that were never loaded, name -> why; omitted when
    # none (ADR 0028).
    down_sources: dict[str, str] = {}
    queue: int  # latest decision is one a person must look at
    resolved: int  # instances whose latest decision a person took
    rules: list[RuleSummary]
    sources: list[SourceSummary]  # the current load of each source
    last_run_at: datetime | None  # the engine's most recent decision


class RunSummary(BaseModel):
    execution_id: int | None = None
    decision_ids: list[int] = []
    decided: int
    by_decision: dict[str, int] = Field(examples=[{"PAGAR": 433, "NO_PAGAR": 36, "ESCALAR": 31}])
    # Sources whose pre-run sync failed or that were never loaded, name -> why; omitted when
    # none (ADR 0028).
    down_sources: dict[str, str] = {}


class RunIn(BaseModel):
    instance_ids: list[int] = Field(min_length=1, max_length=500)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)


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


class ReprocessIn(BaseModel):
    names: list[str] | None = Field(None, examples=[["factura_1217.pdf"]])  # None: all


class ReprocessSummary(BaseModel):
    """What re-deciding the decided instances changed. Only `changes` got a new decision."""

    unchanged: int
    changes: list[ChangeOut]  # the engine decided it before and decides otherwise now
    conflicts: list[ChangeOut]  # a person decided it last; left alone, for the manager
    down_sources: dict[str, str] = {}  # as in RunSummary; omitted when none


class RunOut(BaseModel):
    """One stored execution (a run or a reprocess), read back from its row and its span."""

    id: int  # the execution id; decisions carry it as `execution_id`
    kind: str | None = Field(examples=["run", "reprocess"])  # None: stored before run history
    started_at: datetime
    finished_at: datetime | None
    author: str | None  # the manager who started it
    version_id: int
    version_number: int
    rules_hash: str | None
    instances: int  # instances the engine evaluated
    decided: int  # decisions this execution appended (a reprocess only writes changes)
    # The engine's outcome for every evaluated instance, written or not, so runs compare.
    by_decision: dict[str, int] = Field(examples=[{"PAGAR": 433, "NO_PAGAR": 36, "ESCALAR": 31}])
    escalated: int  # outcomes whose decision type requires a human
    escalation_reasons: dict[str, int] = Field(examples=[{"SOURCE_UNAVAILABLE": 3}])
    down_sources: dict[str, str] = {}
    trace_id: str | None  # `GET /traces/{trace_id}`


class RunDecisionOut(BaseModel):
    decision_id: int
    instance_id: int
    name: str
    decision: str
    reason: str | None
    created_at: datetime


class RunDetail(RunOut):
    decisions: list[RunDecisionOut]  # the rows this execution appended, by instance id


class FindingOut(BaseModel):
    id: int
    decision_id: int
    rule_id: int | None
    type: str
    detail: str | None
    created_at: datetime
