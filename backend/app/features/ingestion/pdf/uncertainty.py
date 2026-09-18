"""Preserve unreadable fragments and prevent uncertain readings becoming usable values."""

import re

from app.common.extraction import Candidate, Evidence
from app.common.normalization import fold

UNREADABLE = re.compile(r"\b(?:ILLEGIBLE|ILEGIBLE|UNREADABLE|UNCLEAR|NO LEGIBLE)\b|\?|\ufffd")
LABELS = {
    "supplier_tax_id": r"\bNIF\b",
    "payment_iban": r"\bIBAN\b",
    "purchase_order_ref": r"\b(?:PEDIDO|PO)\b",
    "invoice_number": r"^(?:FACTURA|INVOICE|REF FACTURA|N[Oº°] DE FACTURA)\b",
    "issued_on": r"\bFECHA\b",
    "net_amount": r"\b(?:BASE|SUBTOTAL)\b",
    "vat_amount": r"\b(?:IVA|CUOTA)\b",
    "vat_rate": r"\bIVA\b",
    "gross_amount": r"\bTOTAL\b",
    "currency": r"\b(?:MONEDA|DIVISA|CURRENCY)\b",
}


def preserve_unreadable(fields, lines):
    warnings = []
    for line in lines:
        text = fold(line.text)
        if not UNREADABLE.search(text):
            continue
        names = [name for name, pattern in LABELS.items() if re.search(pattern, text)]
        if not names:
            if line.method in {"ocr", "vlm"} or "?" not in text:
                warnings.append({"code": "UNREADABLE_REGION", "locator": line.id})
            continue
        for name in names:
            field = fields[name]
            if any(
                c.error == "UNREADABLE_TEXT" and c.evidence.locator == line.id
                for c in field.candidates
            ):
                field.value, field.status = None, "UNVERIFIED"
                continue
            field.candidates.append(
                Candidate(
                    value=None,
                    raw=line.text,
                    error="UNREADABLE_TEXT",
                    evidence=Evidence(
                        locator=line.id,
                        text=line.raw,
                        method=line.method,
                        page=line.page,
                        bbox=line.bbox,
                        confidence=line.confidence,
                        preprocessing=line.preprocessing,
                    ),
                )
            )
            field.value, field.status = None, "UNVERIFIED"
            warnings.append({"code": "UNREADABLE_FIELD", "field": name, "locator": line.id})
    return warnings
