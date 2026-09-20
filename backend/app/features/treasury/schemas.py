from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class TreasuryPlanIn(BaseModel):
    as_of: date
    weekly_budget: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    horizon_weeks: int = Field(default=52, ge=1, le=52)
    # Explicit scenario assumption; no implicit payment term is ever applied.
    default_payment_terms_days: int | None = Field(default=None, ge=0, le=3650)

    @field_validator("weekly_budget")
    @classmethod
    def cents_only(cls, value: Decimal) -> Decimal:
        if value != value.quantize(Decimal("0.01")):
            raise ValueError("weekly_budget must have at most two decimal places")
        return value

    @model_validator(mode="after")
    def valid_horizon(self) -> "TreasuryPlanIn":
        try:
            self.as_of + timedelta(days=self.horizon_weeks * 7 - 1)
        except OverflowError as error:
            raise ValueError("The planning horizon exceeds the supported date range") from error
        return self


class TreasuryProvenance(BaseModel):
    decision_id: int
    decision_author: str
    decision_at: datetime
    execution_id: int | None = None
    version_id: int | None = None
    rules_hash: str
    source_ids: list[int] = Field(default_factory=list)
    amount_source: str
    vendor_source: str
    due_date_source: str
    currency_source: str


class TreasuryRow(BaseModel):
    row_id: str
    instance_id: int
    decision_id: int
    name: str
    vendor: str
    amount: Decimal
    currency: str
    due_date: date
    week_index: int
    week_start: date
    provenance: TreasuryProvenance


class TreasuryExclusion(BaseModel):
    instance_id: int
    name: str
    decision_id: int | None = None
    reason_code: str
    reason: str
    amount: Decimal | None = None
    currency: str | None = None
    due_date: date | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class TreasuryWeek(BaseModel):
    index: int
    start: date
    end: date
    total: Decimal
    remaining_budget: Decimal
    row_ids: list[str]
    backlog_count: int
    backlog_amount: Decimal


class TreasurySupplier(BaseModel):
    vendor: str
    invoice_count: int
    scheduled_count: int
    scheduled_amount: Decimal
    backlog_count: int
    backlog_amount: Decimal


class TreasuryTotals(BaseModel):
    scheduled_count: int
    scheduled_amount: Decimal
    backlog_count: int
    backlog_amount: Decimal
    excluded_count: int
    excluded_amount: Decimal


class TreasuryPlanOut(BaseModel):
    process_id: int
    as_of: date
    weekly_budget: Decimal
    horizon_weeks: int
    currency: str
    rows: list[TreasuryRow]
    weeks: list[TreasuryWeek]
    suppliers: list[TreasurySupplier]
    exclusions: list[TreasuryExclusion]
    totals: TreasuryTotals
