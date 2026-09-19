from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# compiler: writes a rule's code; tester: writes its tests and reviews disputes;
# assistant: suggests how to resolve an escalated case; normalizer: turns a norm in
# natural language into rule texts.
Role = Literal["compiler", "tester", "assistant", "normalizer", "decision_reviewer", "learner"]
ROLES: tuple[Role, ...] = (
    "compiler",
    "tester",
    "assistant",
    "normalizer",
    "decision_reviewer",
    "learner",
)


class Example(BaseModel):
    """A rule of this use case and code a person approved for it: shown to the compiler as
    a model of the use case's conventions, never for the rule being compiled."""

    text: str
    type: Literal["requirement", "prohibition"]
    code: str


class AgentSettings(BaseModel):
    """How one agent role works in a use case. Empty fields fall back to the platform
    defaults (`TRACE_<ROLE>_MODEL`, the limits in `agents/compiler.py`)."""

    model: str | None = Field(None, examples=["helmcode:deepseek-v4-flash"])
    # Tried in order when the model before fails at the provider (5xx, 429 after the SDK's
    # retries, timeout, connection) or its answer is cut by the output-token limit; a
    # rejected answer (ModelRetry) never switches (ADR 0019).
    fallback_models: list[str] = Field([], examples=[["helmcode:glm5.3-flash"]])
    # Per request to the provider; None: the provider's own default.
    timeout_seconds: float | None = None
    # Domain guidance appended to the role's platform prompt.
    instructions: str = ""
    # PydanticAI model settings, e.g. {"temperature": 0}.
    model_settings: dict[str, Any] = {}
    # compiler: max_attempts, auto_activate_max_change; tester: min_tests, max_reviews.
    limits: dict[str, float] = {}
    examples: list[Example] = []
    # normalizer: the decision of a check whose failure the norm does not name (ADR 0017).
    # A decision type of the process, never the default. None: the prompt's own fallbacks.
    failed_check_decision: str | None = None


class UseCaseOut(BaseModel):
    id: int
    name: str
    description: str


class AgentConfigOut(BaseModel):
    id: int
    role: str
    version: int
    config: AgentSettings
    active: bool
    author: str
    note: str | None
    created_at: datetime


class UseCaseDetail(UseCaseOut):
    agents: list[AgentConfigOut]  # the active version of each configured role


class AgentConfigIn(BaseModel):
    config: AgentSettings
    note: str | None = None


class UseCaseDefinition(BaseModel):
    """A use case as data: `processes/<pack>/use-case.json`."""

    name: str
    description: str = ""
    agents: dict[Role, AgentSettings] = {}
