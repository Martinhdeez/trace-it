"""The compiler eval: its harness with a fake LLM (default run), and the real thing (opt-in)."""

from datetime import UTC, datetime

import pytest

from evals import eval_compiler
from tests.support import app_adapter as adapter
from tests.support import challenge

pytestmark = pytest.mark.skipif(
    not challenge.available(), reason="challenge submodule not checked out"
)


@pytest.mark.e2e
async def test_the_harness_scores_the_reference_code_at_100(monkeypatch) -> None:
    """A fake LLM that answers with the reference code must agree 100% with it."""
    spec = adapter.rules(adapter.definition())[1]  # R02: the issuer is in the master
    master = challenge.sources()["suppliers"][:1]
    tests = [
        {
            "name": f"nif {nif}",
            "instance": {"issuer_nif": nif},
            "sources": {"suppliers": master},
            "others": [],
            "fires": nif != master[0]["nif"],
        }
        for nif in [master[0]["nif"], "B00000000", "X1", "B00000001", "B00000002", "B00000003"]
    ]
    code = adapter.REFERENCE_CODE[1]
    adapter.patch_llm(monkeypatch, lambda role: adapter.fake_llm_reply(code, tests, role))

    compiled = await adapter.compile_rule(spec, adapter.definition(), challenge.sources())
    report = eval_compiler.evaluate(spec, compiled)

    assert [c.error for c in compiled] == [None, None]
    assert report.agreement == {role: 100.0 for role in adapter.COMPILER_ROLES}
    assert report.reference_on_tests == "12/12"
    assert report.valid
    table = eval_compiler.render([report], {}, datetime.now(UTC))
    assert "| R02 | NO_PAGAR | yes | 100.0% | 100.0% |" in table


@pytest.mark.llm
async def test_the_compiler_agrees_with_the_reference_on_every_rule() -> None:
    """Real models, real money: `uv run pytest -m llm evals`."""
    result = await eval_compiler.run(None)
    if result is None:
        pytest.skip("no LLM keys or no configured models (see the message above)")
    path, reports = result
    invalid = [f"R{r.spec.number:02d} {r.agreement}" for r in reports if not r.valid]
    assert not invalid, f"see {path}: {invalid}"
