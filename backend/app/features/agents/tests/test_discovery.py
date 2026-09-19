import copy

import pytest

from app.features.agents import discovery, llm
from app.features.processes.tests.test_drafts import plan
from tests.support.models import per_role, retry_prompts


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
