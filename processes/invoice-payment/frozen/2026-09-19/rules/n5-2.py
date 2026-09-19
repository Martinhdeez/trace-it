from decimal import Decimal, ROUND_HALF_UP
from datetime import date


def text(value):
    """Anything a source or an extractor gives us, as a comparable string."""
    return "" if value is None else str(value).strip()


def empty(value):
    return text(value) == ""


def key(value):
    """NIF, IBAN and order references all compare uppercase without separators."""
    return text(value).upper().replace(" ", "").replace("-", "").replace(".", "")


def rows(sources, name):
    return sources.get(name) or []


def fires(reason):
    return {"fires": True, "reason": reason}


def passes():
    return {"fires": False, "reason": ""}


def evaluate(instance, sources, others):
    """The order was already paid. Never pay the same order twice."""
    order = key(instance.get("purchase_order"))
    if not order:
        return passes()
    for row in rows(sources, "erp"):
        if key(row.get("purchase_order")) != order:
            continue
        status = text(row.get("status")).upper()
        if status == "PAGADA":
            return fires("The ERP says PAGADA for " + order)
    return passes()
