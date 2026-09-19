from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AlertOut(BaseModel):
    id: int
    process_id: int
    instance_id: int
    name: str
    decision_id: int  # the decision flagged; never edited
    before: str
    after: str  # what the engine would decide now
    trigger: dict[str, Any]  # source_sync (sources, rows involved) or rule_change (rule ids)
    evidence: dict[str, Any]  # reason codes before and after
    status: str  # open, acknowledged or resolved
    resolved_by_decision_id: int | None  # the later decision that resolved it
    acknowledged_by: str | None
    acknowledged_at: datetime | None
    note: str | None
    created_at: datetime


class AckIn(BaseModel):
    note: str | None = None
