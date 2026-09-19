"""Every agent runs on PydanticAI (ADR 0006): typed output, bounded retries, one seam.

What an agent does is not in the code (ADR 0011). Its platform prompt is a file under
`prompts/` (the contract, the same for every use case); how it works in a use case (model,
domain guidance, model settings, limits, examples) is a versioned `AgentConfig` of that use
case, passed here as a `Setup`. `run` joins both, records the config and prompt hash with
what the model did, and turns every failure into one error the API answers with. Tests swap
the model by monkeypatching `model_for`: no network.
"""

import hashlib
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, AgentRunError
from pydantic_ai.exceptions import FallbackExceptionGroup
from pydantic_ai.messages import RetryPromptPart
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.common.exceptions import TraceError
from app.core.config import settings
from app.features.use_cases.schemas import AgentSettings

PROMPTS = Path(__file__).parent / "prompts"


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
    config_id: int | None = None  # the AgentConfig version it ran with (None: defaults)
    prompt_hash: str = ""  # sha256[:12] of the effective instructions

    def as_data(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "model": self.model,
            "config_id": self.config_id,
            "prompt_hash": self.prompt_hash,
            "requests": self.requests,
            "retries": self.retries,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


@dataclass(frozen=True)
class Setup:
    """How a role runs in a use case: the active AgentConfig version, or the defaults."""

    settings: AgentSettings = field(default_factory=AgentSettings)
    config_id: int | None = None

    def limit(self, name: str, default: float) -> float:
        return self.settings.limits.get(name, default)


def prompt(*names: str) -> str:
    """The platform prompts `prompts/<name>.md`, joined."""
    return "\n\n".join((PROMPTS / f"{n}.md").read_text(encoding="utf-8").strip() for n in names)


def model_for(role: str) -> Model | str:
    """The model configured for a role (`TRACE_<ROLE>_MODEL`)."""
    return getattr(settings, f"{role}_model")


def resolve(model: Model | str) -> Model | str:
    """`helmcode:<model>` runs on Helmcode's OpenAI-compatible API (EU inference, key in
    `HELMCODE_API_KEY`); any other `provider:model` string goes to PydanticAI as is."""
    if isinstance(model, str) and model.startswith("helmcode:"):
        provider = OpenAIProvider(
            base_url=settings.helmcode_base_url, api_key=os.environ.get("HELMCODE_API_KEY")
        )
        return OpenAIChatModel(model.removeprefix("helmcode:"), provider=provider)
    return model


def _cost(usage: Any) -> float | None:
    try:
        cost = usage.cost()
        return float(getattr(cost, "total_price", cost))
    except Exception:  # noqa: BLE001 - unknown price: the run still succeeded
        return None


async def run(
    agent: Agent,
    role: str,
    user_prompt: str,
    *,
    instructions: str,
    setup: Setup | None = None,
    deps: Any = None,
) -> tuple[Any, Trace]:
    """One agent run for `role`: the platform `instructions` plus the use case's guidance,
    with the use case's model and settings. Returns the validated output and its trace."""
    setup = setup or Setup()
    if setup.settings.instructions:
        instructions += "\n\n## Guidance for this use case\n" + setup.settings.instructions
    model = resolve(setup.settings.model or model_for(role))
    start = time.perf_counter()
    try:
        result = await agent.run(
            user_prompt,
            model=model,
            deps=deps,
            instructions=instructions,
            model_settings=setup.settings.model_settings or None,
        )
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
        config_id=setup.config_id,
        prompt_hash=hashlib.sha256(instructions.encode()).hexdigest()[:12],
    )
    return result.output, trace
