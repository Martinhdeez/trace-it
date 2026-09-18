"""The v3 rules decide batch 1 as the golden reference says. No LLM, no database.

Mateo's hand-written code for the 16 rules runs in the real sandbox, one batch per rule, over
the symbols of the 471 text PDFs and the real sources (workbook + ERP export). The engine's
own `decidir` then combines the findings. A failure here means the rule texts, the engine,
the sandbox or the source shapes disagree with an independent reading of the norm.
"""

from typing import Any

import pytest

from tests.golden import golden
from tests.support import app_adapter as adapter
from tests.support import challenge

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not challenge.available(), reason="challenge submodule not checked out"),
]


@pytest.fixture(scope="module")
def verdicts() -> dict[str, adapter.Verdict]:
    defn = adapter.definition()
    specs, out = adapter.rules(defn), adapter.outcomes(defn)
    codes = adapter.REFERENCE_CODE
    sources = challenge.sources()
    instances = golden.symbols()
    others = {
        s["file_id"]: [{**o, "_instancia": o["file_id"]} for o in instances if o is not s]
        for s in instances
    }
    cases = [(s, sources, others[s["file_id"]]) for s in instances]

    # Every rule over every instance, in the real sandbox, batched. The engine then reads
    # these answers instead of spawning 16 x 471 subprocesses.
    answers: dict[tuple[str, str], Any] = {}
    for code, results in zip(codes, adapter.run_batched(codes, cases), strict=True):
        for instance, result in zip(instances, results, strict=True):
            answers[(code, instance["file_id"])] = result

    def execute(code: str, instance: dict[str, Any], *_: Any) -> dict[str, Any]:
        result = answers[(code, instance["file_id"])]
        if isinstance(result, Exception):
            raise result
        return result

    return {
        s["file_id"]: adapter.decide(specs, codes, out, s, sources, others[s["file_id"]], execute)
        for s in instances
    }


def table(rows: list[tuple[str, str, str, str]]) -> str:
    head = ("file", "expected", "got", "fired rules")
    widths = [max(len(r[i]) for r in [head, *rows]) for i in range(3)]
    return "\n".join(
        "  ".join(cell.ljust(w) for cell, w in zip(r[:3], widths, strict=True)) + "  " + r[3]
        for r in [head, *rows]
    )


def test_every_text_invoice_matches_the_golden_outcome(verdicts: dict[str, Any]) -> None:
    expected = golden.expected()
    wrong = [
        (fid, expected[fid]["expected"], v.decision, " | ".join(v.fired) or "-")
        for fid, v in sorted(verdicts.items())
        if v.decision != expected[fid]["expected"] and fid not in golden.KNOWN_MISMATCHES
    ]
    assert not wrong, f"{len(wrong)} of {len(verdicts)} differ from golden:\n{table(wrong)}"


def test_the_golden_covers_every_text_invoice(verdicts: dict[str, Any]) -> None:
    expected = golden.expected()
    assert len(expected) == len(challenge.invoice_paths()) == 500
    decidable = {fid for fid, row in expected.items() if row["expected"] is not None}
    assert set(verdicts) == decidable
    assert len(decidable) == 471


@pytest.mark.parametrize(
    "file_id",
    [
        pytest.param(fid, marks=pytest.mark.xfail(reason=reason, strict=True))
        for fid, reason in sorted(golden.KNOWN_MISMATCHES.items())
    ]
    or [pytest.param(None, marks=pytest.mark.skip(reason="no known mismatch"))],
)
def test_known_mismatch_still_differs(file_id: str, verdicts: dict[str, Any]) -> None:
    """Strict xfail: when the team settles a mismatch, this starts passing and fails CI,
    so the entry is removed from KNOWN_MISMATCHES."""
    assert verdicts[file_id].decision == golden.expected()[file_id]["expected"]
