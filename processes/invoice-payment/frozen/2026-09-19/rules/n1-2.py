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


def rows(sources, name):
    return sources.get(name) or []


def fires(reason):
    return {"fires": True, "reason": reason}


def passes():
    return {"fires": False, "reason": ""}


def evaluate(instance, sources, others):
    """The invoice pays into the account the supplier master has for that NIF."""
    nif = key(instance.get("issuer_nif"))
    if not nif:
        return passes()
    printed = iban(instance.get("iban"))
    if not printed:
        return passes()
    theirs = [r for r in rows(sources, "suppliers") if key(r.get("nif")) == nif]
    if not theirs:
        return passes()
    accounts = [iban(r.get("iban")) for r in theirs]
    accounts = [a for a in accounts if a]
    if not accounts:
        return passes()
    if printed in accounts:
        return passes()
    return fires("IBAN_MISMATCH")
