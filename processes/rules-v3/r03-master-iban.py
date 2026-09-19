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
    """The invoice pays into the account the master approved."""
    nif = key(instance.get("issuer_nif"))
    if not nif or empty(instance.get("iban")):
        return passes()
    theirs = [r for r in rows(sources, "suppliers") if key(r.get("nif")) == nif]
    if not theirs:
        return passes()
    ids = {text(r.get("id")) for r in theirs}
    accounts = {iban(r.get("iban")) for r in theirs}
    if len(ids) > 1 or len(accounts) > 1:
        return passes()
    approved = accounts.pop()
    if iban(instance.get("iban")) != approved:
        return fires("IBAN " + iban(instance.get("iban")) + " is not the master's")
    return passes()
