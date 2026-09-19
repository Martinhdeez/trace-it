from decimal import Decimal, ROUND_HALF_UP


def text(value):
    """Anything a source or an extractor gives us, as a comparable string."""
    return "" if value is None else str(value).strip()


def empty(value):
    return text(value) == ""


def cents(value):
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def fires(reason):
    return {"fires": True, "reason": reason}


def passes():
    return {"fires": False, "reason": ""}


def evaluate(instance, sources, others):
    """The printed total is the base plus the VAT."""
    if empty(instance.get("base")) or empty(instance.get("vat_amount")) or empty(instance.get("total")):
        return passes()
    expected = cents(instance.get("base")) + cents(instance.get("vat_amount"))
    printed = cents(instance.get("total"))
    if abs(expected - printed) > 1:
        return fires(
            "Total " + text(instance.get("total")) + " != base + VAT ("
            + text(instance.get("base")) + " + " + text(instance.get("vat_amount")) + ")"
        )
    return passes()
