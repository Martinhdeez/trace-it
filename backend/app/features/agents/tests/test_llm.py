"""`llm.run`: the platform prompt plus the use case's guidance, model and trace."""

import hashlib

import pytest
from pydantic import BaseModel
from pydantic_ai import Agent

from app.features.agents import llm
from app.features.use_cases.schemas import AgentSettings
from tests.support.models import instructions, per_role


class Answer(BaseModel):
    text: str


agent = Agent(None, output_type=Answer)
SETUP = llm.Setup(AgentSettings(instructions="Amounts in cents."), config_id=42)


async def test_guidance_is_appended_and_traced(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict = {}
    monkeypatch.setattr(llm, "model_for", per_role({"compiler": [{"text": "ok"}]}, seen))

    output, trace = await llm.run(agent, "compiler", "hi", instructions="PLATFORM", setup=SETUP)

    effective = "PLATFORM\n\n## Guidance for this use case\nAmounts in cents."
    assert output == Answer(text="ok")
    assert instructions(seen["compiler"][0]) == effective
    assert trace.config_id == 42
    assert trace.prompt_hash == hashlib.sha256(effective.encode()).hexdigest()[:12]


async def test_the_setup_model_overrides_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    def default(role: str):
        raise AssertionError("the default model must not be used")

    monkeypatch.setattr(llm, "model_for", default)
    setup = llm.Setup(AgentSettings(model="test"))

    _, trace = await llm.run(agent, "compiler", "hi", instructions="PLATFORM", setup=setup)

    assert trace.model == "test"
