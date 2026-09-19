from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class RuleIn(BaseModel):
    text: str
    type: Literal["requirement", "prohibition"]
    decision: str  # must be one of the process's decision types


class RuleOut(BaseModel):
    id: int
    process_id: int
    text: str
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
