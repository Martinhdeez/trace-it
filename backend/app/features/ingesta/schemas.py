from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.common.extraction import ExtractedField


class ExtractOptions(BaseModel):
    ocr: bool = True
    vlm: bool = False


class ReviewRequirement(BaseModel):
    required: bool = Field(
        default=False, description="Block automatic use when review is required."
    )
    action: Literal["CONTINUE", "HUMAN_REVIEW"] = Field(
        default="CONTINUE", description="Extraction handoff only; never a payment decision."
    )
    fields: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


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
    review: ReviewRequirement = Field(default_factory=ReviewRequirement)

    @model_validator(mode="before")
    @classmethod
    def require_review_for_legacy_results(cls, data):
        if isinstance(data, dict) and "review" not in data:
            return {
                **data,
                "status": "NEEDS_REVIEW",
                "review": {
                    "required": True,
                    "action": "HUMAN_REVIEW",
                    "reasons": ["LEGACY_RESULT_REEXTRACT"],
                },
            }
        return data


REQUIRED_INVOICE_FIELDS = (
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
