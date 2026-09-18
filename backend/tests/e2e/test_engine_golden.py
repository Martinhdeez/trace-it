"""The v3 rules decide batch 1 as the golden reference says. No LLM, no database.

The hand-written code for the 16 rules runs in the real sandbox, one subprocess per rule,
over the symbols of the 471 text PDFs and the real sources (workbook + ERP export). The
engine's own `decide` combines the findings, exactly as the service does. A failure here
means the rule texts, the engine, the sandbox or the source shapes disagree with an
independent reading of the norm.
"""

from typing import Any

import pytest

from app.features.agents import sandbox
from app.features.decisions.engine import Verdict, decide
from tests.golden import golden
from tests.support import challenge, pack

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not challenge.available(), reason="challenge submodule not checked out"),
]


def patient(code: str, instances: list, sources: dict, population: list) -> list:
    return sandbox.run_dataset(code, instances, sources, population, timeout_s=120)


@pytest.fixture(scope="module")
def verdicts() -> dict[str, Verdict]:
    instances = golden.symbols()
    dataset = [(s["file_id"], s) for s in instances]
    population = [(s["file_id"], {**s, "_instance": s["file_id"]}) for s in instances]
    results = decide(
        pack.rules(), pack.outcomes(), dataset, challenge.sources(), population, patient
    )
    return {s["file_id"]: v for s, v in zip(instances, results, strict=True)}


def fired(verdict: Verdict) -> str:
    return (
        " | ".join(f"R{r.rule_id:02d}: {r.reason}" for r in verdict.results if r.fires is not False)
        or "-"
    )


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
        (fid, expected[fid]["expected"], v.decision, fired(v))
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
