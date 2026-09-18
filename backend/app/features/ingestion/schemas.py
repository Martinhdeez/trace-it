from typing import Literal

from pydantic import BaseModel, Field

from app.common.extraction import Candidate


class ExtractOptions(BaseModel):
    ocr: bool = True
    vlm: bool | None = None
    jev: bool | None = None


class FieldReading(BaseModel):
    value: str | None = None
    text: str | None = None
    selected_by: str | None = None
    agreeing_readers: list[str] = Field(default_factory=list)
    confidence: float | None = None
    candidates: list[Candidate] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    id: str
    file_id: str
    sha256: str
    kind: Literal["invoice", "workbook"]
    fields: dict[str, FieldReading] = Field(default_factory=dict)
    text: str = ""
    data: dict = Field(default_factory=dict)
    warnings: list[dict] = Field(default_factory=list)
    pages: list[dict] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    cache_hit: bool = False
    pipeline_version: str


INVOICE_FIELDS = (
    "invoice_number",
    "supplier_tax_id",
    "payment_iban",
    "purchase_order_ref",
    "issued_on",
    "net_amount",
    "vat_rate",
    "vat_amount",
    "gross_amount",
    "currency",
)
