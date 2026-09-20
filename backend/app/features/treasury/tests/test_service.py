from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.features.treasury.config import INVOICE_PAYMENT
from app.features.treasury.schemas import TreasuryPlanIn
from app.features.treasury.service import _due_date, _evidence, _parse_decimal


def test_amounts_round_to_cents_without_float_math() -> None:
    assert _parse_decimal("10,005") == Decimal("10.01")
    assert _parse_decimal("not-an-amount") is None


def test_explicit_due_date_wins_over_scenario_terms() -> None:
    due, source, error = _due_date(
        {"due_date": "2026-02-10", "date": "2026-01-01"},
        {},
        INVOICE_PAYMENT,
        90,
    )
    assert (due, source, error) == (date(2026, 2, 10), "symbol:due_date", None)


def test_recorded_source_terms_are_evidence() -> None:
    due, source, error = _due_date(
        {"purchase_order": "PO-1", "date": "2026-01-01"},
        {"orders": [{"purchase_order": "PO-1", "payment_terms_days": 30}]},
        INVOICE_PAYMENT,
        None,
    )
    assert (due, source, error) == (date(2026, 1, 31), "source:orders.payment_terms_days", None)


def test_supplier_terms_fill_an_order_without_terms() -> None:
    due, source, error = _due_date(
        {"purchase_order": "PO-1", "issuer_nif": "B-1", "date": "2026-01-01"},
        {
            "orders": [{"purchase_order": "PO-1"}],
            "suppliers": [{"nif": "B-1", "payment_terms_days": 30}],
        },
        INVOICE_PAYMENT,
        None,
    )
    assert (due, source, error) == (date(2026, 1, 31), "source:suppliers.payment_terms_days", None)


def test_missing_due_date_is_not_guessed() -> None:
    due, source, error = _due_date({"date": "2026-01-01"}, {}, INVOICE_PAYMENT, None)
    assert due is None
    assert source == "missing"
    assert error


def test_request_rejects_fractional_cent_budget() -> None:
    with pytest.raises(ValueError):
        TreasuryPlanIn(as_of="2026-01-01", weekly_budget="10.001")


@pytest.mark.asyncio
async def test_execution_evidence_is_stale_when_a_source_snapshot_changes() -> None:
    instance = SimpleNamespace(
        id=7,
        process_id=3,
        file_hash="file-hash",
        symbols={"total": {"value": "10.00", "origin": "document:x"}},
    )
    engine = SimpleNamespace(execution_id=8, version_id=2, rules_hash="rules", instance_id=7)
    execution = SimpleNamespace(
        id=8,
        version_id=2,
        inputs={
            "instances": [{"id": 7, "file_hash": "file-hash", "symbols": instance.symbols}],
            "source_ids": [10],
        },
    )
    captured = SimpleNamespace(id=10, name="orders", rows=[{"purchase_order": "PO-1"}])
    current = SimpleNamespace(
        id=11, name="orders", rows=[{"purchase_order": "PO-1", "due_date": "2026-02-01"}]
    )

    class Session:
        source_queries = 0

        async def get(self, model, _id):
            return execution

        async def scalars(self, statement):
            if "sources" in str(statement):
                self.source_queries += 1
                return [captured] if self.source_queries == 1 else [current]
            return []

    from app.features.treasury import service

    original_sync_status = service.source_service.sync_status
    service.source_service.sync_status = lambda *args, **kwargs: _empty_sync()
    try:
        evidence = await _evidence(Session(), instance, engine)
    finally:
        service.source_service.sync_status = original_sync_status
    assert evidence.stale == "A current source differs from the captured decision snapshot"


@pytest.mark.asyncio
async def test_decision_without_execution_never_falls_back_to_current_symbols() -> None:
    instance = SimpleNamespace(
        id=7,
        process_id=3,
        file_hash="file-hash",
        symbols={"total": {"value": "10.00", "origin": "document:x"}},
    )
    decision = SimpleNamespace(
        execution_id=None,
        version_id=2,
        rules_hash="rules",
        instance_id=7,
    )

    evidence = await _evidence(object(), instance, decision)

    assert evidence.stale == "Decision execution snapshot is missing"
    assert evidence.symbols == {}
    assert evidence.tables == {}


async def _empty_sync() -> dict:
    return {}
