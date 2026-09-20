"""The hand-written v3 rules, run for real in the sandbox.

One case per rule that must fire, plus an invoice that must leave all eighteen silent. When
the compiler starts generating these, this file is what its output has to agree with.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.features.agents import sandbox
from app.features.decisions.engine import decide
from tests.support import pack

RULES = pack.rules()
OUTCOMES = pack.outcomes()
RATES = json.loads((pack.PACK / "invoice-payment" / "rates.json").read_text(encoding="utf-8"))

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
    "rates": RATES,
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
    # A foreign invoice whose total does not become the order's amount at the published rate.
    18: ({"currency": "USD"}, {}, []),
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


# --- The currency policy (R18) ------------------------------------------------------------
#
# Money is only compared inside one currency. A foreign invoice is escalated when we cannot
# convert it with a published rate in force on its own date, or when its own arithmetic does
# not hold; it is never refused for a difference measured in another currency.

FOREIGN = {**CLEAN, "currency": "USD", "base": 1000.00, "vat_amount": 210.00, "total": 1210.00}
USD = next(r for r in RATES if r["currency"] == "USD")
# 1210.00 USD x 0.92 = 1113.20 EUR: the order of a foreign invoice is in EUR, like every order.
FOREIGN_SOURCES = {**SOURCES, "orders": [{**ORDER, "total_amount": 1113.20}]}


def r18(instance: dict, sources: dict) -> dict[str, Any]:
    return run(18, instance, sources, [])


def test_a_foreign_invoice_that_converts_into_its_order_is_not_escalated() -> None:
    result = r18(FOREIGN, FOREIGN_SOURCES)

    assert result["fires"] is False
    assert "USD 1210.0 x 0.92" in result["reason"], "the trace shows the conversion that passed"
    assert "= 1113.20 EUR = order 1113.2" in result["reason"]


def test_a_foreign_invoice_outside_the_tolerance_is_escalated() -> None:
    sources = {**SOURCES, "orders": [{**ORDER, "total_amount": 1200.00}]}

    result = r18(FOREIGN, sources)

    assert result["fires"] is True
    assert "CONVERSION_OUTSIDE_TOLERANCE" in result["reason"]
    assert "rate in force 2026-01-02..2026-12-31" in result["reason"]


def test_a_currency_with_no_published_rate_is_escalated() -> None:
    sources = {**FOREIGN_SOURCES, "rates": [r for r in RATES if r["currency"] != "USD"]}

    result = r18(FOREIGN, sources)

    assert result["fires"] is True
    assert "NO_PUBLISHED_RATE: USD" in result["reason"]


def test_an_invoice_dated_outside_every_window_is_escalated() -> None:
    result = r18({**FOREIGN, "date": "2025-12-31"}, FOREIGN_SOURCES)

    assert result["fires"] is True
    assert "NO_PUBLISHED_RATE: USD on 2025-12-31" in result["reason"]


def test_each_invoice_takes_the_rate_in_force_on_its_own_date() -> None:
    """A rate change is a new row with its own window, never an edit of the old one."""
    older = {**USD, "eur_per_unit": "0.80", "as_of": "2025-01-01", "valid_until": "2025-12-31"}
    sources = {**FOREIGN_SOURCES, "rates": [older, USD]}
    last_year = {**FOREIGN, "date": "2025-06-30"}  # 1210.00 x 0.80 = 968.00

    assert r18(FOREIGN, sources)["fires"] is False, "2026 takes 0.92"
    assert r18(last_year, sources)["fires"] is True, "2025 takes 0.80, which is not the order"
    assert "x 0.80" in r18(last_year, sources)["reason"]
    assert r18(last_year, {**sources, "orders": [{**ORDER, "total_amount": 968.00}]})["fires"] is (
        False
    )


def test_an_unknown_currency_code_is_escalated() -> None:
    result = r18({**FOREIGN, "currency": "$"}, FOREIGN_SOURCES)

    assert result["fires"] is True
    assert "UNKNOWN_CURRENCY: $" in result["reason"]


# --- The eight foreign invoices of batch 2 ------------------------------------------------

REVIEWED = json.loads(
    (
        Path(__file__).resolve().parents[2] / "ingestion/tests/fixtures/batch2-reviewed-fields.json"
    ).read_text(encoding="utf-8")
)
SYMBOLS = {
    "supplier_tax_id": "issuer_nif",
    "payment_iban": "iban",
    "issued_on": "date",
    "purchase_order_ref": "purchase_order",
    "net_amount": "base",
    "vat_rate": "vat_rate",
    "vat_amount": "vat_amount",
    "gross_amount": "total",
    "currency": "currency",
}
# The cumulative master and ERP the batch-2 update brings, for the eight foreign invoices
# (`proveedores_nuevos.csv`, `pedidos_nuevos.csv`, `erp_export_lote2.csv`).
BATCH2_ORDERS = [
    ("PO-2026-1302", "P002", "A41220987", "2254.00"),
    ("PO-2026-1309", "P015", "5010401075570", "5244.50"),
    ("PO-2026-1310", "P006", "A46990201", "3174.00"),
    ("PO-2026-1311", "P011", "B90233808", "3393.00"),
    ("PO-2026-1312", "P010", "B98455101", "4410.00"),
    ("PO-2026-1313", "P014", "12.345.678/0001-95", "2500.00"),
    ("PO-2026-1314", "P004", "B98120774", "2290.00"),
    ("PO-2026-1315", "P012", "DE812345678", "5670.00"),
]
BATCH2_SOURCES: dict[str, list[dict[str, Any]]] = {
    "suppliers": [
        {"id": "P002", "nif": "A41220987", "iban": "ES76 2100 0813 6101 2345 6789"},
        {"id": "P004", "nif": "B98120774", "iban": "ES44 1465 0100 9517 0430 2211"},
        {"id": "P006", "nif": "A46990201", "iban": "ES35 2038 5778 9830 0076 5410"},
        {"id": "P010", "nif": "B98455101", "iban": "ES27 0239 0806 6671 2233 4455"},
        {"id": "P011", "nif": "B90233808", "iban": "ES93 6888 4400 1235 8890 0142"},
        {"id": "P012", "nif": "DE812345678", "iban": "DE89 3704 0044 0532 0130 00"},
        {"id": "P014", "nif": "12.345.678/0001-95", "iban": "BR97 0036 0305 0000 1000 9795 493C1"},
        {"id": "P015", "nif": "5010401075570", "iban": "JP01 0001 2331 2345 6789 012"},
    ],
    "orders": [
        {
            "purchase_order": ref,
            "supplier_id": supplier,
            "nif": nif,
            "total_amount": amount,
            "status": "ABIERTO",
            "order_date": "2026-09-14",
        }
        for ref, supplier, nif, amount in BATCH2_ORDERS
    ],
    "erp": [
        {
            "entry_id": "AS-9" + ref[-4:],
            "date": "2026-09-15",
            "supplier_id": supplier,
            "nif": nif,
            "purchase_order": ref,
            "amount": amount,
            "status": "PENDIENTE",
        }
        for ref, supplier, nif, amount in BATCH2_ORDERS
    ],
    "parameters": [{"cut_off_date": "2026-09-19"}],
    "rates": RATES,
}
# What each foreign invoice must end as, and which rules say so. The two refusals fail on
# their own data, in their own currency: R10's arithmetic and R03's account. On the six
# reviews only R18 fires, so the reviewer agent has one rule to amend (docs/reviewer-agent.md).
FOREIGN_BATCH2 = {
    "e02_P002.pdf": ("ESCALAR", [18]),
    "e09_P015.pdf": ("ESCALAR", [18]),
    "e10_P006.pdf": ("ESCALAR", [18]),
    "e11_P011.pdf": ("NO_PAGAR", [3]),
    "e12_P010.pdf": ("ESCALAR", [18]),
    "e13_P014.pdf": ("ESCALAR", [18]),
    "e14_P004.pdf": ("NO_PAGAR", [10]),
    "e15_P012.pdf": ("ESCALAR", [18]),
}


def batch2_instance(file_id: str) -> dict[str, Any]:
    fields = next(r["fields"] for r in REVIEWED if r["file_id"] == file_id)
    return {SYMBOLS[k]: v for k, v in fields.items() if k in SYMBOLS}


@pytest.mark.parametrize("file_id", sorted(FOREIGN_BATCH2))
def test_the_foreign_invoices_of_batch_2(file_id: str) -> None:
    """Every rule, in the real sandbox, over the reviewed symbols of the eight foreign
    invoices of batch 2 and the cumulative sources that batch brings."""
    expected = FOREIGN_BATCH2[file_id]
    population = [(f, {**batch2_instance(f), "_instance": f}) for f in sorted(FOREIGN_BATCH2)]

    [verdict] = decide(
        RULES,
        OUTCOMES,
        [(file_id, batch2_instance(file_id))],
        BATCH2_SOURCES,
        population,
        sandbox.run_dataset,
    )

    fired = [r.rule_id for r in verdict.results if r.fires]
    assert (verdict.decision, fired) == expected, verdict.reason
