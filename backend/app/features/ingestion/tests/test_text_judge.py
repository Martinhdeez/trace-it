import json
from dataclasses import replace

import httpx
import pytest

from app.features.ingestion.ocr.judge import TextJudge
from app.features.ingestion.pdf.invoice import parse_invoice

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
    fields, _ = parse_invoice(readers["primary"])
    if invented:
        with pytest.raises(ValueError, match="Invalid Jev selection"):
            judge.select(readers, fields)
    else:
        first = judge.select(readers, fields)
        assert first["visual_vote"] is False
        assert first == judge.select(readers, fields)
    assert len(requests) == 1
