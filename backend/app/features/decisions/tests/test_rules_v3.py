"""The hand-written v3 rules, run for real in the sandbox.

One case per rule that must fire, plus an invoice that must leave all seventeen silent. When
the compiler starts generating these, this file is what its output has to agree with.
"""

from typing import Any

import pytest

from app.features.agents import sandbox
from app.features.decisions.engine import decide
from tests.support import pack

RULES = pack.rules()
OUTCOMES = pack.outcomes()

CLEAN: dict[str, Any] = {
    "issuer_nif": "B96233419",
    "iban": "ES21 0075 2345 6706 0012 3456",
    "purchase_order": "PO-2026-0008",
    "date": "2026-05-02",
    "base": 8494.10,
    "vat_rate": 21,
    "vat_amount": 1783.76,
    "total": 10277.86,
}
SUPPLIER = {"id": "P007", "nif": "B96233419", "iban": "ES2100752345670600123456"}
ORDER = {
    "purchase_order": "PO-2026-0008",
    "supplier_id": "P007",
    "nif": "B96233419",
    "total_amount": 10277.86,
    "status": "ABIERTO",
}
ENTRY = {
    "purchase_order": "PO-2026-0008",
    "supplier_id": "P007",
    "nif": "B96233419",
    "amount": 10277.86,
    "status": "PENDIENTE",
}
SOURCES: dict[str, list[dict[str, Any]]] = {
    "suppliers": [SUPPLIER],
    "orders": [ORDER],
    "erp": [ENTRY],
    "parameters": [{"cut_off_date": "2026-09-18"}],
}

# Per rule (1-based): what to change so that it, and only it, has something to say.
WHAT_MAKES_IT_FIRE: dict[int, tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]] = {
    1: ({"iban": None}, {}, []),
    2: ({"issuer_nif": "B00000000"}, {}, []),
    3: ({"iban": "ES39 0081 5290 0700 1234 5678"}, {}, []),
    4: ({}, {"suppliers": [SUPPLIER, {**SUPPLIER, "iban": "ES3900815290070012345678"}]}, []),
    5: ({"purchase_order": "PO-2026-9999"}, {}, []),
    6: ({}, {"orders": [{**ORDER, "nif": "A41220987"}]}, []),
    7: ({}, {"orders": [{**ORDER, "total_amount": 9999.00}]}, []),
    8: ({"vat_amount": 400.00}, {}, []),
    9: ({"vat_rate": 10}, {}, []),
    10: ({"total": 9999.99}, {}, []),
    11: ({"date": "2026-02-31"}, {}, []),
    12: ({"date": "2027-01-01"}, {}, []),
    13: ({}, {"erp": []}, []),
    14: ({}, {"erp": [{**ENTRY, "amount": 9999.00}]}, []),
    15: ({}, {"erp": [{**ENTRY, "status": "PAGADA"}]}, []),
    16: ({}, {}, [{**CLEAN, "_instance": "other_invoice.pdf"}]),
    # One digit away from the master: our misreading far more often than a new account.
    17: ({"iban": "ES21 0075 2345 6706 0012 3457"}, {}, []),
}


def run(number: int, instance: dict, sources: dict, others: list) -> dict[str, Any]:
    [result] = sandbox.run_batch(RULES[number - 1].code, [(instance, sources, others)])
    if isinstance(result, sandbox.SandboxError):
        raise result
    return result


@pytest.mark.parametrize("number", sorted(WHAT_MAKES_IT_FIRE))
def test_each_rule_fires_when_it_should(number: int) -> None:
    symbols, sources, others = WHAT_MAKES_IT_FIRE[number]

    result = run(number, {**CLEAN, **symbols}, {**SOURCES, **sources}, others)

    assert result["fires"] is True
    assert result["reason"], "a rule that fires explains why"


@pytest.mark.parametrize("number", sorted(WHAT_MAKES_IT_FIRE))
def test_no_rule_fires_on_a_correct_invoice(number: int) -> None:
    assert run(number, CLEAN, SOURCES, [])["fires"] is False


@pytest.mark.parametrize("number", sorted(WHAT_MAKES_IT_FIRE))
def test_no_rule_fails_without_symbols_or_sources(number: int) -> None:
    """Missing evidence is not an error: the rule that checks for it is the one that fires."""
    result = run(number, {}, {}, [])

    assert result["fires"] is (number == 1)


def decide_invoice(instance: dict, sources: dict, others: list[dict]) -> str:
    population = [(0, {**instance, "_instance": "this.pdf"})] + [
        (n, other) for n, other in enumerate(others, 1)
    ]
    [verdict] = decide(RULES, OUTCOMES, [(0, instance)], sources, population, sandbox.run_dataset)
    return verdict.decision


def test_the_whole_process_on_the_three_reference_invoices() -> None:
    """The whole norm at once, on the three cases the rules draft calls out."""
    already_paid = {"erp": [{**ENTRY, "status": "PAGADA"}]}
    new_iban = {"iban": "ES39 0081 5290 0700 1234 5678"}

    assert decide_invoice(CLEAN, SOURCES, []) == "PAGAR"
    assert decide_invoice(CLEAN, {**SOURCES, **already_paid}, []) == "NO_PAGAR"
    assert decide_invoice({**CLEAN, **new_iban}, SOURCES, []) == "NO_PAGAR"


def test_an_iban_a_character_away_from_the_master_goes_to_a_person() -> None:
    """A misread account must not become a refusal. Measured on batch 1: a supplier's new
    account differs from the master in 15 to 20 of its 24 characters, an OCR slip in one
    or two, so the two cases never meet."""
    misread = {"iban": "ES21 0075 2345 6706 0012 3457"}  # the master's, last digit apart
    another_account = {"iban": "ES39 0081 5290 0700 1234 5678"}

    assert decide_invoice({**CLEAN, **misread}, SOURCES, []) == "ESCALAR"
    assert decide_invoice({**CLEAN, **another_account}, SOURCES, []) == "NO_PAGAR"


def test_escalar_beats_no_pagar() -> None:
    """An invoice that is both wrong and suspicious goes to a person, not to a refusal."""
    broken = {**CLEAN, "vat_rate": 10, "vat_amount": 849.41, "total": 9343.51}
    sources = {**SOURCES, "erp": [{**ENTRY, "status": "PAGADA"}]}

    assert decide_invoice(broken, sources, []) == "ESCALAR"


def test_a_duplicate_order_escalates_both_invoices() -> None:
    assert decide_invoice(CLEAN, SOURCES, [{**CLEAN, "_instance": "twin.pdf"}]) == "ESCALAR"
