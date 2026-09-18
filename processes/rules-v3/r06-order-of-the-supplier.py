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
    """The order belongs to the supplier that issued the invoice."""
    nif = key(instance.get("issuer_nif"))
    order = key(instance.get("purchase_order"))
    if not nif or not order:
        return passes()
    its = None
    for row in rows(sources, "orders"):
        if key(row.get("purchase_order")) == order:
            its = row
    if its is None:
        return passes()
    if not empty(its.get("nif")):
        if key(its.get("nif")) != nif:
            return fires("The order belongs to " + key(its.get("nif")) + ", not " + nif)
        return passes()
    supplier = None
    for row in rows(sources, "suppliers"):
        if key(row.get("nif")) == nif:
            supplier = row
    if supplier is None:
        return passes()
    if text(its.get("supplier_id")) != text(supplier.get("id")):
        return fires("The order belongs to supplier " + text(its.get("supplier_id")))
    return passes()
