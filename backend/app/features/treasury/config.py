"""The invoice-payment to treasury boundary.

The deterministic decision engine remains process agnostic. These names are deliberately kept
here so planning cannot accidentally become a second decision engine.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class InvoicePaymentTreasuryConfig:
    eligible_outcomes: frozenset[str] = frozenset({"PAGAR"})
    amount_symbols: tuple[str, ...] = ("total", "amount")
    vendor_symbols: tuple[str, ...] = ("issuer_name", "vendor", "supplier_name", "issuer_nif")
    due_date_symbols: tuple[str, ...] = ("due_date", "payment_due_date", "due_on")
    issue_date_symbols: tuple[str, ...] = ("date", "issue_date", "issued_on")
    currency_symbols: tuple[str, ...] = ("currency", "currency_code")
    order_symbols: tuple[str, ...] = ("purchase_order", "order")
    source_names: tuple[str, ...] = ("orders", "suppliers")
    due_date_source_fields: tuple[str, ...] = ("due_date", "payment_due_date", "due_on")
    terms_source_fields: tuple[str, ...] = (
        "payment_terms_days",
        "terms_days",
        "net_days",
        "payment_terms",
        "condiciones_days",
    )


INVOICE_PAYMENT = InvoicePaymentTreasuryConfig()
