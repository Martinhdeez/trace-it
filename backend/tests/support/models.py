"""Scripted PydanticAI models, so agent tests run without network or keys."""

import json
from collections.abc import Callable
from typing import Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    RetryPromptPart,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel


def scripted(
    replies: list[dict[str, Any]], seen: list[list[ModelMessage]] | None = None
) -> FunctionModel:
    """A model that answers the agent's structured output with each dict in turn. `seen`
    collects the message history the model was shown on every call."""

    def answer(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if seen is not None:
            seen.append(list(messages))
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, replies.pop(0))])

    return FunctionModel(answer, model_name="fake/model")


def per_role(
    scripts: dict[str, list[dict[str, Any]]], seen: dict[str, list] | None = None
) -> Callable:
    """Replacement for `llm.model_for`: a scripted model per role."""
    models = {
        role: scripted(replies, None if seen is None else seen.setdefault(role, []))
        for role, replies in scripts.items()
    }
    return lambda role: models[role]


def user_prompt(messages: list[ModelMessage]) -> str:
    """The user prompt of a run, as the model saw it."""
    return next(p.content for m in messages for p in m.parts if isinstance(p, UserPromptPart))


def user_json(messages: list[ModelMessage]) -> dict[str, Any]:
    return json.loads(user_prompt(messages))


def retry_prompts(messages: list[ModelMessage]) -> list[str]:
    """What the validators told the model to fix, in order."""
    return [str(p.content) for m in messages for p in m.parts if isinstance(p, RetryPromptPart)]
