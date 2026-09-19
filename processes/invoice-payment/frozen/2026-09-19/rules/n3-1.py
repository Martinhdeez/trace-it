from decimal import Decimal, ROUND_HALF_UP


def text(value):
    """Anything a source or an extractor gives us, as a comparable string."""
    return "" if value is None else str(value).strip()


def empty(value):
    return text(value) == ""


def num(value):
    """Amounts may arrive as a number or as text, with a dot or a comma."""
    s = text(value)
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return Decimal(s)


def cents(value):
    return int((num(value) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def fires(reason):
    return {"fires": True, "reason": reason}


def passes():
    return {"fires": False, "reason": ""}


def evaluate(instance, sources, others):
    """The printed VAT is the base times the rate, rounded to the cent."""
    base = instance.get("base")
    rate = instance.get("vat_rate")
    vat = instance.get("vat_amount")
    if empty(base) or empty(rate) or empty(vat):
        return passes()
    expected = (num(base) * num(rate) / Decimal(100)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if abs(cents(expected) - cents(vat)) <= 1:
        return passes()
    return fires("VAT " + text(vat) + " != " + str(expected))
