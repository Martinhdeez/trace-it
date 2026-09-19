"""Schema request counters distinguish network work, journal replay and result cache."""

import io
import json
import uuid
from dataclasses import replace

import httpx

from app.features.ingestion.extraction_plan import ExtractionField, ExtractionPlan
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService

from .conftest import pdf_bytes


def test_schema_network_calls_journal_replay_and_result_cache(settings, monkeypatch):
    requests = []

    def respond(request):
        body = json.loads(request.content)
        messages = body["messages"]
        if isinstance(messages[-1]["content"], list):
            requests.append(("image", body["model"]))
            content = "The certificate remains valid until 21/04/2027."
        else:
            requests.append(("schema", body["model"]))
            task = json.loads(messages[-1]["content"])
            content = json.dumps(
                {
                    "expiry": {
                        "line_id": task["lines"][0]["line_id"],
                        "quote": "21/04/2027",
                    }
                }
            )
        return httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "stop", "message": {"content": content}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 5},
            },
        )

    original_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    configured = replace(
        settings,
        helmcode_api_key="secret",
        vision_providers=("helmcode",),
        helmcode_vision_models=("qwen3.6", "gemma4"),
        helmcode_text_model="qwen3.6",
    )
    service = ExtractionService(configured)
    item = service.ingest(io.BytesIO(pdf_bytes("")), "first.pdf")
    plan = ExtractionPlan(process_id=1, fields=[ExtractionField(name="expiry", type="date")])
    options = ExtractOptions(mode="api", ocr=False)

    first = service.extract_schema(item, options, plan)
    assert requests == [("image", "qwen3.6"), ("image", "gemma4"), ("schema", "qwen3.6")]
    assert not first.cache_hit
    assert (first.metrics["ocr_calls_this_request"], first.metrics["vlm_calls_this_request"]) == (
        0,
        2,
    )
    assert (
        first.metrics["jev_calls_this_request"],
        first.metrics["schema_calls_this_request"],
    ) == (
        0,
        1,
    )
    assert first.metrics["schema_calls"] == 1
    assert first.metrics["schema_cache_hits_this_request"] == 0

    changed_contract = plan.model_copy(update={"process_id": 2})
    replay = service.extract_schema({**item, "id": uuid.uuid4().hex}, options, changed_contract)
    assert not replay.cache_hit
    assert len(requests) == 3
    assert replay.metrics["vlm_calls_this_request"] == 0
    assert replay.metrics["schema_calls_this_request"] == 0
    assert replay.metrics["vlm_cache_hits_this_request"] == 2
    assert replay.metrics["schema_cache_hits_this_request"] == 1

    cached = service.extract_schema({**item, "id": uuid.uuid4().hex}, options, plan)
    assert cached.cache_hit
    assert len(requests) == 3
    for reader in ("ocr", "vlm", "jev", "schema"):
        assert cached.metrics[f"{reader}_calls_this_request"] == 0
        assert cached.metrics[f"{reader}_cache_hits_this_request"] == 0
