import json
from dataclasses import replace

import httpx
import pytest

from app.features.ingestion.ocr.errors import ProviderUnavailable
from app.features.ingestion.ocr.judge import TextJudge
from app.features.ingestion.pdf.committee import reconcile

from .conftest import lines


@pytest.mark.parametrize("invented", [False, True])
def test_text_judge_checks_typed_candidates_and_reuses_journal(settings, monkeypatch, invented):
    requests = []

    def respond(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert "images" not in payload["state"]
        assert payload["state"]["readers"]["primary"] == ["NIF: B98120774"]
        assert "cannot see the image" in payload["questions"]["supplier_tax_id"]["instructions"]
        return httpx.Response(
            200,
            json={
                "answers": {
                    "supplier_tax_id": {
                        "type": "choice",
                        "choice": "invented" if invented else "B98120774",
                        "probabilities": {"B98120774": 0.8, "none": 0.2},
                        "confidence": 0.8,
                    }
                },
                "model": "test-jev",
                "usage": {},
            },
        )

    original = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs)
    )
    judge = TextJudge(replace(settings, jev_api_key="test-key"))
    readers = {"primary": lines("NIF: B98120774", "ocr", 0.99)}
    fields, _, _ = reconcile(readers, settings.ocr_min_confidence)
    if invented:
        with pytest.raises(ProviderUnavailable, match="jev call unavailable"):
            judge.select(readers, fields)
    else:
        first = judge.select(readers, fields)
        assert first["visual_vote"] is False
        assert first == judge.select(readers, fields)
    assert len(requests) == 1


def test_judge_skips_confirmed_image_readings(settings, monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Confirmed evidence must not invoke the text judge")

    monkeypatch.setattr(httpx, "Client", fail)
    readers = {name: lines("NIF: B98120774", "ocr", 0.99) for name in ("primary", "secondary")}
    fields, _, _ = reconcile(readers, settings.ocr_min_confidence)
    assert fields["supplier_tax_id"].status == "OBSERVED"
    assert TextJudge(settings).select(readers, fields) == {}
