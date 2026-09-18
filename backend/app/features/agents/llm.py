"""Every agent runs on PydanticAI (ADR 0006): typed output, bounded retries, one seam.

A role names a model in `Settings` (`provider:model`); `run` records what the model did and
turns every failure into one error the API answers with. Tests swap the model with
`agent.override(model=FunctionModel(...))` or by monkeypatching `model_for`: no network.
"""

import time
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, AgentRunError
from pydantic_ai.exceptions import FallbackExceptionGroup
from pydantic_ai.messages import RetryPromptPart
from pydantic_ai.models import Model

from app.common.exceptions import TraceError
from app.core.config import settings


class AgentError(TraceError):
    """The model failed, or gave nothing valid within the retries. Nothing is stored."""

    status_code = 502
    code = "llm_error"


@dataclass(frozen=True)
class Trace:
    """What one agent run cost, for the events table."""

    role: str
    model: str
    requests: int
    retries: int  # answers the validators rejected and the model was asked to fix
    input_tokens: int
    output_tokens: int
    cost: float | None
    latency_ms: int

    def as_data(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "model": self.model,
            "requests": self.requests,
            "retries": self.retries,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


def model_for(role: str) -> Model | str:
    """The model configured for a role (`TRACE_<ROLE>_MODEL`)."""
    return getattr(settings, f"{role}_model")


def _cost(usage: Any) -> float | None:
    try:
        cost = usage.cost()
        return float(getattr(cost, "total_price", cost))
    except Exception:  # noqa: BLE001 - unknown price: the run still succeeded
        return None


async def run(agent: Agent, role: str, prompt: str, *, deps: Any = None) -> tuple[Any, Trace]:
    """One agent run for `role`. Returns the validated output and its trace."""
    model = model_for(role)
    start = time.perf_counter()
    try:
        result = await agent.run(prompt, model=model, deps=deps)
    except (AgentRunError, FallbackExceptionGroup, TimeoutError) as error:
        raise AgentError(f"{role}: {type(error).__name__}: {error}") from error
    latency_ms = int((time.perf_counter() - start) * 1000)
    usage = result.usage
    retries = sum(
        isinstance(part, RetryPromptPart) for m in result.all_messages() for part in m.parts
    )
    trace = Trace(
        role=role,
        model=result.response.model_name or str(model),
        requests=usage.requests,
        retries=retries,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cost=_cost(usage),
        latency_ms=latency_ms,
    )
    return result.output, trace
