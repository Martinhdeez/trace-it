from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Channel = Literal["escalation", "chat", "learning"]
Kind = Literal["decision", "rule", "context", "input", "source"]
Status = Literal["open", "accepted", "rejected", "superseded"]


class ManagerProposalOut(BaseModel):
    """One thing an agent proposes; only a manager accepts or rejects it."""

    id: int
    process_id: int
    instance_id: int | None  # the escalated case, for `kind: decision`
    channel: Channel
    kind: Kind
    summary: str
    rationale: str
    evidence: list[str]  # references: symbol:<name>, rule:<id>, case:<id>, chat:<n>...
    # decision: {proposed, why, options[{decision, consequence}], escalation_reason, ...}
    # escalation rule: {decision_id, engine_decision_id, replaces, text, summary, type,
    # decision, resolved_as, version_id} (ADR 0035)
    # chat: {draft_id, revision, review_key, before, after}; learning: {analysis_id, ...}
    payload: dict[str, Any]
    status: Status
    author: str  # the agent role: assistant, discovery, learner
    created_at: datetime
    resolved_by: str | None
    resolved_at: datetime | None
    # decision_id, draft revision, adoption or version; escalation rule: {reason, rule_id,
    # retired, draft_revision}; superseded: {cause} (ignored, version_published,
    # case_changed, superseded); rejected: {reason}
    outcome: dict[str, Any] | None


class SettleIn(BaseModel):
    reason: str = Field(default="", max_length=8000)


class AcceptIn(SettleIn):
    # Escalation rule suggestion only: the manager's edit of `payload.text`, compiled in
    # its place; the outcome records `edited` and `original_text`. Ignored elsewhere.
    text: str | None = Field(default=None, max_length=8000)
