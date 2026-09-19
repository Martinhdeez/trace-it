from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)]


class AnalysisIn(BaseModel):
    case_limit: int = Field(default=30, ge=2, le=100)


class ProposedNorm(BaseModel):
    kind: Literal["deterministic", "guidance"]
    text: Text
    reasoning: Text
    evidence: list[str] = Field(min_length=1, max_length=100)
    counterexamples: list[str] = Field(default_factory=list, max_length=100)
    limitations: Text


class DefinitionChange(BaseModel):
    """A change to the process definition itself, not a norm. Accepting one stages it in
    the version draft (context, input) or records it (source); it is never published here."""

    kind: Literal["context", "input", "source"]  # description, symbol, source of truth
    name: str = Field(default="", pattern=r"^([a-z][a-z0-9_]*)?$")  # symbol or source
    type: str = ""  # symbol type: text, number, date...
    text: Text  # a convention to add, what the symbol holds, what the source provides
    reasoning: Text
    evidence: list[str] = Field(min_length=1, max_length=100)


class LearningOutput(BaseModel):
    reasoning: Text
    proposals: list[ProposedNorm] = Field(default_factory=list, max_length=5)
    definition_changes: list[DefinitionChange] = Field(default_factory=list, max_length=5)


class ValidationOut(BaseModel):
    id: int
    proposal_id: int
    author: str
    baseline: str
    snapshot: dict[str, Any]
    report: dict[str, Any]
    created_at: datetime


class AdoptionOut(BaseModel):
    id: int
    validation_id: int | None
    approved: bool
    author: str
    reason: str
    snapshot: dict[str, Any]
    created_at: datetime


class ProposalOut(ProposedNorm):
    id: int
    analysis_id: int
    validations: list[ValidationOut] = []
    adoption: AdoptionOut | None = None


class AnalysisOut(BaseModel):
    id: int
    process_id: int
    author: str
    reasoning: str
    snapshot: dict[str, Any]
    created_at: datetime
    proposals: list[ProposalOut] = []


class ApproveIn(BaseModel):
    validation_id: int
    reason: Text


class RejectIn(BaseModel):
    reason: Text
