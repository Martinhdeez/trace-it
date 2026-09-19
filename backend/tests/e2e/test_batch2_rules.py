"""Order-independent ERP history and an explicit, conservative currency policy."""

from itertools import permutations

import pytest

from app.features.agents import sandbox
from tests.support import pack


def run(number, instance, sources):
    code = pack.codes()[number - 1]
    [result] = sandbox.run_dataset(code, [(1, instance)], sources, [], timeout_s=30)
    assert isinstance(result, dict), result
    return result


@pytest.mark.parametrize("currency", [None, "EUR", "USD", "JPY", "BRL", "GBP", "CHF", "MXN"])
def test_amounts_are_only_compared_in_the_reference_currency(currency):
    invoice = {"purchase_order": "PO-2026-1234", "currency": currency, "total": "100"}
    sources = {"orders": [{"purchase_order": invoice["purchase_order"], "total_amount": "200"}]}
    foreign = currency not in {None, "EUR"}
    assert run(7, invoice, sources)["fires"] is not foreign
    assert run(18, invoice, sources)["fires"] is foreign


def test_paid_history_is_never_hidden_by_a_pending_entry():
    entries = [
        {"purchase_order": "PO-2026-0071", "status": status}
        for status in ("PENDIENTE", "PAGADA", "PENDIENTE")
    ]
    for ordering in permutations(entries):
        assert run(15, {"purchase_order": "PO-2026-0071"}, {"erp": list(ordering)})["fires"]


def test_erp_discrepancies_cannot_be_hidden_by_row_order():
    order = {"purchase_order": "PO-2026-0071", "total_amount": "100", "supplier_id": "P001"}
    entries = [{**order, "amount": amount} for amount in ("100", "200")]
    for ordering in permutations(entries):
        result = run(14, order, {"orders": [order], "erp": list(ordering)})
        assert result == {"fires": True, "reason": "ERP and orders differ in: amount"}
