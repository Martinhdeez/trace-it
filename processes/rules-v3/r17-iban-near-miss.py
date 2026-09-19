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


NEAR_MISS = 4  # a supplier's new account differs in 15-20 of 24 characters (docs)


def differences(one, other):
    """Single-character edits between two identifiers, for telling a misreading from
    a different account. Levenshtein; both strings are 24 characters at most."""
    if one == other:
        return 0
    previous = list(range(len(other) + 1))
    for i, a in enumerate(one, 1):
        current = [i]
        for j, b in enumerate(other, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def approved_account(instance, suppliers):
    """The one account the master approves for this invoice's supplier, or None when the
    master cannot answer: no NIF, no IBAN on the invoice, no rows, or rows that disagree
    (R02 and R04 already fire on those)."""
    nif = key(instance.get("issuer_nif"))
    if not nif or empty(instance.get("iban")):
        return None
    theirs = [r for r in suppliers if key(r.get("nif")) == nif]
    if not theirs:
        return None
    ids = {text(r.get("id")) for r in theirs}
    accounts = {iban(r.get("iban")) for r in theirs}
    if len(ids) > 1 or len(accounts) > 1:
        return None
    return accounts.pop()


def evaluate(instance, sources, others):
    """An IBAN a few characters away from the approved one is far more likely our
    misreading than the supplier's new account: a person looks instead of a refusal."""
    approved = approved_account(instance, rows(sources, "suppliers"))
    if approved is None:
        return passes()
    theirs = iban(instance.get("iban"))
    if theirs == approved:
        return passes()
    edits = differences(theirs, approved)
    if edits > NEAR_MISS:
        return passes()
    return fires(
        "IBAN " + theirs + " differs from the master's " + approved
        + " in " + str(edits) + " characters: read it again"
    )
