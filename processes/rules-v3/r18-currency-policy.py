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


def number(value):
    """A printed amount as a Decimal, or None when it is not one."""
    try:
        return Decimal(text(value))
    except Exception:
        return None


def published_rate(rates, currency, day):
    """The `rates` row for this currency whose as_of..valid_until covers the invoice's day,
    or None: the rate in force on the day the invoice was issued, never the nearest one and
    never a clock. Rates are published figures the manager loads; none is ever derived from
    an order or an ERP amount."""
    if day is None:
        return None
    for row in rates:
        if text(row.get("currency")).upper() != currency:
            continue
        since, until = date_of(row.get("as_of")), date_of(row.get("valid_until"))
        if since is None or until is None or not (since <= day <= until):
            continue
        if number(row.get("eur_per_unit")) is None:
            continue
        return row
    return None


def order_of(instance, orders):
    """The `orders` row of this invoice's purchase order, or None."""
    order = key(instance.get("purchase_order"))
    found = None
    for row in orders:
        if order and key(row.get("purchase_order")) == order:
            found = row
    return found


def broken_arithmetic(instance):
    """R10's check: the invoice does not add up in its own currency, whatever that is."""
    for symbol in ("base", "vat_amount", "total"):
        if empty(instance.get(symbol)):
            return False
    base, vat, total = (number(instance.get(s)) for s in ("base", "vat_amount", "total"))
    if base is None or vat is None or total is None:
        return False
    return not matches(total, base + vat)


def another_account(instance, suppliers):
    """R03's check: the invoice pays into an account the master did not approve, far enough
    from it that it is not a misreading (R17's 4 characters)."""
    nif = key(instance.get("issuer_nif"))
    if not nif or empty(instance.get("iban")):
        return False
    theirs = [r for r in suppliers if key(r.get("nif")) == nif]
    accounts = {iban(r.get("iban")) for r in theirs}
    if len(theirs) == 0 or len({text(r.get("id")) for r in theirs}) > 1 or len(accounts) > 1:
        return False
    approved = accounts.pop()
    mine = iban(instance.get("iban"))
    if mine == approved:
        return False
    previous = list(range(len(approved) + 1))
    for i, a in enumerate(mine, 1):
        current = [i]
        for j, b in enumerate(approved, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1] > 4


def vat_disagrees(instance):
    """The VAT printed on the invoice is not the one its own printed rate implies. Pure
    arithmetic inside the document: it needs no exchange rate."""
    for symbol in ("base", "vat_rate", "vat_amount"):
        if empty(instance.get(symbol)):
            return ""
    base, rate = number(instance.get("base")), number(instance.get("vat_rate"))
    amount = number(instance.get("vat_amount"))
    if base is None or rate is None or amount is None:
        return ""
    expected = (base * rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if matches(amount, expected):
        return ""
    return "VAT " + text(instance.get("vat_amount")) + " != " + str(expected)


def evaluate(instance, sources, others):
    """Money is only compared inside one currency. A foreign invoice we cannot convert with
    a published rate, or whose own arithmetic does not hold, goes to a person; it is never
    refused for anything measured in another currency."""
    currency = text(instance.get("currency")).upper()
    if currency in ("", "EUR"):
        return passes()
    # ponytail: these two carve-outs repeat what R10 and R03 already check. The engine takes
    # the highest-priority rule that fired and ESCALAR outranks NO_PAGAR, so a rule has no
    # way to say "stay quiet, a rejection already fired"; without them a foreign invoice with
    # a wrong total or a stranger's IBAN would escalate instead of being refused. Ceiling: a
    # third rejection reason has to be repeated here too. Lift it with a "suppress if a
    # rejection fired" notion in the engine, which ADR 0035 leaves out for now.
    if broken_arithmetic(instance) or another_account(instance, rows(sources, "suppliers")):
        return passes()
    reasons = []
    arithmetic = ""
    if not (len(currency) == 3 and currency.isalpha()):
        reasons.append("UNKNOWN_CURRENCY: " + currency)
    else:
        rate = published_rate(rows(sources, "rates"), currency, date_of(instance.get("date")))
        total = number(instance.get("total"))
        order = order_of(instance, rows(sources, "orders"))
        expected = number((order or {}).get("total_amount"))
        if rate is None:
            reasons.append("NO_PUBLISHED_RATE: " + currency + " on " + text(instance.get("date")))
        elif total is not None and expected is not None:
            converted = (total * number(rate["eur_per_unit"])).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            pct = number(rate.get("tolerance_pct")) or Decimal("0")
            allowed = max(Decimal("0.01"), (converted * pct / Decimal("100")).copy_abs())
            off = abs(converted - expected) > allowed
            # The whole sum, so a reader can redo it and see which rate applied and why.
            arithmetic = (
                currency + " " + text(instance.get("total")) + " x " + text(rate["eur_per_unit"])
                + " (rate in force " + text(rate.get("as_of")) + ".." + text(rate.get("valid_until"))
                + ", ref. " + text(rate.get("reference")) + ") = " + str(converted)
                + " EUR " + ("!=" if off else "=") + " order " + str(expected)
            )
            if off:
                reasons.append("CONVERSION_OUTSIDE_TOLERANCE: " + arithmetic)
    if problem := vat_disagrees(instance):
        reasons.append(problem)
    if reasons:
        if arithmetic and not any(r.startswith("CONVERSION") for r in reasons):
            reasons.append(arithmetic)  # the conversion held; something else did not
        return fires("CURRENCY_REVIEW " + currency + ": " + " | ".join(reasons))
    # It passes, and the trace still records the conversion that let it pass.
    return {"fires": False, "reason": arithmetic}
