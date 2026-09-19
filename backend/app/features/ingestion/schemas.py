from typing import Literal

from pydantic import BaseModel, Field

from app.common.extraction import Candidate

CriticalField = Literal["supplier_tax_id", "payment_iban", "purchase_order_ref"]


class ExtractOptions(BaseModel):
    mode: Literal["local", "api", "hybrid"] | None = None
    ocr: bool = True
    secondary_ocr: bool = True
    focused_verification: bool = True
    source_verification: bool = True
    vlm: bool | None = None
    jev: bool | None = None
    verify_fields: list[CriticalField] = Field(default_factory=list, max_length=3)

    def normalized(self, settings) -> "ExtractOptions":
        mode = self.mode or settings.ocr_mode
        changes = {"mode": mode}
        if mode == "local":
            changes.update(vlm=False, jev=False)
        elif mode == "api":
            changes.update(ocr=False)
        return self.model_copy(update=changes)


class FieldReading(BaseModel):
    value: str | None = None
    proposed_value: str | None = None
    proposed_by: str | None = None
    verification: str = "unverified"
    verification_reason: str | None = None
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
