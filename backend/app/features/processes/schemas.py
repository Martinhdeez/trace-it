from typing import Annotated, Literal

from pydantic import BaseModel, Field


class SymbolExtraction(BaseModel):
    """Optional hints for finding a process symbol in an input document."""

    labels: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=12
    )
    source: Literal["document", "filename", "text", "none"] = "document"


class SymbolIO(BaseModel):
    name: str
    type: str = Field(examples=["text", "number", "date"])
    description: str = ""
    required: bool = False  # missing, None or blank -> the instance escalates (ADR 0016)
    extraction: SymbolExtraction | None = None


class DecisionTypeIO(BaseModel):
    name: str
    priority: int  # highest wins when several rules fire
    is_default: bool = False  # applies when no rule fires
    requires_human: bool = False  # goes to the human queue for a manager


class DecisionReviewConfig(BaseModel):
    """Optional advice after the engine; any disagreement needs human approval."""

    guidance: str = Field(min_length=1)
    timeout_seconds: float = Field(default=30, gt=0, le=120)


class ProcessIn(BaseModel):
    name: str
    # The use case this process belongs to, by name; it must exist (`use-case.json` next to
    # the pack, loaded first). Without it the process gets a use case of its own, with the
    # same name and this `description`.
    use_case: str | None = None
    description: str | None = None
    decision_types: list[DecisionTypeIO]
    symbols: list[SymbolIO] = []
    decision_review: DecisionReviewConfig | None = None


class ProcessOut(BaseModel):
    id: int
    name: str
    use_case_id: int
    description: str  # the use case's


class ProcessDetail(ProcessOut):
    active_version_id: int | None = None
    decision_types: list[DecisionTypeIO]
    symbols: list[SymbolIO]
    decision_review: DecisionReviewConfig | None = None
