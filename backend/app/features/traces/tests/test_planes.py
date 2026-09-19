"""The three monitoring planes (ADR 0018): every span name in exactly one, their metrics per
process and across processes, their health and the live stream. Models are scripted."""

import ast
import uuid
from pathlib import Path

import pytest
from pydantic import BaseModel
from pydantic_ai import Agent

from app.core import events
from app.core.config import settings
from app.core.database import session_factory
from app.features.agents import llm
from app.features.decisions.tests.test_api import FAKE_SANDBOX, client, create_process
from app.features.traces import service
from app.features.traces.schemas import Plane
from app.features.use_cases.schemas import AgentSettings
from tests.support.models import down, scripted

ROOT = Path(__file__).resolve().parents[5]  # the repository
EMITTERS = {"events.span", "events.record", "_status_span"}


def emitted_steps() -> set[str]:
    """Every span name the code writes: the first string argument of `events.span`,
    `events.record` and `_status_span`, outside tests."""
    steps = set()
    for folder in (ROOT / "backend" / "app", ROOT / "tools"):
        for path in folder.rglob("*.py"):
            if "tests" in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Call) and ast.unparse(node.func) in EMITTERS:
                    # `_status_span` passes its own argument on: its callers name the step.
                    steps.update([a.value for a in node.args if isinstance(a, ast.Constant)][:1])
    return steps


def test_every_span_name_has_exactly_one_plane() -> None:
    steps = emitted_steps()
    assert {"llm_run", "run_process", "upload_document", "activate_rule"} <= steps
    assert steps - set(service.PLANES) == set(), "spans with no plane: add them to PLANES"
    assert set(service.PLANES) - steps == set(), "planes for spans nothing emits"


class Answer(BaseModel):
    text: str


async def test_the_three_planes_of_a_process(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.features.agents import sandbox

    monkeypatch.setattr(sandbox, "run_dataset", FAKE_SANDBOX)
    models = {m.model_name: m for m in (down("down/a"), scripted([{"text": "ok"}], name="ok/b"))}
    monkeypatch.setattr(llm, "resolve", lambda name: models[name])
    setup = llm.Setup(AgentSettings(model="down/a", fallback_models=["ok/b"]))
    provider_model = f"gemini-plane-{uuid.uuid4().hex}"
    async with client() as api:
        process_id, headers = await create_process(api, "manager")
        rule_id = (await api.get(f"/processes/{process_id}/rules")).json()[0]["id"]

        # Ingestion: an upload read by text and OCR, one field left null.
        with (
            events.span("upload_document", process_id=process_id),
            events.span("extraction", cache_hit=True),
        ):
            with events.span("native_text", pages=2):
                pass
            with events.span("ocr"):
                with events.span(
                    "provider_call",
                    provider="gemini",
                    model=provider_model,
                    operation="image_transcription",
                    network_attempted=True,
                    outcome="success",
                    input_tokens=12,
                    output_tokens=4,
                ):
                    pass
                with events.span(
                    "provider_call",
                    provider="gemini",
                    model=provider_model,
                    operation="image_transcription",
                    network_attempted=False,
                    outcome="replay",
                    input_tokens=12,
                    output_tokens=4,
                ):
                    pass
        async with session_factory() as session:
            symbols = {"iban": {"value": None, "origin": "d"}, "nif": {"value": "B", "origin": "d"}}
            events.record(
                session,
                "ingest_document",
                process_id=process_id,
                data={"symbols": symbols},
                duration_ms=10,
            )
            await session.commit()

        # Agents: a compile whose first model is down; the fallback answers.
        compiler = Agent(None, output_type=Answer, name="compiler")
        with (
            events.span("compile_rule", process_id=process_id, rule_id=rule_id, valid=True),
            events.span("coder_attempt", attempt=1),
        ):
            await llm.run(compiler, "compiler", "hi", instructions="P", setup=setup)

        # Execution: a run, then a person resolves the escalated invoice.
        assert (await api.post(f"/processes/{process_id}/run")).status_code == 200
        [escalated] = (await api.get(f"/processes/{process_id}/queue")).json()
        body = {"decision": "NO_PAGAR", "reason": "checked"}
        r = await api.post(f"/instances/{escalated['id']}/resolve", json=body, headers=headers)
        assert r.status_code == 200, r.text

        url = f"/processes/{process_id}/metrics"
        ingestion = (await api.get(f"{url}/ingestion")).json()
        agents = (await api.get(f"{url}/agents")).json()
        execution = (await api.get(f"{url}/execution")).json()
        ingestion_everywhere = (await api.get("/metrics/ingestion")).json()
        everywhere = (await api.get("/metrics/agents")).json()
        assert (await api.get(f"{url}/nothing")).status_code == 422
        old = (await api.get(url)).json()

    assert ingestion["plane"] == "ingestion" and ingestion["process_id"] == process_id
    assert {s["step"] for s in ingestion["steps"]} == {
        "upload_document",
        "extraction",
        "native_text",
        "ocr",
        "provider_call",
        "ingest_document",
    }
    assert (ingestion["files"], ingestion["pages"], ingestion["ocr_calls"]) == (1, 2, 1)
    assert ingestion["providers"] == [
        {
            "provider": "gemini",
            "model": provider_model,
            "operation": "image_transcription",
            "attempts": 2,
            "network_requests": 1,
            "replays": 1,
            "errors": 0,
            "input_tokens": 12,
            "output_tokens": 4,
        }
    ]
    assert (
        next(p for p in ingestion_everywhere["providers"] if p["model"] == provider_model)
        == (ingestion["providers"][0])
    )
    assert ingestion["cache_hits"] == 1 and ingestion["abstentions_by_field"] == {"iban": 1}

    [compiler] = agents["by_role"]
    assert compiler["key"] == "compiler" and compiler["calls"] == 1
    assert compiler["fallbacks"] == 1 and compiler["errors"] == 0
    assert compiler["input_tokens"] > 0 and compiler["output_tokens"] > 0
    assert [m["key"] for m in agents["by_model"]] == ["ok/b"]
    assert [r["key"] for r in agents["by_rule"]] == [str(rule_id)]
    assert len(agents["by_use_case"]) == 1 and agents["per_hour"][0]["calls"] == 1
    assert agents["compile"] == {
        "compilations": 1,
        "valid": 1,
        "success_rate": 1.0,
        "attempts": 1,
        "attempts_per_compilation": 1.0,
        "max_attempts": 1,
    }
    assert {s["step"] for s in agents["steps"]} == {
        "load_definition",
        "publish_process_version",
        "compile_rule",
        "coder_attempt",
        "llm_run",
    }
    assert sum(r["calls"] for r in everywhere["by_role"]) >= 1 and everywhere["process_id"] is None

    assert execution["runs"] == 1 and execution["instances_decided"] == 3
    assert [r["evaluations"] for r in execution["rules"]] == [1, 1]
    assert execution["resolutions"] == 1 and execution["resolutions_by_author"] == {"Ana": 1}
    assert execution["resolution_p50_s"] is not None and execution["escalated"] == 0
    assert "llm_run" not in {s["step"] for s in execution["steps"]}

    # The original metrics keep their shape, with the new token fields.
    assert old["runs"] == 1 and old["llm"][0]["fallbacks"] == 1


async def test_a_failed_llm_run_still_records_what_came_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm, "resolve", lambda name: down(name))
    with events.span("demo_llm_down") as root, pytest.raises(llm.AgentError):
        await llm.run(Agent(None, output_type=Answer), "compiler", "hi", instructions="P")
    [row] = [r for r in root.rows if r["step"] == "llm_run"]
    assert row["status"] == "error" and row["data"]["requests"] == 0
    assert row["data"]["input_tokens"] == 0 and row["data"]["cached_tokens"] == 0


async def test_plane_health_follows_the_thresholds(monkeypatch: pytest.MonkeyPatch) -> None:
    for step in ("upload_document", "llm_run", "run_process"):
        with events.span(step):
            pass
    async with client() as api:
        monkeypatch.setattr(settings, "health_min_spans", 1)
        monkeypatch.setattr(settings, "health_down_error_rate", 2.0)
        monkeypatch.setattr(settings, "health_degraded_error_rate", 2.0)
        monkeypatch.setattr(settings, "health_p95_ms", {p: 10**9 for p in Plane})
        healthy = (await api.get("/health/planes")).json()
        monkeypatch.setattr(settings, "health_p95_ms", {p: -1 for p in Plane})
        slow = (await api.get("/health/planes")).json()
        monkeypatch.setattr(settings, "health_down_error_rate", 0.0)
        down_ = (await api.get("/health/planes")).json()

    assert [(h["plane"], h["status"]) for h in healthy] == [
        ("ingestion", "ok"),
        ("agents", "ok"),
        ("execution", "ok"),
    ]
    assert all(h["spans"] >= 1 for h in healthy)
    assert {h["status"] for h in slow} == {"degraded"} and "p95" in slow[0]["reason"]
    assert {h["status"] for h in down_} == {"down"}


async def test_a_plane_with_too_few_spans_is_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    with events.span("run_process") as run:
        run.status = "error"
    monkeypatch.setattr(settings, "health_down_error_rate", 0.0)
    monkeypatch.setattr(settings, "health_min_spans", 10**9)
    async with client() as api:
        planes = (await api.get("/health/planes")).json()
    execution = next(h for h in planes if h["plane"] == "execution")
    assert execution["status"] == "ok" and execution["errors"] >= 1
    assert execution["reason"].startswith("not enough data")


async def test_the_stream_sends_new_spans_of_one_plane(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "STREAM_POLL_S", 0)
    async with client() as api:
        process_id, _ = await create_process(api, "manager")
    stream = service.stream(Plane.execution, process_id, None)
    assert await anext(stream) == ": ping\n\n"  # nothing new yet
    with events.span("upload_document", process_id=process_id):  # another plane
        pass
    with events.span("run_process", process_id=process_id) as run:
        pass
    event = await anext(stream)
    await stream.aclose()
    head, data = event.split("data: ")
    assert head.startswith("id: ") and "event: execution" in head
    assert f'"span_id":"{run.span_id}"' in data and event.endswith("\n\n")
