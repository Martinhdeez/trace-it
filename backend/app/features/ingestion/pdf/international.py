"""Literal international invoice fields; no master-data repairs or inferred FX rates."""

import re

from app.common.normalization import fold, iban, identifier, invoice_date, money

RECIPIENT = re.compile(
    r"^(?:CLIENTE|CLIENT|DESTINATARIO|FACTURAR A|FATURAR A|BILL TO|"
    r"FACTURE A|RECHNUNGSEMPFANGER)\b"
)


def recipient_lines(lines):
    """Carry an explicit recipient role across its following fiscal/address lines."""
    excluded = set()
    recipient = False
    previous_page = None
    boundary = re.compile(
        r"^(?:EMISOR|EMITENTE|ISSUER|SUPPLIER|FOURNISSEUR|FORNITORE|LIEFERANT|"
        r"IBAN|FECHA|ISSUE DATE|DATA|DATE|PEDIDO|PURCHASE ORDER|FACTURA|INVOICE|"
        r"BASE|SUBTOTAL|TOTAL|IVA|VAT|TVA|MWST|GESAMT|SOUS-TOTAL|IMPONIBILE|VALOR BASE)\b"
    )
    for line in lines:
        text = fold(line.text)
        if line.page != previous_page:
            recipient = False
            previous_page = line.page
        if RECIPIENT.match(text):
            recipient = True
        elif boundary.match(text):
            recipient = False
        if recipient:
            excluded.add(line.id)
    return excluded


MONTHS = (
    "ENERO GENER JANEIRO JANVIER GENNAIO JANUAR JANUARY JAN",
    "FEBRERO FEBRER FEVEREIRO FEVRIER FEBBRAIO FEBRUAR FEBRUARY FEB",
    "MARZO MARC MARCO MARS MARZO MARZ MARCH MAR",
    "ABRIL AVRIL APRILE APRIL APR",
    "MAYO MAIG MAIO MAI MAGGIO MAY",
    "JUNIO JUNY JUNHO JUIN GIUGNO JUNI JUNE JUN",
    "JULIO JULIOL JULHO JUILLET LUGLIO JULI JULY JUL",
    "AGOSTO AGOST AOUT AUGUST AUG",
    "SEPTIEMBRE SETEMBRE SETEMBRO SEPTEMBRE SETTEMBRE SEPTEMBER SEP",
    "OCTUBRE OUTUBRO OCTOBRE OTTOBRE OKTOBER OCTOBER OCT",
    "NOVIEMBRE NOVEMBRE NOVEMBRO NOVEMBER NOV",
    "DICIEMBRE DESEMBRE DEZEMBRO DECEMBRE DICEMBRE DEZEMBER DECEMBER DEC",
)
DAY_WORDS = {
    "UNO": 1,
    "UN": 1,
    "ONE": 1,
    "FIRST": 1,
    "UM": 1,
    "EINS": 1,
    "DOS": 2,
    "DOIS": 2,
    "DEUX": 2,
    "DUE": 2,
    "TWO": 2,
    "SECOND": 2,
    "ZWEI": 2,
    "TRES": 3,
    "TROIS": 3,
    "TRE": 3,
    "THREE": 3,
    "THIRD": 3,
    "DREI": 3,
    "CUATRO": 4,
    "QUATRE": 4,
    "QUATRO": 4,
    "QUATTRO": 4,
    "FOUR": 4,
    "FOURTH": 4,
    "CINCO": 5,
    "CINC": 5,
    "CINQ": 5,
    "CINQUE": 5,
    "FIVE": 5,
    "FIFTH": 5,
    "SEIS": 6,
    "SIS": 6,
    "SIX": 6,
    "SEI": 6,
    "SIXTH": 6,
    "SIETE": 7,
    "SET": 7,
    "SETE": 7,
    "SEPT": 7,
    "SETTE": 7,
    "SEVEN": 7,
    "SEVENTH": 7,
    "SIEBTEN": 7,
    "SIEBEN": 7,
    "OCHO": 8,
    "VUIT": 8,
    "OITO": 8,
    "HUIT": 8,
    "OTTO": 8,
    "EIGHT": 8,
    "NUEVE": 9,
    "NOU": 9,
    "NOVE": 9,
    "NEUF": 9,
    "EIGHTH": 8,
    "NINE": 9,
    "DIEZ": 10,
    "DEU": 10,
    "DEZ": 10,
    "DIX": 10,
    "DIECI": 10,
    "TEN": 10,
    "ONCE": 11,
    "ONZE": 11,
    "UNDICI": 11,
    "ELEVEN": 11,
    "DOCE": 12,
    "DOTZE": 12,
    "DOUZE": 12,
    "DODICI": 12,
    "TWELVE": 12,
    "TRECE": 13,
    "TRETZE": 13,
    "TREIZE": 13,
    "TREDICI": 13,
    "THIRTEEN": 13,
    "CATORCE": 14,
    "CATORZE": 14,
    "QUATORZE": 14,
    "QUATTORDICI": 14,
    "QUINCE": 15,
    "QUINZE": 15,
    "QUINDICI": 15,
    "FIFTEEN": 15,
    "FUNFZEHNTEN": 15,
    "DIECISEIS": 16,
    "SETZE": 16,
    "DEZESSEIS": 16,
    "SEIZE": 16,
    "SEDICI": 16,
    "DIECISIETE": 17,
    "DISSET": 17,
    "DICIASSETTE": 17,
    "DIECIOCHO": 18,
    "DIVUIT": 18,
    "DICIOTTO": 18,
    "DIECINUEVE": 19,
    "DINOU": 19,
    "DICIANNOVE": 19,
    "VEINTE": 20,
    "VINT": 20,
    "VINGT": 20,
    "VENTI": 20,
    "TWENTY": 20,
    "TREINTA": 30,
    "TRENTA": 30,
    "TRINTA": 30,
    "TRENTE": 30,
    "THIRTY": 30,
}


def number_word(text):
    text = text.strip()
    if text.isdigit():
        return int(text)
    if text in DAY_WORDS:
        return DAY_WORDS[text]
    parts = [p for p in re.split(r"[ -]+", text) if p not in {"Y", "I", "E", "ET"}]
    if len(parts) == 2 and DAY_WORDS.get(parts[0]) in {20, 30}:
        last = DAY_WORDS.get(parts[1], 0)
        if 1 <= last <= 9:
            return DAY_WORDS[parts[0]] + last
    for prefix in ("VEINTI", "VENTI"):
        if text.startswith(prefix) and 1 <= DAY_WORDS.get(text[len(prefix) :], 0) <= 9:
            return 20 + DAY_WORDS[text[len(prefix) :]]
    raise ValueError("Unsupported date words")


def literal_date(raw):
    """Bounded date grammar; preserve impossible numeric dates in the existing parser."""
    try:
        return invoice_date(raw)
    except (ValueError, KeyError):
        pass
    text = fold(raw).replace(",", " ")
    for month, aliases in enumerate(MONTHS, 1):
        match = re.fullmatch(r"(.+?)\s+(?:DE\s+)?(" + "|".join(aliases.split()) + r")\s+(.+)", text)
        if not match:
            continue
        day_text = re.sub(r"^(?:THE|LE|AM)\s+", "", match[1]).strip()
        day_text = re.sub(r"\s+(?:OF|DE)$", "", day_text)
        day = number_word(day_text)
        year_text = re.sub(r"^(?:DE|DEL)\s+", "", match[3]).strip()
        year_text = re.sub(r"\s+", " ", year_text)
        if re.fullmatch(r"\d{4}", year_text):
            year = int(year_text)
        else:
            year_match = re.fullmatch(
                r"(?:DOS MIL |DOIS MIL |DEUX MILLE |TWO THOUSAND |DUEMILA)(.+)", year_text
            )
            if year_match:
                suffix = re.sub(r"^AND ", "", year_match[1])
                # Fused cardinal forms used by the supported date grammars.
                suffix = {"VEINTISEIS": "VEINTE SEIS", "VENTISEI": "VENTI SEI"}.get(suffix, suffix)
                year = 2000 + number_word(suffix)
            elif year_text.startswith("ZWEITAUSEND"):
                suffix = year_text[len("ZWEITAUSEND") :]
                german = {
                    "ZWANZIG": 20,
                    "EINUNDZWANZIG": 21,
                    "ZWEIUNDZWANZIG": 22,
                    "DREIUNDZWANZIG": 23,
                    "VIERUNDZWANZIG": 24,
                    "FUNFUNDZWANZIG": 25,
                    "SECHSUNDZWANZIG": 26,
                    "SIEBENUNDZWANZIG": 27,
                    "ACHTUNDZWANZIG": 28,
                    "NEUNUNDZWANZIG": 29,
                }
                if suffix not in german:
                    raise ValueError("Unsupported year words")
                year = 2000 + german[suffix]
            else:
                raise ValueError("Unsupported year words")
        if not 1 <= day <= 31:
            raise ValueError("Ambiguous day")
        return f"{year:04d}-{month:02d}-{day:02d}"
    raise ValueError("Unsupported date format")


def extra_fields(lines, candidates, add):
    """Add only unsupported literal fields, preserving legacy candidates byte for byte."""
    supported = {name for name, values in candidates.items() if values}
    recipients = recipient_lines(lines)

    def missing(name):
        # Collect all supplemental observations, including conflicting ones.
        return name not in supported

    for line in lines:
        text = fold(line.text)
        if RECIPIENT.match(text):
            continue

        tax = re.match(r"^(?:NIF|TAX ID|UST-ID|N[Oº°]?\s*TVA|P\.\s*IVA)\s*[:.]?\s*(\S+)\s*$", text)
        if tax and line.id not in recipients and missing("supplier_tax_id"):
            token = tax[1]
            if re.fullmatch(
                r"(?:[A-Z]{0,2}\d{8,14}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|[A-Z]\d{8})", token
            ):
                add("supplier_tax_id", token, line, identifier)
        bank = re.fullmatch(r"IBAN\s*:\s*([A-Z]{2}\d{2}[A-Z0-9 .-]+)", text)
        if bank and not bank[1].startswith("ES"):
            # Replace a partial numeric-only legacy match with the complete token.
            token = bank[1].strip()
            compact = identifier(token)
            if 15 <= len(compact) <= 34:
                candidates["payment_iban"][:] = [
                    c for c in candidates["payment_iban"] if c.evidence.locator != line.id
                ]
                add("payment_iban", token, line, iban)
        po = re.match(
            r"^(?:PURCHASE ORDER|COMANDA|ENCOMENDA|BON DE COMMANDE|ORDINE|BESTELLUNG)"
            r"\s*:\s*(PO-\d{4}-\d{4})\s*$",
            text,
        )
        if po and missing("purchase_order_ref"):
            add("purchase_order_ref", po[1], line)
        date = re.match(
            r"^(?:FECHA DE EMISION|ISSUE DATE|DATA D'EMISSIO|DATA DE EMISSAO|"
            r"DATE D'EMISSION|DATA DI EMISSIONE|AUSSTELLUNGSDATUM)\s*:\s*(.+)$",
            text,
        )
        if date and missing("issued_on"):
            try:
                literal_date(date[1])
            except (ValueError, KeyError):
                pass  # Unsupported words/blank handwriting are unresolved, not false dates.
            else:
                add("issued_on", date[1], line, literal_date)
        inv = re.match(
            r"^(?:INVOICE NO\.|FACTURA NUM\.|FATURA N\.[Oº°]?|FACTURE N[Oº°]?|"
            r"FATTURA N\.|RECHNUNG NR\.)\s*:\s*([A-Z0-9/-]+)$",
            text,
        )
        if inv and missing("invoice_number"):
            add("invoice_number", inv[1], line)
        match = re.match(
            r"^(BASE IMPOSABLE|VALOR BASE|SOUS-TOTAL|IMPONIBILE|ZWISCHENSUMME|"
            r"TOTALE|GESAMT|BASE IMPONIBLE|TOTAL|SUBTOTAL)\s*:\s*(.+)$",
            text,
        )
        vat = re.match(r"^(?:VAT|TVA|MWST\.|IVA)\s*\((\d{1,2})%\)\s*:\s*(.+)$", text)
        name, tail = None, None
        if match:
            name = "gross_amount" if match[1] in {"TOTALE", "GESAMT", "TOTAL"} else "net_amount"
            tail = match[2]
        if vat:
            if missing("vat_rate"):
                add("vat_rate", vat[1], line)
            name, tail = "vat_amount", vat[2]
        yen_document = any(re.search(r"\bJPY\b", fold(x.text)) for x in lines)
        if name and (missing(name) or (yen_document and all(c.error for c in candidates[name]))):
            currency = re.search(r"\b(EUR|USD|GBP|JPY|CHF|BRL|MXN)\b", tail)
            explicit = currency[1] if currency else None
            numeric = re.sub(
                r"\b(?:EUR|USD|GBP|JPY|CHF|BRL|MXN)\b|MX\$|R\$|FR\b|[€$£¥]", "", tail
            ).strip()
            # Integer grouping is unambiguous only with an explicit JPY document.
            yen = explicit == "JPY" or any("JPY" in fold(x.text) for x in lines)
            if yen and re.fullmatch(r"\d{1,3}(?:,\d{3})+", numeric):
                candidates[name][:] = [c for c in candidates[name] if c.evidence.locator != line.id]
                add(name, numeric, line, lambda v: money(v.replace(",", "")))
            elif re.fullmatch(r"[-+]?\d[\d., ]*", numeric):
                add(name, numeric, line, money)
        if missing("currency") and (
            match
            or vat
            or re.match(r"^(?:BILLING CURRENCY|RECHNUNGSWAHRUNG|MOEDA DE FATURACAO)\b", text)
        ):
            currency = re.search(r"\b(EUR|USD|GBP|JPY|CHF|BRL|MXN)\b", text)
            if currency:
                add("currency", currency[1], line)
