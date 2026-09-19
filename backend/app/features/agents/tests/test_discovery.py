import copy

import pytest

from app.features.agents import discovery, llm
from app.features.processes.tests.test_drafts import plan
from tests.support.models import per_role, retry_prompts


async def test_malformed_output_and_scalar_example_source_retry_without_relaxing_schema(
    monkeypatch,
):
    from pydantic_ai.messages import ModelResponse, ToolCallPart
    from pydantic_ai.models.function import FunctionModel

    correct = plan()
    correct["examples"][0]["sources"] = {"parameters": [{"cut_off_date": "2026-09-18"}]}
    bad = copy.deepcopy(correct)
    bad["examples"][0]["sources"] = {"parameters": "2026-09-18"}
    replies = ['{"name":"cut off', bad, correct]
    seen = []

    def answer(messages, info):
        seen.append(list(messages))
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, replies.pop(0))])

    monkeypatch.setattr(llm, "model_for", lambda _: FunctionModel(answer))
    data = {
        "plan": {},
        "reviews": {},
        "documents": {},
        "snapshots": {},
        "messages": [{"role": "user", "text": "Escalate above 100"}],
    }
    output = await discovery.discover(data, None)
    assert output.examples[0].sources == {"parameters": [{"cut_off_date": "2026-09-18"}]}
    feedback = " ".join(retry_prompts(seen[-1]))
    assert "json_invalid" in feedback
    assert "list_type" in feedback


async def test_fabricated_evidence_retried_and_conflicting_instructions_remain_visible(monkeypatch):
    correct = plan()
    bad = copy.deepcopy(correct)
    bad["rules"][0]["evidence"][0]["reference"] = "imaginary:Policy!Z99"
    seen = {}
    monkeypatch.setattr(llm, "model_for", per_role({"discovery": [bad, correct]}, seen))
    data = {
        "plan": {},
        "reviews": {},
        "documents": {},
        "snapshots": {},
        "messages": [{"role": "user", "text": "The old policy is wrong; escalate above 100"}],
    }
    output = await discovery.discover(data, None)
    assert output.rules[0].decision == "REVIEW"
    assert "imaginary" in " ".join(retry_prompts(seen["discovery"][-1]))


async def test_failed_model_does_not_invent_a_plan(monkeypatch):
    from tests.support.models import down

    monkeypatch.setattr(llm, "model_for", lambda _: down("offline"))
    data = {"plan": {}, "reviews": {}, "documents": {}, "snapshots": {}, "messages": []}
    with pytest.raises(llm.AgentError):
        await discovery.discover(data, None)


async def test_discussion_treats_authoring_guidance_as_context_not_published_policy(monkeypatch):
    from app.features.use_cases.schemas import AgentSettings
    from tests.support.models import instructions, user_json

    note = "During setup, ask whether VAT errors should escalate instead of reject."
    seen = {}
    monkeypatch.setattr(
        llm,
        "model_for",
        per_role(
            {
                "discovery": [
                    {
                        "message": "The rule rejects; the setup note suggests escalation.",
                        "evidence": ["rule:8"],
                    }
                ]
            },
            seen,
        ),
    )
    setup = llm.Setup(AgentSettings(instructions=note))
    data = {
        "plan": {},
        "reviews": {},
        "documents": {},
        "snapshots": {},
        "messages": [{"role": "user", "text": "Explain the current rule."}],
        "base_references": ["rule:8"],
    }
    await discovery.discuss(data, setup)
    messages = seen["discovery"][0]
    assert user_json(messages)["authoring_guidance"] == note
    assert note not in instructions(messages)
    assert setup.settings.instructions == note
