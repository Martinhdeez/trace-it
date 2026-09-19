"""The reviewable contract between discovery, the manager and compilation."""

from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.features.processes.definition import Definition
from app.features.processes.schemas import DecisionTypeIO, SymbolIO


class Evidence(BaseModel):
    reference: str  # workbook hash:sheet!cell, snapshot:name, chat:message number
    explanation: str


class SourceProposal(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    explanation: str
    evidence: list[Evidence] = Field(min_length=1)
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


class RuleProposal(BaseModel):
    name: str = Field(min_length=1)
    text: str = Field(min_length=1)
    type: Literal["requirement", "prohibition"]
    decision: str
    evidence: list[Evidence] = Field(min_length=1)


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
    sources: list[SourceProposal] = []
    rules: list[RuleProposal] = []
    examples: list[AcceptanceExample] = []
    questions: list[str] = []
    summary: str = "Describe the decision you want this process to make."

    @model_validator(mode="after")
    def unique_names(self) -> Self:
        for field in ("sources", "rules", "examples", "symbols", "decision_types"):
            names = [item.name for item in getattr(self, field)]
            if len(names) != len(set(names)):
                raise ValueError(f"Duplicate {field} names")
        return self

    def definition(self) -> Definition:
        return Definition(
            name=self.name,
            description=self.description,
            decision_types=self.decision_types,
            symbols=self.symbols,
            rules=[r.model_dump(exclude={"name", "evidence"}) for r in self.rules],
        )


class DraftStart(BaseModel):
    process_id: int | None = None
    use_case_id: int | None = None
    name: str = Field(default="", max_length=200)


class RevisionIn(BaseModel):
    revision: int = Field(ge=1)


class MessageIn(RevisionIn):
    message: str = Field(min_length=1, max_length=16000)


class ReviewIn(RevisionIn):
    proposal: str  # setup, source:name, rule:name, example:name
    disposition: Literal["accepted", "rejected"]
    explanation: str = Field(default="", max_length=4000)


class DraftOut(BaseModel):
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
