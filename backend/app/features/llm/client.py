"""One interface for every LLM provider (P22). The model per role lives in `llm_config`."""

import time
from dataclasses import dataclass
from typing import Any

import litellm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.features.llm.model import LLMConfig


@dataclass(frozen=True)
class Reply:
    content: str
    model: str
    cost: float | None
    latency_ms: int


async def complete(
    session: AsyncSession,
    role: str,
    messages: list[dict[str, Any]],
    response_format: type[BaseModel] | None = None,
) -> Reply:
    """Call the model configured for `role`. With `response_format`, the reply is JSON that
    validates against it (`response_format.model_validate_json(reply.content)`)."""
    config = await session.get(LLMConfig, role)
    if config is None:
        raise NotFoundError(f"No model configured for role {role!r}")
    start = time.perf_counter()
    response = await litellm.acompletion(
        model=config.model, messages=messages, response_format=response_format
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    try:
        cost = litellm.completion_cost(completion_response=response)
    except Exception:  # unknown price for this model: the call still succeeded
        cost = None
    return Reply(
        content=response.choices[0].message.content or "",
        model=config.model,
        cost=cost,
        latency_ms=latency_ms,
    )
