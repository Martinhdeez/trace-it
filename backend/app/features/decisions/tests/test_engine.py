"""The engine on the invoice process: PAGAR by default, NO_PAGAR and ESCALAR by rule."""

from typing import Any

import pytest

from app.features.decisions.engine import decide
from app.features.rules.model import Rule

PRIORITIES = {"ESCALAR": 3, "NO_PAGAR": 2, "PAGAR": 1}
DEFAULT = "PAGAR"

# Rule text -> what its compiled code does. The real code comes from Martín's compiler and
# runs in his sandbox; here a rule is a plain function, which is all the engine needs.
RULES_V3 = {
    "iban_mismatch": (
        "prohibition",
        "ESCALAR",
        lambda i, s, o: i["iban"] != _supplier(s, i["nif"])["iban"],
    ),
    "order_already_paid": (
        "prohibition",
        "NO_PAGAR",
        lambda i, s, o: _entry(s, i["purchase_order"])["status"] == "PAGADA",
    ),
    "future_date": (
        "requirement",
        "ESCALAR",
        lambda i, s, o: i["date"] > s["parameters"][0]["cut_off_date"],
    ),
}

SUPPLIERS = [
    {"nif": "B96233419", "iban": "ES2100752345670600123456"},
    {"nif": "B78451236", "iban": "ES9368884400123588900142"},
]
ENTRIES = [
    {"purchase_order": "PO-2026-0008", "status": "PENDIENTE"},
    {"purchase_order": "PO-2026-0474", "status": "PAGADA"},
    {"purchase_order": "PO-2026-0813", "status": "PENDIENTE"},
]
PARAMETERS = [{"cut_off_date": "2026-09-19"}]  # a rule never reads the clock (P18)
SOURCES = {"suppliers": SUPPLIERS, "erp": ENTRIES, "parameters": PARAMETERS}

# factura_1217.pdf: everything matches and the order is unpaid.
CLEAN = {
    "nif": "B96233419",
    "iban": "ES2100752345670600123456",
    "purchase_order": "PO-2026-0008",
    "date": "2026-05-02",
}
# FA-1016_papelería.pdf: correct in every way, but the ERP already paid the order.
ALREADY_PAID = {**CLEAN, "purchase_order": "PO-2026-0474"}
# FA-5044_mensajería2.pdf: a new IBAN the supplier master does not know.
NEW_IBAN = {
    "nif": "B78451236",
    "iban": "ES3900815290070012345678",
    "purchase_order": "PO-2026-0813",
    "date": "2026-05-02",
}


def _supplier(sources: dict, nif: str) -> dict:
    return next(p for p in sources["suppliers"] if p["nif"] == nif)


def _entry(sources: dict, order: str) -> dict:
    return next(e for e in sources["erp"] if e["purchase_order"] == order)


def rules(*names: str) -> list[Rule]:
    return [
        Rule(
            id=number,
            text=name,
            type=RULES_V3[name][0],
            decision=RULES_V3[name][1],
            code_a=name,
            code_b=name,
            hash=f"hash-{name}",
        )
        for number, name in enumerate(names, start=1)
    ]


def run(code: str, instance: dict, sources: dict, others: list) -> dict:
    """One case of a rule. Raises when the rule fails, like the real sandbox."""
    fires = RULES_V3[code][2](instance, sources, others)
    return {"fires": fires, "reason": code if fires else ""}


def batch(one: Any) -> Any:
    """A stand-in for `sandbox.run_batch` built from a per-case function: like the real one,
    a failing case comes back as its exception instead of raising."""

    def run_batch(code: str, cases: list) -> list:
        answers = []
        for case in cases:
            try:
                answers.append(one(code, *case))
            except Exception as error:  # noqa: BLE001
                answers.append(error)
        return answers

    return run_batch


def decide_invoice(active: list[Rule], instance: dict[str, Any], **extra: Any) -> Any:
    return decide(active, PRIORITIES, DEFAULT, instance, SOURCES, [], batch(extra.get("run", run)))


def test_no_rule_fires_decides_the_default() -> None:
    verdict = decide_invoice(rules("iban_mismatch", "order_already_paid"), CLEAN)

    assert verdict.decision == "PAGAR"
    assert [(r.rule_id, r.fires) for r in verdict.results] == [(1, False), (2, False)]


def test_one_rule_fires() -> None:
    verdict = decide_invoice(rules("iban_mismatch", "order_already_paid"), ALREADY_PAID)

    assert verdict.decision == "NO_PAGAR"
    assert verdict.reason == "order_already_paid"


def test_several_fire_and_the_highest_priority_wins() -> None:
    """The IBAN is unknown *and* the order is already paid: a person looks at it first."""
    active = rules("iban_mismatch", "order_already_paid")

    verdict = decide_invoice(active, {**NEW_IBAN, "purchase_order": "PO-2026-0474"})

    assert verdict.decision == "ESCALAR"
    assert all(r.fires for r in verdict.results)


def test_a_failing_rule_goes_to_review() -> None:
    """A rule that cannot be evaluated never produces a silent PAGAR, nor an ESCALAR."""
    unknown = {**CLEAN, "nif": "B00000000"}  # not in the supplier master

    verdict = decide_invoice(rules("iban_mismatch", "order_already_paid"), unknown)

    assert verdict.decision is None
    assert "RULE_ERROR 1" in verdict.reason
    assert verdict.results[0].fires is None
    assert verdict.results[1].fires is False  # every rule still ran


def test_a_priority_tie_between_different_decisions_goes_to_review() -> None:
    active = rules("iban_mismatch", "order_already_paid")
    tie = {"ESCALAR": 2, "NO_PAGAR": 2, "PAGAR": 1}

    verdict = decide(
        active,
        tie,
        DEFAULT,
        {**NEW_IBAN, "purchase_order": "PO-2026-0474"},
        SOURCES,
        [],
        batch(run),
    )

    assert verdict.decision is None
    assert "RULE_CONFLICT" in verdict.reason


def test_the_cut_off_date_comes_from_a_source() -> None:
    """Rules are pure: they never read the clock, so a past decision replays identically."""
    active = rules("future_date")
    future = {**CLEAN, "date": "2027-01-01"}

    assert decide_invoice(active, future).decision == "ESCALAR"
    assert decide_invoice(active, CLEAN).decision == "PAGAR"


def test_the_verdict_identifies_the_rule_set() -> None:
    active = rules("iban_mismatch", "order_already_paid")

    first = decide_invoice(active, CLEAN)
    second = decide_invoice(list(reversed(active)), CLEAN)
    third = decide_invoice(rules("iban_mismatch"), CLEAN)

    assert first.rules_hash == second.rules_hash  # order is not a change
    assert first.rules_hash != third.rules_hash  # removing a rule is


@pytest.mark.parametrize("answer", [{"reason": "x"}, "not a dict", None])
def test_a_malformed_answer_goes_to_review(answer: Any) -> None:
    def broken(*_: Any) -> Any:
        return answer

    verdict = decide_invoice(rules("iban_mismatch"), CLEAN, run=broken)

    assert verdict.decision is None
    assert "RULE_ERROR 1" in verdict.reason


def test_an_unknown_decision_type_goes_to_review() -> None:
    active = rules("order_already_paid")
    active[0].decision = "HOLD"  # not a type of this process

    verdict = decide_invoice(active, ALREADY_PAID)

    assert verdict.decision is None
    assert "UNKNOWN_DECISION: HOLD" in verdict.reason


def test_a_rule_without_code_b_goes_to_review() -> None:
    active = rules("iban_mismatch")
    active[0].code_b = None

    verdict = decide_invoice(active, CLEAN)

    assert verdict.decision is None
    assert "without both codes" in verdict.reason
