from typing import Literal

from pydantic import BaseModel, Field

from app.common.extraction import ExtractedField


class ExtractOptions(BaseModel):
    ocr: bool = True
    vlm: bool = False


class ExtractionResult(BaseModel):
    id: str
    file_id: str
    sha256: str
    kind: Literal["invoice", "workbook"]
    status: Literal["COMPLETE", "NEEDS_REVIEW"]
    fields: dict[str, ExtractedField] = Field(default_factory=dict)
    data: dict = Field(default_factory=dict)
    warnings: list[dict] = Field(default_factory=list)
    pages: list[dict] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    cache_hit: bool = False
    pipeline_version: str


REQUIRED_INVOICE_FIELDS = (
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
