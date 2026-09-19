"""The norm eval: its harness with scripted models (default run), and the real thing
(opt-in)."""

import json
from datetime import UTC, datetime

import pytest

from app.features.agents import llm
from evals import eval_norm
from tests.support import challenge, pack
from tests.support.models import per_role

pytestmark = pytest.mark.skipif(
    not challenge.available(), reason="challenge submodule not checked out"
)


@pytest.mark.e2e
async def test_the_harness_decides_batch_1_with_the_normalized_checks(monkeypatch) -> None:
    """Norm rule 1 normalized to one check (the supplier is in the master), compiled to the
    reference code: it catches the 3 unknown suppliers, so 433 + 3 invoices agree."""
    rule = pack.rules()[1]  # R02: the issuer is in the master
    master = challenge.sources()["suppliers"][:1]
    tests = [
        {
            "name": f"nif {nif}",
            "instance_json": json.dumps({"issuer_nif": nif}),
            "sources_json": json.dumps({"suppliers": master}),
            "others_json": "[]",
            "fires": nif != master[0]["nif"],
        }
        for nif in [master[0]["nif"], "B00000000", "X1", "B00000001", "B00000002", "B00000003"]
    ]
    check = {"text": rule.text, "type": "requirement", "decision": "NO_PAGAR"}
    sentence = {
        "number": 1,
        "text": "Pagar solo si el NIF esta en el maestro",
        "checks": [
            {**check, "decision_source": "policy", "interpretation": "'Pay only if': no outcome."}
        ],
        "policies": ["When in doubt, escalate."],
    }
    scripts = {
        "normalizer": [{"norm_rules": [sentence]}],
        "tester": [{"tests": tests}],
        "compiler": [{"code": rule.code}],
    }
    monkeypatch.setattr(llm, "model_for", per_role(scripts))

    result = await eval_norm.evaluate({})

    assert "1. Pagar solo si el NIF" in result.norm and result.norm.count("\n") == 5
    assert [c.outcome for c in result.checks] == ["valid"]
    assert len(result.verdicts) - len(result.mismatches()) == 436
    report = eval_norm.render(result, {}, datetime.now(UTC))
    assert "**436/471**" in report
    assert "| 1.1 | requirement | NO_PAGAR | valid | 1 |" in report
    assert "### Decided by no check fired (35)" in report


@pytest.mark.llm
async def test_the_norm_decides_batch_1_like_the_golden() -> None:
    """Real models, real money: `uv run pytest -m llm evals`."""
    result = await eval_norm.run()
    if result is None:
        pytest.skip("no LLM keys (see the message above)")
    path, outcome = result
    assert not outcome.mismatches(), f"see {path}"
