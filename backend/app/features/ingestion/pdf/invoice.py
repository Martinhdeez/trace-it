import re
from decimal import ROUND_HALF_UP, Decimal

from app.common.extraction import Candidate, Evidence, ExtractedField, TextLine
from app.common.normalization import fold, iban, identifier, invoice_date, money
from app.features.ingestion.schemas import INVOICE_FIELDS

from .uncertainty import preserve_unreadable

AMOUNT = r"(?<![\w.,])[-+]?\d(?:[\d.,\u00a0 ]*\d)?(?![\w.,])"
DATE = r"\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s+de\s+\w+\s+de\s+\d{4}"
VAT = r"I\s*\.?\s*V\s*\.?\s*A\s*\.?"
CURRENCY_CODE = (
    r"(?<![A-Z])(?:EUR|USD|GBP|CAD|MXN|ARS|CLP|COP|PEN|UYU|JPY|"
    r"CHF|CNY|AUD|NZD|BRL|INR|AED|SEK|NOK|DKK|PLN|CZK|ZAR)(?![A-Z])"
)
# Product convention requested by the team; explicit document currency takes precedence.
CURRENCY_SYMBOLS = {"€": "EUR", "$": "USD", "£": "GBP"}


def aggregate(candidates: list[Candidate], min_confidence: float = 0.90) -> ExtractedField:
    if not candidates:
        return ExtractedField()
    valid = [c for c in candidates if c.error is None]
    values = {c.value for c in valid}
    if len(values) > 1 or (valid and len(valid) != len(candidates)):
        return ExtractedField(status="AMBIGUOUS", candidates=candidates)
    if not valid:
        return ExtractedField(status="INVALID", candidates=candidates)
    reliable = any(
        c.evidence.method == "native"
        or (c.evidence.confidence is not None and c.evidence.confidence >= min_confidence)
        for c in valid
    )
    if all(c.evidence.method == "vlm" for c in valid):
        status = "UNVERIFIED"
    else:
        status = "OBSERVED" if reliable else "LOW_CONFIDENCE"
    return ExtractedField(value=valid[0].value, status=status, candidates=candidates)


def parse_invoice(lines: list[TextLine], min_confidence: float = 0.90):
    expanded = []
    for line in lines:
        if line.method == "ocr":
            # Tolerate corrupted labels, never substitute characters inside financial values.
            text = re.sub(r"(?<!\w)(?:1I?BAN|\|BAN)\b", "IBAN", line.text, flags=re.I)
            text = re.sub(r"(?<!\w)(?:1VA|\|VA)(?=\W|\d)", "IVA", text, flags=re.I)
            text = re.sub(r"^Pedid(?:a|α)?(?=\W|$)", "Pedido", text, flags=re.I)
            line = line.model_copy(update={"text": text})
        if re.match(rf"^(?:BASE|IMPORTE BASE|SUBTOTAL|{VAT}|CUOTA IVA)(?=\W|\d)", fold(line.text)):
            parts = re.split(
                rf"\s*(?=(?<![A-Z])(?:{VAT}\s*\(?\s*\d|TOTAL(?=\W|\d)))",
                line.text,
                flags=re.IGNORECASE,
            )
            expanded.extend(line.model_copy(update={"text": part}) for part in parts)
        else:
            expanded.append(line)
    lines = expanded
    candidates = {name: [] for name in (*INVOICE_FIELDS, "invoice_number")}
    warnings = []
    symbol_observations = []

    def add(name, raw, line, normalizer=lambda v: v):
        try:
            value, error = normalizer(raw), None
        except (ValueError, KeyError):
            value, error = None, "Invalid or ambiguous format"
            # OCR can confuse decimal and grouping punctuation. Keep this as a
            # proposal: a plausible correction is not a verified transcription.
            if normalizer is money and line.method in {"ocr", "vlm"}:
                compact = raw.replace(" ", "")
                match = re.fullmatch(r"([+-]?\d{1,3})([.,])(\d{3}(?:\2\d{3})*)\2(\d{2})", compact)
                if match:
                    value = money(match[1] + match[3].replace(match[2], "") + "." + match[4])
                    error = None
                    warnings.append(
                        {"code": "OCR_SEPARATOR_PROPOSAL", "field": name, "locator": line.id}
                    )
        candidates[name].append(
            Candidate(
                value=value,
                raw=raw,
                error=error,
                evidence=Evidence(
                    locator=line.id,
                    text=line.raw,
                    page=line.page,
                    bbox=line.bbox,
                    method=line.method,
                    confidence=line.confidence,
                    preprocessing=line.preprocessing,
                ),
            )
        )

    for i, line in enumerate(lines):
        text, upper = line.text, fold(line.text)
        if re.search(
            (
                r"IGNORAR|AGENTE|REGISTR(?:A|AR).*PAGAR|NO.*RECALCUL|SIN "
                r"ESCALADO|NO PROCEDE.*ERP|NO BLOQUEAR.*CONCILI"
            ),
            upper,
        ):
            warnings.append(
                {
                    "code": "UNTRUSTED_INSTRUCTION",
                    "locator": line.id,
                    "message": "Document instruction retained as evidence, not executed",
                }
            )
        # Only extract anchored fiscal/header labels. Ignore accounts in narrative text.
        if not re.match(r"^(?:CLIENTE|DESTINATARIO|FACTURAR A|BILL TO)\b", upper):
            for match in re.finditer(
                r"\bNIF\s*[:.]?\s*([A-Z][\s.-]*\d(?:[\s.-]*\d){7})(?!\d)", upper
            ):
                add("supplier_tax_id", match[1], line, identifier)
        bank = re.search(
            r"\bIBAN\s*\)?\s*[:\-]?\s*([A-Z]{2}[ .-]*\d[ .-]*\d(?:[ .-]*\d){10,30})", upper
        )
        if bank and (upper.startswith(("IBAN", "CUENTA", "NIF")) or "EMISOR:" in upper):
            add("payment_iban", bank[1], line, iban)
        po = re.search(
            (
                r"(?:\bPEDIDO(?:\s+(?:ASOCIADO|CLIENTE))?|"
                r"\bPO)\s*[:#]?\s*(PO[- ]\d{4}[- ]\d(?:\s*\d){3})(?!\d)"
            ),
            upper,
        )
        if po:

            def normalize_po(value):
                digits = "".join(re.findall(r"\d", value))
                return f"PO-{digits[:4]}-{digits[4:]}"

            add("purchase_order_ref", po[1], line, normalize_po)
        header = re.sub(r"(?<=[0-9])(?=FECHA\s*[:.]?\s*\d)", " ", upper)
        if re.match(r"^(?:FECHA|FACTURA[: ]|PEDIDO[: ])", header):
            date_label = re.search(
                r"(?<![A-Z])FECHA(?:\s+(?:DE EMISION|FACTURA))?\s*[:.]?\s*(.+)", header
            )
            if date_label and (match := re.search(DATE, date_label[1], re.I)):
                add("issued_on", match[0], line, invoice_date)
        inv = re.match(
            (
                r"^(?:FACTURA(?: SIMPLIFICADA)?(?: N[Oº°])?|N[Oº°] DE FACTURA|"
                r"REF FACTURA|INVOICE)\s*[:#]?\s*([A-Z0-9]+[-/][A-Z0-9/-]+)"
            ),
            header,
        )
        if inv:
            add("invoice_number", inv[1], line)

        name = None
        if re.match(r"^(?:BASE(?: IMPONIBLE)?|IMPORTE BASE|SUBTOTAL)(?=\W|\d)", upper):
            name = "net_amount"
        elif re.match(r"^(?:TOTAL(?: A PAGAR| FACTURA)?|IMPORTE TOTAL)(?=\W|\d)", upper):
            name = "gross_amount"
        vat_match = re.match(
            rf"^(?:CUOTA\s+)?{VAT}\s*\(?\s*(\d{{1,2}}(?:[.,]\d+)?)\s*%\s*\)?", upper
        )
        if vat_match:
            add("vat_rate", vat_match[1], line, lambda v: format(Decimal(v.replace(",", ".")), "f"))
            name = "vat_amount"
        if name:
            tail = (
                text[vat_match.end() :]
                if vat_match
                else re.sub(
                    (
                        r"^(?:BASE IMPONIBLE|IMPORTE BASE|SUBTOTAL|BASE|TOTAL A PAGAR|"
                        r"TOTAL FACTURA|IMPORTE TOTAL|TOTAL)"
                    ),
                    "",
                    upper,
                )
            )
            # Strip decorative dot leaders before parsing; don't pick numbers in explanatory prose.
            tail = re.sub(r"^[\s.:]+", "", tail)
            tail = re.sub(CURRENCY_CODE + r"|EUROS?\b|[€$£]", " ", tail, flags=re.IGNORECASE)
            numeric = re.findall(AMOUNT, tail)
            if len(numeric) == 1 and not re.search(r"[A-Z]", tail, re.I):
                add(name, numeric[0].strip(), line, money)
            elif not numeric and i + 1 < len(lines) and lines[i + 1].page == line.page:
                following = lines[i + 1]
                if re.fullmatch(r"\s*(?:EUR\s*)?[-+]?\d[\d., ]*(?:\s*€)?\s*", following.text, re.I):
                    add(name, following.text, following, money)
        if (
            name
            or re.fullmatch(
                rf"(?:[-+]?\d[\d., ]*\s*(?:{CURRENCY_CODE}|[€$£])|"
                rf"(?:{CURRENCY_CODE}|[€$£])\s*[-+]?\d[\d., ]*)",
                upper,
            )
            or re.match(r"^(?:MONEDA|CURRENCY|DIVISA|IMPORTES? EN)\b", upper)
            or re.fullmatch(CURRENCY_CODE, upper)
            or re.fullmatch(r"EUROS?|[€$£]", upper)
        ):
            for match in re.finditer(CURRENCY_CODE, upper):
                add("currency", match[0], line)
            for match in re.finditer(r"\bEUROS?\b", upper):
                add("currency", match[0], line, lambda _: "EUR")
            for symbol, iso in CURRENCY_SYMBOLS.items():
                if symbol in text:
                    symbol_observations.append((symbol, iso, line))

    if not candidates["currency"]:
        for symbol, iso, line in symbol_observations:
            add("currency", symbol, line, lambda _, value=iso: value)

    fields = {key: aggregate(value, min_confidence) for key, value in candidates.items()}
    for warning in warnings:
        if (
            warning["code"] == "OCR_SEPARATOR_PROPOSAL"
            and fields[warning["field"]].status == "OBSERVED"
        ):
            fields[warning["field"]].status = "UNVERIFIED"
    consistency = arithmetic_checks(fields)
    warnings.extend(consistency)
    if consistency:
        for key in ("net_amount", "vat_rate", "vat_amount", "gross_amount"):
            field = fields[key]
            if field.status == "OBSERVED" and all(
                c.evidence.method == "ocr" for c in field.candidates
            ):
                field.status = "UNVERIFIED"
                warnings.append({"code": "OCR_ARITHMETIC_UNVERIFIED", "field": key})
    warnings.extend(preserve_unreadable(fields, lines))
    return fields, warnings


def unresolved(fields):
    # Preserve clearly printed invalid dates/amounts; do not hallucinate a correction.
    return [
        key
        for key in INVOICE_FIELDS
        if fields[key].status in {"MISSING", "AMBIGUOUS", "LOW_CONFIDENCE", "UNVERIFIED"}
    ]


def arithmetic_checks(fields):
    warnings = []
    keys = ("net_amount", "vat_rate", "vat_amount", "gross_amount")
    available = {
        key: Decimal(fields[key].value)
        for key in keys
        if fields[key].status == "OBSERVED" and fields[key].value is not None
    }
    if all(key in available for key in ("net_amount", "vat_rate", "vat_amount")):
        base, rate, vat = (available[key] for key in ("net_amount", "vat_rate", "vat_amount"))
        expected = (base * rate / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if abs(expected - vat) > Decimal("0.01"):
            warnings.append(
                {"code": "VAT_MISMATCH", "expected": str(expected), "observed": str(vat)}
            )
    if all(key in available for key in ("net_amount", "vat_amount", "gross_amount")):
        base, vat, total = (available[key] for key in ("net_amount", "vat_amount", "gross_amount"))
        if abs(base + vat - total) > Decimal("0.01"):
            warnings.append(
                {"code": "TOTAL_MISMATCH", "expected": str(base + vat), "observed": str(total)}
            )
    return warnings
