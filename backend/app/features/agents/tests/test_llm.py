"""`llm.run`: the platform prompt plus the use case's guidance, model and trace."""

import hashlib
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.messages import ModelResponse
from pydantic_ai.models.function import FunctionModel

from app.core import events
from app.core.database import session_factory
from app.features.agents import llm
from app.features.use_cases import service as use_cases
from app.features.use_cases.schemas import AgentSettings
from app.main import app
from tests.support.models import down, instructions, per_role, scripted


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


def chain(monkeypatch: pytest.MonkeyPatch, *models) -> llm.Setup:
    """A setup whose model and fallbacks are the scripted `models`, in order."""
    by_name = {m.model_name: m for m in models}
    monkeypatch.setattr(llm, "resolve", lambda name: by_name[name])
    primary, *fallbacks = by_name
    return llm.Setup(AgentSettings(model=primary, fallback_models=fallbacks))


async def run_traced(run_agent: Agent, setup: llm.Setup) -> tuple[object, dict]:
    """The run's output (or its AgentError) and the data of its `llm_run` span."""
    with events.span("test") as outer:
        try:
            output = await llm.run(run_agent, "compiler", "hi", instructions="P", setup=setup)
        except llm.AgentError as e:
            output = e
    return output, next(r["data"] for r in outer.rows if r["step"] == "llm_run")


async def test_a_provider_failure_moves_to_the_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    setup = chain(monkeypatch, down("primary"), scripted([{"text": "ok"}], name="backup"))

    (output, trace), span = await run_traced(agent, setup)

    assert output == Answer(text="ok")
    assert trace.model == span["model"] == "backup"
    assert span["chain"] == ["primary", "backup"]
    assert [f["model"] for f in span["failed_attempts"]] == ["primary"]
    assert "status_code: 503" in span["failed_attempts"][0]["error"]


async def test_an_answer_cut_by_the_token_limit_moves_to_the_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def cut(messages, info) -> ModelResponse:
        return ModelResponse(parts=[], finish_reason="length")

    primary = FunctionModel(cut, model_name="primary")
    setup = chain(monkeypatch, primary, scripted([{"text": "ok"}], name="backup"))

    (output, trace), span = await run_traced(agent, setup)

    assert output == Answer(text="ok")
    assert trace.model == "backup"
    assert span["failed_attempts"] == [{"model": "primary", "error": "output token limit hit"}]


picky = Agent(None, output_type=Answer)


@picky.output_validator
def _not_bad(answer: Answer) -> Answer:
    if answer.text == "bad":
        raise ModelRetry("say ok")
    return answer


async def test_a_rejected_answer_is_retried_on_the_same_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = scripted([{"text": "bad"}, {"text": "ok"}], name="primary")
    setup = chain(monkeypatch, primary, down("backup"))

    (output, trace), span = await run_traced(picky, setup)

    assert output == Answer(text="ok")
    assert (trace.model, trace.retries) == ("primary", 1)
    assert span["failed_attempts"] == []


async def test_when_every_model_fails_the_run_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup = chain(monkeypatch, down("primary"), down("backup"))

    error, span = await run_traced(agent, setup)

    assert isinstance(error, llm.AgentError) and error.status_code == 502
    assert "every model failed: primary: " in error.message and "; backup: " in error.message
    assert [f["model"] for f in span["failed_attempts"]] == ["primary", "backup"]


async def test_a_rule_whose_models_all_fail_is_blocked_with_the_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Through the API: the use case's chain is used and a compilation it cannot serve
    leaves the rule `blocked` (it escalates, ADR 0020), never stuck in `compiling`."""
    monkeypatch.setattr(llm, "resolve", lambda name: down(name))
    suffix = uuid.uuid4().hex[:8]
    definition = {
        "name": f"fallback-{suffix}",
        "decision_types": [
            {"name": "ESCALATE", "priority": 2, "requires_human": True},
            {"name": "PAY", "priority": 1, "is_default": True},
        ],
        "symbols": [{"name": "amount", "type": "number"}],
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as api:
        r = await api.post("/processes/definition", json=definition)
        assert r.status_code == 200, r.text
        process = r.json()["process"]
        chain_settings = AgentSettings(model="primary", fallback_models=["backup"])
        async with session_factory() as session:
            for role in ("tester", "compiler"):
                await use_cases.configure(
                    session, process["use_case_id"], role, chain_settings, "test", None
                )
        r = await api.post(
            f"/processes/{process['id']}/rules",
            json={"text": "amount > 1000", "type": "prohibition", "decision": "ESCALATE"},
        )
        assert r.status_code == 201, r.text
        rule = (await api.get(f"/rules/{r.json()['id']}")).json()

    assert rule["status"] == "blocked"
    assert rule["report"]["valid"] is False
    assert "every model failed: primary: " in rule["report"]["error"]
    assert "; backup: " in rule["report"]["error"]
