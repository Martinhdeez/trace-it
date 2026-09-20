import pytest
from pydantic import ValidationError

from app.features.treasury.schemas import TreasuryPlanIn


@pytest.mark.parametrize("budget", ["NaN", "Infinity", "1e100", "0", "-10", "10.001"])
def test_invalid_budget_is_rejected_before_scheduling(budget):
    with pytest.raises(ValidationError):
        TreasuryPlanIn(as_of="2026-01-01", weekly_budget=budget)


def test_date_overflow_is_a_validation_error():
    with pytest.raises(ValidationError, match="planning horizon"):
        TreasuryPlanIn(as_of="9999-12-31", weekly_budget="100.00", horizon_weeks=1)
