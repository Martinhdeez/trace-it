"""Bounded source-triggered OCR checks for the invoice-payment source schema.

Source values identify suspicious fields; they are never sent to a reader or
copied into a document. Business decisions still belong to the rule engine.
"""

import re
import uuid
from dataclasses import dataclass

from .schemas import CriticalField, ExtractionResult, ExtractOptions

PAYMENT_FIELDS = {
    "issuer_nif": "supplier_tax_id",
    "iban": "payment_iban",
    "invoice_number": "invoice_number",
    "date": "issued_on",
    "purchase_order": "purchase_order_ref",
    "base": "net_amount",
    "vat_rate": "vat_rate",
    "vat_amount": "vat_amount",
    "total": "gross_amount",
}
REQUIRED_PAYMENT_SYMBOLS = frozenset(PAYMENT_FIELDS) - {"invoice_number"}


def payment_symbols(result: ExtractionResult, names: set[str]) -> dict:
    """Map document values to the process contract; proposals never become facts."""
    values = {
        name: result.fields[field].value if field in result.fields else None
        for name, field in PAYMENT_FIELDS.items()
    }
    if values["date"] is None and "issued_on" in result.fields:
        match = re.fullmatch(
            r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})",
            (result.fields["issued_on"].text or "").strip(),
        )
        if match:
            day, month, year = map(int, match.groups())
            values["date"] = f"{year:04d}-{month:02d}-{day:02d}"
    values.update(file_id=result.file_id, free_text=result.text)
    return {
        name: {"value": values.get(name), "origin": origin(result, name)} for name in sorted(names)
    }


def origin(result: ExtractionResult, name: str) -> str:
    """No page with native text: every value was read by OCR or vision, and one its readers
    did not confirm says so (ADR 0025)."""
    if result.metrics.get("native_pages") != 0:
        return f"document:{result.id}"
    reading = result.fields.get(PAYMENT_FIELDS.get(name, ""))
    check = reading.verification if reading else "verified"
    return f"scan:{result.id}" + ("" if check == "verified" else f":{check}")


def key(value):
    return re.sub(r"[\s.\-]", "", str(value or "")).upper()


def verification_triggers(result: ExtractionResult, sources: dict) -> list[CriticalField]:
    if result.kind != "invoice":
        return []

    def value(name):
        reading = result.fields.get(name)
        return key(reading.value or reading.proposed_value) if reading else ""

    nif, iban, order = map(value, ("supplier_tax_id", "payment_iban", "purchase_order_ref"))
    suppliers = sources.get("suppliers", [])
    matching = [row for row in suppliers if key(row.get("nif")) == nif]
    triggers = set()
    if suppliers and nif and not matching:
        triggers.add("supplier_tax_id")
    authorized = {key(row.get("iban")) for row in matching} - {""}
    if len(authorized) == 1 and iban and iban not in authorized:
        triggers.add("payment_iban")
    for table in ("orders", "erp"):
        rows = sources.get(table, [])
        match = [row for row in rows if key(row.get("purchase_order")) == order]
        if rows and order and not match:
            triggers.add("purchase_order_ref")
        elif nif and match and all(row.get("nif") and key(row["nif"]) != nif for row in match):
            triggers.update(("supplier_tax_id", "purchase_order_ref"))
    # An explicit document observation can legitimately disagree with a master.
    # Already focused fields have consumed their retry budget for this result.
    return sorted(
        name
        for name in triggers
        if name not in result.data.get("focused_verification", {})
        and not any(c.evidence.method == "native" for c in result.fields[name].candidates)
    )


@dataclass
class PaymentReading:
    initial: ExtractionResult
    result: ExtractionResult
    triggers: list[CriticalField]


def extract_for_payment(service, item, options: ExtractOptions, sources: dict) -> PaymentReading:
    """At most one source-triggered extraction; preserve both persisted results."""
    if hasattr(service, "settings"):
        options = options.normalized(service.settings)
    initial = service.extract(item, options)
    triggers = verification_triggers(initial, sources)
    enabled = (
        options.source_verification
        and options.focused_verification
        and (options.ocr or options.mode == "api")
        and (
            options.vlm is True
            or (options.vlm is None and getattr(service.vlm, "configured", False))
        )
    )
    if not triggers or not enabled:
        return PaymentReading(initial, initial, triggers)
    updated = options.model_copy(
        update={"verify_fields": sorted(set(options.verify_fields + triggers))}
    )
    result = service.extract({**item, "id": uuid.uuid4().hex}, updated)
    return PaymentReading(initial, result, triggers)
