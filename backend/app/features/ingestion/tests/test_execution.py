import io
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import httpx
import pytest

from app.features.ingestion.extraction_plan import ExtractionField, ExtractionPlan
from app.features.ingestion.ocr.judge import TextJudge
from app.features.ingestion.pdf.committee import reconcile
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService
from app.features.processes.execution import (
    ExecutionSettings,
    ExtractionSettings,
    ingestion_settings,
)
from app.features.use_cases.schemas import ROLES, AgentSettings

from .conftest import NoOCR, NoVLM, lines, pdf_bytes


def config(settings, **changes):
    extraction = ExtractionSettings(
        primary_model_dir=str(settings.model_dir),
        verification_model_dir=str(settings.model_dir / "verify"),
        **changes,
    )
    return ExecutionSettings(
        local_only=True,
        local_endpoint="http://localhost:11434/v1",
        agents={role: AgentSettings(model="local:test") for role in ROLES},
        extraction=extraction,
    )


def test_configured_services_share_capacity_but_isolate_models_and_caches(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    original = service.settings
    configs = [config(settings, vision_model=f"local:vision-{i}", dpi=240 + i) for i in range(2)]
    with ThreadPoolExecutor(max_workers=2) as workers:
        first, second = list(workers.map(service.configured, configs))
    assert service.settings == original
    assert first.settings.vlm_model == "vision-0"
    assert second.settings.vlm_model == "vision-1"
    assert first.settings.gemini_api_key is None
    assert first.settings.jev_api_key is None
    assert first.slots is second.slots is service.slots
    assert service.configured(configs[0]) is first
    item = service.ingest(io.BytesIO(pdf_bytes("invoice")), "invoice.pdf")
    assert first.cache_key(item, ExtractOptions()) != second.cache_key(item, ExtractOptions())


@pytest.mark.parametrize("force", [False, True])
def test_configured_schema_mapper_uses_process_endpoint_timeout_and_budget(
    settings, monkeypatch, force
):
    global_settings = replace(
        settings,
        vlm_url="https://global-vision.example/v1",
        vlm_model="global-model",
        gemini_api_key="dummy-cloud",
        helmcode_api_key="dummy-cloud",
        ocr_force_recompute=force,
    )
    base = ExtractionService(global_settings, NoOCR(), NoVLM())
    scoped = base.configured(
        config(
            settings,
            vision_model="local:schema-model",
            vision_timeout_seconds=7,
            vision_max_tokens=128,
        )
    )
    assert scoped.field_reader.settings is scoped.settings
    assert base.field_reader.settings is global_settings
    calls = []
    original_client = httpx.Client
    fail_local = [False]

    def respond(request):
        calls.append(request)
        assert request.url.host == "localhost"  # Cloud routes fail this test.
        if fail_local[0]:
            return httpx.Response(503)
        body = json.loads(request.content)
        assert str(request.url) == "http://localhost:11434/v1/chat/completions"
        assert body["model"] == "schema-model"
        assert body["max_tokens"] == 128
        task = json.loads(body["messages"][1]["content"])
        source = next(line for line in task["lines"] if "21/04/2027" in line["text"])
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "expires_on": {
                                        "line_id": source["line_id"],
                                        "quote": "21/04/2027",
                                    }
                                }
                            )
                        }
                    }
                ]
            },
        )

    def client(**kwargs):
        assert kwargs["timeout"] == 7
        return original_client(**kwargs, transport=httpx.MockTransport(respond))

    monkeypatch.setattr(httpx, "Client", client)
    plan = ExtractionPlan(process_id=1, fields=[ExtractionField(name="expires_on", type="date")])
    options = ExtractOptions(ocr=False, vlm=True, jev=False)
    item = base.ingest(
        io.BytesIO(
            pdf_bytes("Please pay before 21/04/2027. This visible native text has no field label.")
        ),
        "case.pdf",
    )
    result = scoped.extract_schema(item, options, plan)
    assert result.fields["expires_on"].value == "2027-04-21"
    provenance = result.data["provenance"]
    assert provenance["execution_hash"] == scoped.execution_hash
    assert provenance["schema_mapper"]["chain"][0]["model"] == "schema-model"
    assert "dummy-cloud" not in json.dumps(provenance)
    assert not result.cache_hit
    replay = scoped.extract_schema({**item, "id": "repeat"}, options, plan)
    assert replay.cache_hit is not force
    assert replay.data["provenance"]["execution_hash"] == provenance["execution_hash"]
    assert replay.data["provenance"]["cache_key"] == provenance["cache_key"]
    assert len(calls) == (2 if force else 1)

    fail_local[0] = True
    unavailable = base.ingest(
        io.BytesIO(
            pdf_bytes("Please pay before 22/04/2027. This visible native text has no field label.")
        ),
        "unavailable.pdf",
    )
    failed = scoped.extract_schema(unavailable, options, plan)
    assert any(warning["code"] == "SCHEMA_READER_ERROR" for warning in failed.warnings)
    assert len(calls) == (3 if force else 2)
    assert all(request.url.host == "localhost" for request in calls)


def test_schema_cache_changes_with_process_mapping_timeout(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    first = service.configured(
        config(
            settings,
            vision_model="local:schema-model",
            vision_timeout_seconds=7,
        )
    )
    second = service.configured(
        config(
            settings,
            vision_model="local:schema-model",
            vision_timeout_seconds=8,
        )
    )
    item = service.ingest(
        io.BytesIO(pdf_bytes("Destination: London\nThis native document has enough visible text.")),
        "case.pdf",
    )
    plan = ExtractionPlan(process_id=1, fields=[ExtractionField(name="destination", type="text")])
    options = ExtractOptions(ocr=False, vlm=True, jev=False)
    assert first.cache_key(item, options) != second.cache_key(item, options)
    initial = first.extract_schema(item, options, plan)
    changed = second.extract_schema({**item, "id": "different"}, options, plan)
    repeated = first.extract_schema({**item, "id": "repeat"}, options, plan)
    assert initial.fields["destination"].value == "London"
    assert not initial.cache_hit and not changed.cache_hit
    assert repeated.cache_hit


def test_disabled_readers_cannot_be_auto_enabled_by_available_cloud_keys(settings):
    base = replace(
        settings, gemini_api_key="cloud-key", jev_api_key="cloud-key", helmcode_api_key="cloud-key"
    )
    scoped = ExtractionService(base).configured(config(settings))
    assert not scoped.vlm.configured
    assert not scoped.judge.configured
    assert scoped.settings.gemini_api_key is None
    assert scoped.settings.jev_api_key is None
    assert scoped.settings.helmcode_api_key is None
    local = ExtractionService(base).configured(
        config(settings, vision_model="local:vision", text_judge_model="local:judge")
    )
    assert local.settings.visual_chain() == [("compatible", "vision")]
    assert local.judge._chain() == []
    assert local.judge.configured


def test_secondary_effort_changes_work_without_relaxing_acceptance(settings):
    class OCR(NoOCR):
        def recognize(self, *args):
            return lines("NIF: B98120774", "ocr", 0.99)

        verify = recognize

    service = ExtractionService(settings, OCR(), NoVLM())
    item = service.ingest(io.BytesIO(pdf_bytes("")), "scan.pdf")
    single = service.extract(item, ExtractOptions(secondary_ocr=False))
    double = service.extract({**item, "id": "second-reading"}, ExtractOptions())
    assert single.fields["supplier_tax_id"].value is None
    assert double.fields["supplier_tax_id"].value == "B98120774"
    assert single.metrics["ocr_verification_calls"] == 0
    assert double.metrics["ocr_verification_calls"] == 1
    assert single.data["provenance"]["cache_key"] != double.data["provenance"]["cache_key"]


@pytest.mark.parametrize("choice,valid", [("B98120774", True), ("invented", False)])
def test_local_text_judge_only_selects_existing_candidates(settings, monkeypatch, choice, valid):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"supplier_tax_id":"' + choice + '"}'},
                    }
                ]
            },
        )

    original_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original_client(**kwargs, transport=httpx.MockTransport(respond)),
    )
    bound = ingestion_settings(config(settings, text_judge_model="local:judge"), settings)
    judge = TextJudge(bound)
    readers = {"primary": lines("NIF: B98120774", "ocr", 0.99)}
    fields = reconcile(readers, 0.9)[0]
    if valid:
        answer = judge.select(readers, fields)
        assert answer["visual_vote"] is False
        assert answer["answers"]["supplier_tax_id"]["choice"] == choice
        judge.select(readers, fields)
        assert len(calls) == 1  # Replay from the existing provider journal.
    else:
        from app.features.ingestion.ocr.errors import ProviderUnavailable

        with pytest.raises(ProviderUnavailable):
            judge.select(readers, fields)
    assert str(calls[0].url) == "http://localhost:11434/v1/chat/completions"


def test_same_recognizer_cannot_supply_two_independent_votes(settings):
    from app.features.ingestion.ocr.errors import ProviderUnavailable
    from app.features.ingestion.ocr.local import LocalOCR

    for directory in (settings.model_dir, settings.model_dir / "verify"):
        path = directory / "rec/inference.onnx"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"identical recognition weights")
    with pytest.raises(ProviderUnavailable, match="different recognition weights"):
        LocalOCR(settings).verify(b"image", 1, (100, 100))


def test_helmcode_and_api_mode_are_explicit_process_choices(settings):
    from app.features.processes.execution import ExecutionSettings

    value = config(settings).model_dump()
    value["local_only"] = False
    value["extraction"].update(
        mode="api", vision_model="helmcode:qwen3.6", text_judge_model="helmcode:gemma4"
    )
    bound = ingestion_settings(
        ExecutionSettings.model_validate(value), replace(settings, helmcode_api_key="cloud-key")
    )
    assert bound.visual_chain() == [("helmcode", "qwen3.6")]
    assert bound.text_providers == ("helmcode",)
    assert bound.helmcode_text_model == "gemma4"
    assert not ExtractOptions().normalized(bound).ocr


def test_focused_verification_can_be_disabled_in_api_mode(settings):
    from app.features.ingestion.pdf.focused import verify_identifiers

    assert (
        verify_identifiers(
            b"",
            {},
            {},
            [],
            settings,
            None,
            None,
            ExtractOptions(mode="api", focused_verification=False),
            True,
            {},
        )
        == {}
    )
