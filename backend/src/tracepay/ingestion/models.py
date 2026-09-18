from typing import Literal

from pydantic import BaseModel, Field

FieldStatus = Literal["OBSERVED", "MISSING", "INVALID", "AMBIGUOUS", "LOW_CONFIDENCE", "UNVERIFIED"]


class Evidence(BaseModel):
    locator: str
    text: str
    method: str
    page: int | None = None
    bbox: list[float] | None = None
    confidence: float | None = None
    preprocessing: list[str] = Field(default_factory=list)


class Candidate(BaseModel):
    value: str | None
    raw: str
    evidence: Evidence
    error: str | None = None


class ExtractedField(BaseModel):
    value: str | None = None
    status: FieldStatus = "MISSING"
    candidates: list[Candidate] = Field(default_factory=list)
    origin: str = "DOCUMENT"


class TextLine(BaseModel):
    id: str
    page: int
    raw: str
    text: str
    bbox: list[float]
    method: str = "native"
    confidence: float | None = None
    preprocessing: list[str] = Field(default_factory=list)


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
