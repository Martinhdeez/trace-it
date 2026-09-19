"""Execution preferences stay explicit, isolated and pinned to the approved version."""

from copy import deepcopy

import pytest
from pydantic import ValidationError
from pydantic_ai import Agent

from app.core.config import settings
from app.features.agents import llm
from app.features.processes import execution
from app.features.use_cases.schemas import ROLES, AgentSettings
from app.features.versions import configuration
from app.features.versions.tests.test_api import client, publish, seed
from tests.support.models import scripted


def choices():
    return execution.ExecutionSettings(
        local_endpoint="http://localhost:11434/v1",
        agents={role: AgentSettings(model=f"local:{role}") for role in ROLES},
        extraction=execution.extraction_defaults(),
    )


def test_presets_are_editable_values_and_do_not_mutate_defaults(monkeypatch):
    original = choices()
    before = original.model_dump()
    monkeypatch.setattr(
        settings,
        "execution_presets",
        {"fastest": {"agents": {"compiler": {"model": "local:fast-code"}}}},
    )
    fastest = execution.preset(original, "fastest")
    quality = execution.preset(original, "highest_quality")
    assert fastest.agents["compiler"].model == "local:fast-code"
    assert fastest.agents["compiler"].timeout_seconds < quality.agents["compiler"].timeout_seconds
    assert not fastest.extraction.focused_verification
    assert quality.extraction.focused_verification
    fastest.agents["compiler"].model = "local:my-choice"
    fastest.extraction.dpi = 400
    assert original.model_dump() == before


@pytest.mark.parametrize("field", ["primary", "fallback", "vision", "judge"])
def test_local_only_rejects_hosted_models_in_every_path(field):
    value = choices().model_dump()
    value["local_only"] = True
    value["extraction"].update(vision_model=None, text_judge_model=None)
    if field == "primary":
        value["agents"]["discovery"]["model"] = "anthropic:hosted"
    elif field == "fallback":
        value["agents"]["tester"]["fallback_models"] = ["openai:hosted"]
    elif field == "vision":
        value["extraction"]["vision_model"] = "gemini:gemini-test"
    else:
        value["extraction"]["text_judge_model"] = "jev:test"
    with pytest.raises(ValidationError, match="[Ll]ocal-only"):
        execution.ExecutionSettings.model_validate(value)


@pytest.mark.parametrize(
    "patch",
    [
        {"dpi": 0},
        {"vision_timeout_seconds": -1},
        {"unknown": True},
        {"vision_model": "unknown:model"},
        {"text_judge_model": "local:"},
    ],
)
def test_invalid_extraction_configuration_is_rejected(patch):
    value = choices().model_dump()
    value["extraction"].update(patch)
    with pytest.raises(ValidationError):
        execution.ExecutionSettings.model_validate(value)


def test_local_guard_checks_whole_fallback_chain_before_resolving(monkeypatch):
    def unexpected(*args):
        pytest.fail("Local-only guard must run before creating any provider")

    monkeypatch.setattr(llm, "resolve", unexpected)
    setup = llm.Setup(
        AgentSettings(model="local:primary", fallback_models=["openai:remote"]), local_only=True
    )
    with pytest.raises(llm.AgentError, match="local-only"):
        llm.chain(setup, "compiler", [])


def test_local_adapter_uses_pinned_endpoint_without_cloud_credentials(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LOCAL_LLM_API_KEY", raising=False)
    model = llm.resolve("local:code-model", "http://127.0.0.1:1234/v1")
    assert model.model_name == "code-model"
    assert str(model.client.base_url) == "http://127.0.0.1:1234/v1/"


async def test_manual_retry_and_request_limits_reach_the_agent(monkeypatch):
    from pydantic import BaseModel

    class Answer(BaseModel):
        number: int

    calls = []
    model = scripted([{"number": "invalid"}, {"number": 2}], calls)
    monkeypatch.setattr(llm, "model_for", lambda role: model)
    setup = llm.Setup(AgentSettings(retries=0, request_limit=1))
    with pytest.raises(llm.AgentError):
        await llm.run(
            Agent(None, output_type=Answer), "compiler", "answer", instructions="test", setup=setup
        )
    assert len(calls) == 1


async def test_process_configuration_is_published_atomically_and_stays_pinned(monkeypatch):
    async with client() as api:
        pid, headers, _, _ = await seed(api)
        initial = await publish(api, pid, headers)
        endpoint = f"/processes/{pid}/execution"
        current = (await api.get(endpoint, headers=headers)).json()
        selected = current["presets"]["fastest"]["settings"]
        selected["agents"]["compiler"]["model"] = "local:manual-code"
        selected["agents"]["compiler"]["retries"] = 3
        selected["extraction"]["dpi"] = 360
        saved = await api.put(
            f"/processes/{pid}/draft", headers=headers, json={"execution": selected}
        )
        assert saved.status_code == 200, saved.text
        draft = saved.json()
        assert draft["snapshot"]["execution"]["preset"] == "custom"
        previous = (await api.get(f"/process-versions/{initial['id']}")).json()
        assert previous["snapshot"] == initial["snapshot"]
        stale = await api.put(
            f"/processes/{pid}/draft", headers=headers, json={"execution": selected}
        )
        assert stale.status_code == 409
        published = await publish(api, pid, headers)
        monkeypatch.setattr(settings, "compiler_model", "local:changed-default")
        setup = configuration.setups(published["snapshot"])["compiler"]
        assert setup.settings.model == "local:manual-code"
        assert setup.settings.retries == 3
        assert setup.execution_hash
        assert published["snapshot"]["execution"]["extraction"]["dpi"] == 360
        assert (await api.get(endpoint, headers=headers)).json()["revision"] is None


async def test_processes_share_defaults_but_not_manual_changes():
    async with client() as api:
        first, headers, _, _ = await seed(api)
        second, other_headers, _, _ = await seed(api)
        before = (await api.get(f"/processes/{second}/execution", headers=other_headers)).json()
        response = (await api.get(f"/processes/{first}/execution", headers=headers)).json()
        config = response["settings"]
        config["agents"]["learner"]["model"] = "local:custom-learner"
        result = await api.put(
            f"/processes/{first}/draft",
            headers=headers,
            json={
                "execution": config,
                "expected_revision": response["revision"],
            },
        )
        assert result.status_code == 200, result.text
        after = (await api.get(f"/processes/{second}/execution", headers=other_headers)).json()
        assert before == after


async def test_api_rejects_hosted_local_only_config_without_creating_a_revision():
    async with client() as api:
        pid, headers, _, _ = await seed(api)
        response = (await api.get(f"/processes/{pid}/execution", headers=headers)).json()
        invalid = deepcopy(response["settings"])
        invalid["local_only"] = True
        result = await api.put(
            f"/processes/{pid}/draft",
            headers=headers,
            json={
                "execution": invalid,
                "expected_revision": response["revision"],
            },
        )
        assert result.status_code == 422
        assert (await api.get(f"/processes/{pid}/execution", headers=headers)).json() == response


async def test_discovery_pins_manual_models_before_any_process_exists(monkeypatch):
    from app.features.processes.tests.test_drafts import plan

    selected = choices()
    selected.extraction.vision_model = selected.extraction.text_judge_model = None
    selected.local_only = True
    calls = []
    model = scripted([plan()])

    def resolve(name, endpoint=None):
        calls.append((name, endpoint))
        return model

    monkeypatch.setattr(llm, "resolve", resolve)
    async with client() as api:
        _, headers, _, _ = await seed(api)
        response = await api.post(
            "/process-drafts",
            headers=headers,
            json={
                "execution": selected.model_dump(mode="json"),
            },
        )
        assert response.status_code == 201, response.text
        draft = response.json()
        response = await api.post(
            f"/process-drafts/{draft['id']}/messages",
            headers=headers,
            json={
                "revision": draft["revision"],
                "message": "Escalate amounts above 100",
                "mode": "revise",
            },
        )
        assert response.status_code == 200, response.text
        assert calls == [("local:discovery", selected.local_endpoint)]
        discussed = response.json()
        selected.agents["discovery"].model = "local:another-model"
        response = await api.put(
            f"/process-drafts/{draft['id']}/execution",
            headers=headers,
            json={
                "revision": discussed["revision"],
                "execution": selected.model_dump(mode="json"),
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["execution"]["agents"]["discovery"]["model"] == "local:another-model"
        assert response.json()["reviews"] == {}
        assert response.json()["preview"] is None


async def test_bad_deployment_preset_does_not_block_manual_settings(monkeypatch):
    monkeypatch.setattr(
        settings,
        "execution_presets",
        {
            "fastest": {"agents": {"not_a_role": {"model": "local:test"}}},
        },
    )
    async with client() as api:
        pid, headers, _, _ = await seed(api)
        result = await api.get(f"/processes/{pid}/execution", headers=headers)
        assert result.status_code == 200
        data = result.json()
        assert "error" in data["presets"]["fastest"]
        selected = data["settings"]
        selected["preset"] = "fastest"
        selected["agents"]["compiler"]["model"] = "local:manual"
        response = await api.put(
            f"/processes/{pid}/draft",
            headers=headers,
            json={
                "execution": selected,
                "expected_revision": data["revision"],
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["snapshot"]["execution"]["preset"] == "custom"
