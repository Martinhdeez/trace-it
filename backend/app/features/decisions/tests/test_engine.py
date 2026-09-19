"""The engine on the invoice process: PAGAR by default, NO_PAGAR and ESCALAR by rule."""

import threading
from typing import Any

import pytest

from app.features.decisions.engine import Outcomes, decide
from app.features.rules.model import Rule
from tests.support.fakes import dataset_runner

OUTCOMES = Outcomes({"ESCALAR": 3, "NO_PAGAR": 2, "PAGAR": 1}, default="PAGAR", escalate="ESCALAR")

# Rule text -> what its compiled code does. The real code runs in the sandbox; here a rule is
# a plain function, which is all the engine needs.
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
PARAMETERS = [{"cut_off_date": "2026-09-18"}]  # a rule never reads the clock
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
RUN = dataset_runner({name: fn for name, (_, _, fn) in RULES_V3.items()})


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
            code=name,
            hash=f"hash-{name}",
        )
        for number, name in enumerate(names, start=1)
    ]


def decide_invoice(
    active: list[Rule], instance: dict[str, Any], outcomes: Outcomes = OUTCOMES, run: Any = RUN
) -> Any:
    [verdict] = decide(active, outcomes, [(1, instance)], SOURCES, [(1, instance)], run)
    return verdict


def test_no_rule_fires_decides_the_default() -> None:
    verdict = decide_invoice(rules("iban_mismatch", "order_already_paid"), CLEAN)

    assert verdict.decision == "PAGAR"
    assert [(r.rule_id, r.fires) for r in verdict.results] == [(1, False), (2, False)]


def test_one_rule_fires() -> None:
    verdict = decide_invoice(rules("iban_mismatch", "order_already_paid"), ALREADY_PAID)

    assert verdict.decision == "NO_PAGAR"
    assert verdict.reason == "order_already_paid"


def test_the_reason_is_the_rules_reason_code_not_its_text() -> None:
    [rule] = rules("order_already_paid")
    rule.text = "The ERP entry of the purchase order must not be PAGADA."

    def run(code: str, instances: list, sources: dict, population: list) -> list:
        return [{"fires": True, "reason": "ORDER_PAID PO-2026-0474"}]

    assert decide_invoice([rule], ALREADY_PAID, run=run).reason == "ORDER_PAID PO-2026-0474"


def test_several_fire_and_the_highest_priority_wins() -> None:
    """The IBAN is unknown *and* the order is already paid: a person looks at it first."""
    active = rules("iban_mismatch", "order_already_paid")

    verdict = decide_invoice(active, {**NEW_IBAN, "purchase_order": "PO-2026-0474"})

    assert verdict.decision == "ESCALAR"
    assert all(r.fires for r in verdict.results)


def test_a_failing_rule_escalates_with_the_error() -> None:
    """A rule that cannot be evaluated never produces a silent PAGAR: a person gets the case
    and the reason, and every other rule still ran."""
    unknown = {**CLEAN, "nif": "B00000000"}  # not in the supplier master

    verdict = decide_invoice(rules("iban_mismatch", "order_already_paid"), unknown)

    assert verdict.decision == "ESCALAR"
    assert verdict.reason.startswith("RULE_ERROR 1: StopIteration")
    assert verdict.results[0].fires is None
    assert verdict.results[1].fires is False


def test_a_priority_tie_between_different_decisions_escalates() -> None:
    active = rules("iban_mismatch", "order_already_paid")
    tie = Outcomes({"ESCALAR": 2, "NO_PAGAR": 2, "PAGAR": 1}, "PAGAR", "ESCALAR")

    verdict = decide_invoice(active, {**NEW_IBAN, "purchase_order": "PO-2026-0474"}, tie)

    assert verdict.decision == "ESCALAR"
    assert verdict.reason == "RULE_CONFLICT: ESCALAR, NO_PAGAR share priority 2"


REQUIRED = Outcomes(
    OUTCOMES.priorities, "PAGAR", "ESCALAR", required=("nif", "iban", "purchase_order")
)


def test_a_missing_required_symbol_escalates_whatever_the_rules_say() -> None:
    """No rule fires on this invoice, yet without an IBAN it is never paid. The rules still
    ran and their results are kept."""
    active = rules("order_already_paid")

    verdict = decide_invoice(active, {**CLEAN, "iban": None, "nif": "  "}, REQUIRED)

    assert verdict.decision == "ESCALAR"
    assert verdict.reason == "MISSING_DATA: nif, iban"
    assert [(r.rule_id, r.fires) for r in verdict.results] == [(1, False)]


def test_an_instance_without_symbols_misses_every_required_one() -> None:
    """A scanned PDF with no text: every rule errors or passes, the reason names the data."""
    verdict = decide_invoice(rules("iban_mismatch"), {}, REQUIRED)

    assert verdict.decision == "ESCALAR"
    assert verdict.reason == "MISSING_DATA: nif, iban, purchase_order"
    assert verdict.results[0].fires is None


def test_required_symbols_present_leave_the_rules_to_decide() -> None:
    active = rules("iban_mismatch", "order_already_paid")

    assert decide_invoice(active, CLEAN, REQUIRED).decision == "PAGAR"
    assert decide_invoice(active, ALREADY_PAID, REQUIRED).decision == "NO_PAGAR"


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


@pytest.mark.parametrize("answer", [{"reason": "x"}, "not a dict", None, {"fires": 1}])
def test_a_malformed_answer_escalates(answer: Any) -> None:
    def broken(code: str, instances: list, sources: dict, population: list) -> list:
        return [answer] * len(instances)

    verdict = decide_invoice(rules("iban_mismatch"), CLEAN, run=broken)

    assert verdict.decision == "ESCALAR"
    assert "RULE_ERROR 1" in verdict.reason


def test_a_rule_without_code_escalates() -> None:
    active = rules("iban_mismatch")
    active[0].code = None

    verdict = decide_invoice(active, CLEAN)

    assert verdict.decision == "ESCALAR"
    assert "without code" in verdict.reason


def test_a_rule_that_needs_data_escalates_every_instance() -> None:
    active = rules("iban_mismatch")
    active[0].code = None
    active[0].report = {"needs_data": {"missing": ["symbol: delivery_date"]}}

    verdicts = decide(active, OUTCOMES, [(1, CLEAN), (2, NEW_IBAN)], SOURCES, [], RUN)

    assert [v.decision for v in verdicts] == ["ESCALAR", "ESCALAR"]
    assert {v.reason for v in verdicts} == {"RULE_NEEDS_DATA 1: missing symbol: delivery_date"}


def test_a_rule_whose_compile_failed_escalates_every_instance() -> None:
    active = rules("iban_mismatch")
    active[0].code = None
    active[0].report = {"valid": False, "error": "AgentError: every model failed"}

    verdicts = decide(active, OUTCOMES, [(1, CLEAN), (2, NEW_IBAN)], SOURCES, [], RUN)

    assert [v.decision for v in verdicts] == ["ESCALAR", "ESCALAR"]
    assert {v.reason for v in verdicts} == {"RULE_COMPILE_FAILED 1: AgentError: every model failed"}


def test_each_instance_sees_the_others_but_not_itself() -> None:
    seen: list = []
    run = dataset_runner({"iban_mismatch": RULES_V3["iban_mismatch"][2]}, seen)
    population = [(1, {**CLEAN, "_instance": "a"}), (2, {**NEW_IBAN, "_instance": "b"})]

    verdicts = decide(
        rules("iban_mismatch"), OUTCOMES, [(1, CLEAN), (2, NEW_IBAN)], SOURCES, population, run
    )

    assert [v.decision for v in verdicts] == ["PAGAR", "ESCALAR"]
    assert [others for _, _, others in seen] == [
        [{**NEW_IBAN, "_instance": "b"}],
        [{**CLEAN, "_instance": "a"}],
    ]


def test_rules_can_run_in_parallel_without_changing_result_order() -> None:
    lock = threading.Lock()
    both_running = threading.Event()
    active = 0

    def run(code: str, instances: list, sources: dict, population: list) -> list:
        nonlocal active
        with lock:
            active += 1
            if active == 2:
                both_running.set()
        both_running.wait(1)
        with lock:
            active -= 1
        return [{"fires": code == "order_already_paid", "reason": code}] * len(instances)

    [verdict] = decide(
        rules("iban_mismatch", "order_already_paid"),
        OUTCOMES,
        [(1, CLEAN)],
        SOURCES,
        [(1, CLEAN)],
        run,
        rule_workers=2,
    )

    assert both_running.is_set()
    assert [result.rule_id for result in verdict.results] == [1, 2]
    assert verdict.decision == "NO_PAGAR"


# ADR 0025: a scan is read and decided, but a rejection on data read by OCR escalates.
IBAN_REJECTS = [
    Rule(id=1, text="iban", type="prohibition", decision="NO_PAGAR", code="iban_mismatch", hash="h")
]


WITH_TOTAL = Outcomes(
    OUTCOMES.priorities, "PAGAR", "ESCALAR", required=(*REQUIRED.required, "total")
)


def decide_scan(instance: dict[str, Any], unconfirmed: list[str] | None) -> Any:
    """`unconfirmed` None: a text PDF; a list: a scan and the symbols its readers doubted."""
    scans = {} if unconfirmed is None else {1: unconfirmed}
    instance = {"total": "919.60", **instance}
    [verdict] = decide(IBAN_REJECTS, WITH_TOTAL, [(1, instance)], SOURCES, [], RUN, scans)
    return verdict


def test_a_scan_the_rules_would_reject_escalates_naming_the_rule() -> None:
    verdict = decide_scan(NEW_IBAN, [])

    assert verdict.decision == "ESCALAR"
    assert verdict.reason == "SCAN_REVIEW: iban_mismatch"
    assert [(r.rule_id, r.fires) for r in verdict.results] == [(1, True)]


def test_a_clean_scan_is_paid() -> None:
    assert decide_scan(CLEAN, []).decision == "PAGAR"


def test_a_text_pdf_with_the_same_mismatch_is_still_rejected() -> None:
    verdict = decide_scan(NEW_IBAN, None)

    assert (verdict.decision, verdict.reason) == ("NO_PAGAR", "iban_mismatch")


def test_a_scan_with_a_null_field_is_missing_data() -> None:
    verdict = decide_scan({**NEW_IBAN, "iban": None}, ["iban"])

    assert (verdict.decision, verdict.reason) == ("ESCALAR", "MISSING_DATA: iban")


def test_a_scan_with_a_conflicting_total_escalates_whatever_the_rules_say() -> None:
    """Readers disagreed on the total: a clean scan is not paid on it. A symbol no rule
    requires does not count."""
    verdict = decide_scan(CLEAN, ["total", "free_text"])

    assert (verdict.decision, verdict.reason) == ("ESCALAR", "UNVERIFIED_DATA: total")
    assert decide_scan(CLEAN, ["free_text"]).decision == "PAGAR"
