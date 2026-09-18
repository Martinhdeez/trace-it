from pydantic import BaseModel, Field


class SymbolIO(BaseModel):
    name: str
    type: str = Field(examples=["text", "number", "date"])
    description: str = ""


class DecisionTypeIO(BaseModel):
    name: str
    priority: int  # highest wins when several rules fire
    is_default: bool = False  # applies when no rule fires
    requires_human: bool = False  # goes to the human queue for a manager


class ProcessIn(BaseModel):
    name: str
    description: str = ""
    decision_types: list[DecisionTypeIO]
    symbols: list[SymbolIO] = []


class ProcessOut(BaseModel):
    id: int
    name: str
    description: str


class ProcessDetail(ProcessOut):
    decision_types: list[DecisionTypeIO]
    symbols: list[SymbolIO]
