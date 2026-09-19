"""The compiler eval: its harness with a scripted model (default run), and the real thing
(opt-in)."""

import json
from datetime import UTC, datetime

import pytest

from app.features.agents import llm
from evals import eval_compiler
from tests.support import challenge, pack
from tests.support.models import per_role

pytestmark = pytest.mark.skipif(
    not challenge.available(), reason="challenge submodule not checked out"
)


@pytest.mark.e2e
async def test_the_harness_scores_the_reference_code_at_100(monkeypatch) -> None:
    """Scripted agents that answer with the reference code must agree 100% with it."""
    defn = pack.definition()
    rule = pack.rules(defn)[1]  # R02: the issuer is in the master
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
    scripts = {"tester": [{"tests": tests}], "compiler": [{"code": rule.code}]}
    monkeypatch.setattr(llm, "model_for", per_role(scripts))

    report = eval_compiler.evaluate(await eval_compiler.compile_one(rule, defn))

    assert report.error is None
    assert report.agreement == 100.0
    assert report.reference_on_tests == "6/6"
    assert report.valid
    table = eval_compiler.render([report], {}, datetime.now(UTC))
    assert "| R02 | NO_PAGAR | yes | True | 100.0% | 6/6 | 1 | 0 |" in table


@pytest.mark.llm
async def test_the_compiler_agrees_with_the_reference_on_every_rule() -> None:
    """Real models, real money: `uv run pytest -m llm evals`."""
    result = await eval_compiler.run(None)
    if result is None:
        pytest.skip("no LLM keys (see the message above)")
    path, reports = result
    invalid = [f"R{r.rule.id:02d} {r.agreement}" for r in reports if not r.valid]
    assert not invalid, f"see {path}: {invalid}"
