from pydantic import BaseModel, Field


class SymbolIO(BaseModel):
    name: str
    type: str = Field(examples=["text", "number", "date"])
    description: str = ""
    required: bool = False  # missing, None or blank -> the instance escalates (ADR 0016)


class DecisionTypeIO(BaseModel):
    name: str
    priority: int  # highest wins when several rules fire
    is_default: bool = False  # applies when no rule fires
    requires_human: bool = False  # goes to the human queue for a manager


class ProcessIn(BaseModel):
    name: str
    # The use case this process belongs to, by name; it must exist (`use-case.json` next to
    # the pack, loaded first). Without it the process gets a use case of its own, with the
    # same name and this `description`.
    use_case: str | None = None
    description: str | None = None
    decision_types: list[DecisionTypeIO]
    symbols: list[SymbolIO] = []


class ProcessOut(BaseModel):
    id: int
    name: str
    use_case_id: int
    description: str  # the use case's


class ProcessDetail(ProcessOut):
    decision_types: list[DecisionTypeIO]
    symbols: list[SymbolIO]
