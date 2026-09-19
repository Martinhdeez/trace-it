"""The reviewable contract between discovery, the manager and compilation."""

from datetime import datetime
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.features.processes.definition import Definition
from app.features.processes.execution import ExecutionSettings
from app.features.processes.schemas import DecisionReviewConfig, DecisionTypeIO, SymbolIO
from app.features.sources.http_connector import HttpSourceConfig


class ProposalEvidence(BaseModel):
    reference: str  # workbook hash:sheet!cell, snapshot:name, chat:message number
    explanation: str


class SourceProposal(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    explanation: str
    evidence: list[ProposalEvidence] = Field(min_length=1)
    kind: Literal["workbook", "snapshot", "constant"]
    document: str = ""  # workbook content hash
    sheet: str = ""
    first_row: int = Field(default=2, ge=1)
    last_row: int = Field(default=2, ge=1)
    columns: dict[str, Annotated[str, Field(pattern=r"^[A-Z]{1,3}$")]] = Field(
        default_factory=dict,
        description='Output field name to Excel column letter, e.g. {"supplier_id": "A"}, '
        'never {"A": "supplier_id"}.',
    )
    snapshot: str = ""
    rows: list[dict[str, Any]] = []  # constants only, approved as part of this proposal
    operation: Literal["replace", "append", "upsert", "delete"] = "replace"
    key: list[str] = Field(
        default_factory=list,
        description="Canonical output fields identifying a row for append/upsert/delete.",
    )

    @model_validator(mode="after")
    def valid_mutation(self) -> Self:
        if self.operation in {"upsert", "delete"} and not self.key:
            raise ValueError(f"Source operation {self.operation} requires a key")
        available = set(self.columns)
        if self.kind == "constant":
            available.update(field for row in self.rows for field in row)
        if self.kind != "snapshot" and (unknown := set(self.key) - available):
            raise ValueError(f"Source key fields are not mapped: {sorted(unknown)}")
        return self


class ConnectorProposal(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    explanation: str
    evidence: list[ProposalEvidence] = Field(min_length=1)
    config: HttpSourceConfig
    required: list[str] = Field(min_length=1)
    optional: list[str] = []
    sync_before_run: bool = True


class RuleProposal(BaseModel):
    name: str = Field(min_length=1)
    text: str = Field(min_length=1)
    summary: str = ""  # one plain line for a non-technical reader
    type: Literal["requirement", "prohibition"]
    decision: str
    evidence: list[ProposalEvidence] = Field(min_length=1)


class GuidanceProposal(BaseModel):
    name: str = Field(min_length=1)
    text: str = Field(min_length=1)
    evidence: list[ProposalEvidence] = Field(min_length=1)


class AcceptanceExample(BaseModel):
    name: str = Field(min_length=1)
    instance: dict[str, Any]
    sources: dict[str, list[dict[str, Any]]] = {}
    others: list[dict[str, Any]] = []
    decision: str
    explanation: str


class DraftPlan(BaseModel):
    name: str = ""
    description: str = ""
    decision_types: list[DecisionTypeIO] = []
    symbols: list[SymbolIO] = []
    connectors: list[ConnectorProposal] = []
    sources: list[SourceProposal] = []
    rules: list[RuleProposal] = []
    decision_review: DecisionReviewConfig | None = None
    guidance: list[GuidanceProposal] = []
    examples: list[AcceptanceExample] = []
    questions: list[str] = []
    summary: str = "Describe the decision you want this process to make."

    @model_validator(mode="after")
    def unique_names(self) -> Self:
        for field in (
            "connectors",
            "sources",
            "rules",
            "guidance",
            "examples",
            "symbols",
            "decision_types",
        ):
            names = [item.name for item in getattr(self, field)]
            if len(names) != len(set(names)):
                raise ValueError(f"Duplicate {field} names")
        source_names = {source.name for source in self.sources}
        if unknown := {connector.name for connector in self.connectors} - source_names:
            raise ValueError(f"Connectors need matching source proposals: {sorted(unknown)}")
        return self

    def definition(self) -> Definition:
        return Definition(
            name=self.name,
            description=self.description,
            decision_types=self.decision_types,
            symbols=[s.model_dump() for s in self.symbols],  # checked as input here
            decision_review=self.decision_review,
            rules=[r.model_dump(exclude={"name", "evidence"}) for r in self.rules],
        )


class DraftStart(BaseModel):
    execution: ExecutionSettings | None = None
    process_id: int | None = None
    use_case_id: int | None = None
    name: str = Field(default="", max_length=200)


class RevisionIn(BaseModel):
    revision: int = Field(ge=1)


class ExecutionIn(RevisionIn):
    execution: ExecutionSettings


class MessageIn(RevisionIn):
    mode: Literal["discuss", "revise"] = "discuss"
    message: str = Field(min_length=1, max_length=16000)


class ReviewIn(RevisionIn):
    proposal: str  # setup, source:name, rule:name, example:name
    disposition: Literal["accepted", "rejected"]
    explanation: str = Field(default="", max_length=4000)


class DiscoveryDraftOut(BaseModel):
    execution: ExecutionSettings | None = None
    # The audit trail of the last agent run on this draft: `GET /traces/{trace_id}` returns
    # its tree, every model call with the instructions it saw and the output it gave.
    trace_id: str | None = None
    id: int
    revision: int
    process_id: int | None
    published_process_id: int | None
    plan: DraftPlan
    reviews: dict[str, str]
    messages: list[dict[str, Any]]
    documents: list[dict[str, Any]]
    snapshots: list[dict[str, Any]]
    connectors: list[str]
    preview: dict[str, Any] | None
    changes: list[dict[str, Any]] = []


class Discussion(BaseModel):
    message: str = Field(min_length=1)
    evidence: list[str] = []
    questions: list[str] = []


class DiscoverySessionSummary(BaseModel):
    id: int
    name: str
    revision: int
    process_id: int | None
    published_process_id: int | None


class DiscoveryRevisionOut(BaseModel):
    revision: int
    author_id: int
    created_at: datetime
    plan: dict[str, Any]
    reviews: dict[str, Any]
    messages: list[dict[str, Any]]
    preview: dict[str, Any] | None
    published_rule_ids: list[int]
    retired_rule_ids: list[int]
