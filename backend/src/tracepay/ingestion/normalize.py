import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

INVISIBLE = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff\u2060\u00ad"), None)
MONTHS = dict(
    zip(
        "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(),
        range(1, 13),
    )
)


def clean_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value.translate(INVISIBLE))
    return re.sub(r"[^\S\n]+", " ", value).strip()


def fold(value: str) -> str:
    value = clean_text(value)
    return "".join(c for c in unicodedata.normalize("NFD", value) if not unicodedata.combining(c)).upper()


def identifier(value: str) -> str:
    return re.sub(r"[\s.-]", "", clean_text(value)).upper()


def iban(value: str) -> str:
    value = identifier(value)
    # Structural check only: synthetic accounts in the challenge do not have
    # reliable checksums. Never repair a digit or fill a truncated account.
    if value.startswith("ES") and not re.fullmatch(r"ES\d{22}", value):
        raise ValueError("Spanish IBAN must contain 24 characters")
    return value


def money(value: str) -> str:
    value = clean_text(value).replace("−", "-")
    value = re.sub(r"(?i)EUR|USD|GBP|[€$£]", "", value).strip()
    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1]
    value = value.replace(" ", "")
    if not re.fullmatch(r"[+-]?\d[\d.,]*", value):
        raise ValueError("Invalid amount")
    sign = "-" if value.startswith("-") else ""
    unsigned = value.lstrip("+-")
    if "," in unsigned and "." in unsigned:
        decimal_sep = "," if unsigned.rfind(",") > unsigned.rfind(".") else "."
        thousands = "." if decimal_sep == "," else ","
        left, right = unsigned.rsplit(decimal_sep, 1)
        if not re.fullmatch(rf"\d{{1,3}}(?:{re.escape(thousands)}\d{{3}})+", left) or len(right) != 2:
            raise ValueError("Invalid grouping")
        unsigned = left.replace(thousands, "") + "." + right
    elif "," in unsigned or "." in unsigned:
        sep = "," if "," in unsigned else "."
        parts = unsigned.split(sep)
        if len(parts) != 2 or len(parts[1]) not in (1, 2):
            raise ValueError("Ambiguous decimal/thousands separator")
        unsigned = ".".join(parts)
    try:
        return format(Decimal(sign + unsigned).quantize(Decimal("0.01")), "f")
    except InvalidOperation as exc:
        raise ValueError("Invalid amount") from exc


def excel_decimal(value) -> str:
    if isinstance(value, bool):
        raise ValueError("Boolean is not an amount")
    if isinstance(value, (int, float, Decimal)):
        number = Decimal(str(value))
        if not number.is_finite():
            raise ValueError("Non-finite number")
        return format(number.quantize(Decimal("0.01")), "f")
    return money(str(value))


def invoice_date(value: str) -> str:
    value = clean_text(value).lower()
    match = re.fullmatch(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", value)
    if match:
        return date(int(match[3]), MONTHS[match[2]], int(match[1])).isoformat()
    for pattern in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            pass
    raise ValueError("Invalid or unsupported date")
