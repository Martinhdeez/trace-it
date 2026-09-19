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


def iban(value):
    return text(value).upper().replace(" ", "")


def cents(value):
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def matches(one, other):
    """The tolerance of the norm: one cent."""
    return abs(cents(one) - cents(other)) <= 1


def rows(sources, name):
    return sources.get(name) or []


def date_of(value):
    """The printed date as a real date, or None if no such day exists."""
    parts = text(value).split("-")
    if len(parts) != 3:
        return None
    try:
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None


def fires(reason):
    return {"fires": True, "reason": reason}


def passes():
    return {"fires": False, "reason": ""}

def evaluate(instance, sources, others):
    """The order must still be pending in the ERP: never pay it twice."""
    order = key(instance.get("purchase_order"))
    if not order:
        return passes()
    entry = None
    for row in rows(sources, "erp"):
        if key(row.get("purchase_order")) == order:
            entry = row
    if entry is None or empty(entry.get("status")):
        return passes()
    status = text(entry.get("status")).upper()
    if status != "PENDIENTE":
        return fires("The ERP says " + status)
    return passes()
