import json

import httpx
import pytest

from app.features.ingesta.tools.jev_cases import CASES, request_body
from app.features.ingesta.tools.probe_jev import cached_probe


def test_references_are_not_sent_to_provider():
    for case in CASES:
        payload = request_body(case)
        assert set(payload["state"]) == {"source_text", "requested_field", "proposed_value"}
        assert "expected_choice" not in json.dumps(payload)
        assert "none" in payload["questions"]["selection"]["criteria"]


def test_timeout_is_journaled_without_secret_or_automatic_resubmission(tmp_path):
    calls = []

    def timeout(request):
        calls.append(request)
        raise httpx.ReadTimeout("Simulated timeout")

    with httpx.Client(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(httpx.ReadTimeout):
            cached_probe(client, request_body(CASES[0]), "test-secret", tmp_path)
        with pytest.raises(RuntimeError, match="Incomplete attempt"):
            cached_probe(client, request_body(CASES[0]), "test-secret", tmp_path)
    assert len(calls) == 1
    journal = next(tmp_path.glob("*.json")).read_text()
    assert "test-secret" not in journal
    assert json.loads(journal)["state"] == "uncertain_or_failed"


def test_invalid_choice_is_rejected(tmp_path):
    def respond(request):
        return httpx.Response(
            200,
            json={
                "answers": {
                    "selection": {"type": "choice", "choice": "invented"},
                    "support": {"type": "noul", "noul": 1},
                }
            },
        )

    with (
        httpx.Client(transport=httpx.MockTransport(respond)) as client,
        pytest.raises(ValueError, match="Invalid typed answers"),
    ):
        cached_probe(client, request_body(CASES[0]), "test-secret", tmp_path)
