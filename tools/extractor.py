"""Read an invoice's symbols from the PDF text layer. No model involved.

Stand-in for symbol extraction over `features/ingestion`'s readings (ADR 0010). This
exists so the process can be run end to end today, and it is a useful baseline to hold that against: it reads all 471 text-layer invoices of the
challenge and none of the 29 scans.

Suppliers label things differently (`BASE IMPONIBLE....`, `Importe base:`, `Cuota IVA (21%)`,
`Total factura:`, `I.V.A. (21%)`), so rather than matching whole lines it finds a label and
takes the last number on that line. Anything it cannot read is left out on purpose: the
rules escalate an invoice whose symbols are missing, which is the honest answer.
"""

import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

# Zero-width characters are used in this corpus to break an IBAN into unmatchable pieces.
INVISIBLE = dict.fromkeys(map(ord, "\u200b‌‍﻿⁠­"), None)
MONTHS = {
    name: n
    for n, name in enumerate(
        [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ],
        1,
    )
}
AMOUNT = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}|-?\d+,\d{2}|-?\d+\.\d{2}|-?\d+")
CUSTOMER = "A58231074"  # Banco Miralmar: the customer, never the issuer
MIN_TEXT = 200  # below this there is no text layer worth reading: it is a scan


def text_of(path: Path) -> str:
    output = subprocess.run(
        ["pdftotext", "-q", "-layout", str(path), "-"], capture_output=True, text=True
    ).stdout
    return unicodedata.normalize("NFC", output.translate(INVISIBLE))


def is_scan(text: str) -> bool:
    return len(text.strip()) < MIN_TEXT


def plain(line: str) -> str:
    """Lowercase without accents, for comparing labels."""
    return "".join(
        c for c in unicodedata.normalize("NFD", line) if not unicodedata.combining(c)
    ).lower()


def last_amount(line: str) -> str | None:
    """What a labelled line states is the last number on it."""
    numbers = AMOUNT.findall(line)
    if not numbers:
        return None
    raw = numbers[-1]
    return raw.replace(".", "").replace(",", ".") if "," in raw else raw


def labelled(
    lines: list[str], labels: tuple[str, ...], exclude: tuple[str, ...] = ()
) -> str | None:
    for line in lines:
        flat = plain(line)
        if any(e in flat for e in exclude):
            continue
        if any(label in flat for label in labels):
            amount = last_amount(line)
            if amount is not None:
                return amount
    return None


def date_in(text: str) -> str | None:
    """Whatever the invoice printed, as `YYYY-MM-DD`. Impossible days are kept as they are:
    correcting them is not extraction's job, and a rule checks the date is real."""
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if m:
        day, month, year = m.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    m = re.search(r"(\d{1,2})\s+de\s+([a-zá-úA-ZÁ-Ú]+)\s+de\s+(\d{4})", text)
    if m:
        day, name, year = m.groups()
        month = MONTHS.get(plain(name))
        if month:
            return f"{year}-{month:02d}-{int(day):02d}"
    m = re.search(r"\d{4}-\d{2}-\d{2}", text)
    return m.group(0) if m else None


def symbols(file_id: str, text: str) -> dict[str, Any]:
    lines = [line for line in text.splitlines() if line.strip()]
    nifs = [n for n in re.findall(r"\b([A-Z]\d{8}|\d{8}[A-Z])\b", text) if n != CUSTOMER]
    iban = re.search(r"\b([A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){4,6})\b", text)
    order = re.search(r"\bPO-\d{4}-\d{4}\b", text)
    number = re.search(
        r"(?im)(?:n[ºo°]?\s*de\s*factura|ref\s*factura|factura\s*n[ºo°]?|factura)\s*:?\s*"
        r"([A-Z0-9][\w/\-]{2,})",
        text,
    )
    rate = re.search(r"(?i)i\.?\s*v\.?\s*a\.?[^%\n]{0,20}?(\d{1,2}(?:[.,]\d+)?)\s*%", text)
    date_line = next((line for line in lines if "fecha" in plain(line)), "")

    return {
        "file_id": file_id,
        "issuer_nif": nifs[0] if nifs else None,
        "issuer_name": lines[0].strip() if lines else None,
        "iban": iban.group(1) if iban else None,
        "invoice_number": number.group(1) if number else None,
        "date": date_in(date_line) or date_in(text),
        "purchase_order": order.group(0) if order else None,
        "base": labelled(lines, ("base imponible", "importe base", "base", "subtotal"), ("iva",)),
        "vat_rate": rate.group(1).replace(",", ".") if rate else None,
        "vat_amount": labelled(lines, ("cuota iva", "iva (", "i.v.a", "iva")),
        "total": labelled(
            lines,
            ("total factura", "importe total", "total a pagar", "total"),
            ("suma y sigue", "subtotal"),
        ),
        # Kept for the trace. No rule reads it, however the invoice phrases its instructions.
        "free_text": "\n".join(lines[-3:]),
    }
