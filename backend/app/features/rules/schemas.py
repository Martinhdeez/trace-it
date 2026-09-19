from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class RuleIn(BaseModel):
    text: str
    summary: str | None = None  # one plain line for the console; `text` is what compiles
    type: Literal["requirement", "prohibition"]
    decision: str  # must be one of the process's decision types


class RuleOut(BaseModel):
    id: int
    process_id: int
    norm_rule_id: int | None  # the sentence of the client's norm it checks, if any
    text: str
    summary: str | None
    type: str
    decision: str
    status: str
    hash: str | None
    report: dict[str, Any] | None
    created_at: datetime
    activated_at: datetime | None


class RuleDetail(RuleOut):
    code: str | None
    tests: list[dict[str, Any]] | None


class CheckOut(BaseModel):
    id: int
    text: str
    summary: str | None
    decision: str
    status: str


class NormRuleOut(BaseModel):
    id: int
    number: int
    text: str  # the sentence exactly as the client wrote it
    policies: list[str]
    created_at: datetime
    rules: list[CheckOut]  # its atomic checks
