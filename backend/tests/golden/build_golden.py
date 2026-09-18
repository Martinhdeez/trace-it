"""Build the golden outcomes of batch 1 from the challenge files alone.

    cd backend && uv run python -m tests.golden.build_golden

Deterministic and idempotent: the same challenge files always give byte-identical output.
Needs `pdftotext` (poppler) on PATH. Reads only `.context/500-sombras-de-alberto`.

This is an independent reference: its own regex parser and its own reading of
Norma_Pagos_v3. It shares nothing with the app or with the hand-written rule code, so the
engine golden test compares two separate implementations of the same norm. See README.md.
"""

import calendar
import json
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from tests.support import challenge

HERE = Path(__file__).parent
EXPECTED = HERE / "batch1_expected.jsonl"
SYMBOLS = HERE / "batch1_symbols.jsonl"

CLIENT_NIF = "A58231074"  # Banco Miralmar, the customer: never the issuer
INVISIBLE = re.compile("[\u00ad\u200b-\u200f\u2060-\u2064\ufeff]")
MONTHS = {
    m: i
    for i, m in enumerate(
        ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"],
        1,
    )
}  # fmt: skip
# Invoice text addressed at whoever processes it. Recorded in `why`, never obeyed.
INJECTION = re.compile(
    r"(marcar(?:se)? como|registrar como|debe marcarse|no bloquear|aprobad[oa] por|"
    r"pagar el total impreso|autorizad[oa]|ignore|approved)",
    re.I,
)

AMOUNT = r"(?:EUR\s*)?(-?\d[\d.,]*[.,]\d{2})(?!\d)"
LABELS = {
    "base": r"(?<![A-Za-z])(?:BASE IMPONIBLE|Importe base|Subtotal|Base)\b[ .:€]*" + AMOUNT,
    "vat": r"(?:I\.V\.A\.|IVA|Cuota IVA)\s*\((\d+(?:[.,]\d+)?)\s*%\)[ .:€]*" + AMOUNT,
    "total": r"(?<![A-Za-z])(?:TOTAL A PAGAR|IMPORTE TOTAL|Total factura|TOTAL)\b[ .:€]*" + AMOUNT,
}
NUMBER_LABELS = [
    r"FACTURA SIMPLIFICADA N[ºo°]\s*:?\s*(\S+)",
    r"FACTURA N[ºo°]\s*:\s*(\S+)",
    r"N[ºo°] de factura\s*:\s*(\S+)",
    r"REF FACTURA\s*:\s*(\S+)",
    r"Invoice\s*#\s*(\S+)",
    r"Factura\s*:\s*(\S+)",
]
DATE_LABEL = r"(?:Fecha|FECHA)(?: de emisi[oó]n| factura)?\s*:\s*"


def text_of(pdf: Path) -> str:
    out = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True
    ).stdout
    return out


def amount(raw: str) -> Decimal:
    raw = raw.replace(" ", "")
    if re.search(r",\d{2}$", raw):
        raw = raw.replace(".", "").replace(",", ".")
    else:
        raw = raw.replace(",", "")
    return Decimal(raw)


def as_json_number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral() else float(value)


def printed_date(text: str) -> str | None:
    """YYYY-MM-DD with the printed numbers, never corrected (31/02 stays 02-31)."""
    m = re.search(DATE_LABEL + r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}"
    m = re.search(DATE_LABEL + r"(\d{1,2}) de (\w+) de (\d{4})", text, re.I)
    if m and m[2].lower() in MONTHS:
        return f"{int(m[3]):04d}-{MONTHS[m[2].lower()]:02d}-{int(m[1]):02d}"
    return None


def last(pattern: str, text: str) -> re.Match[str] | None:
    """The last match: on a multi-page invoice the totals are on the last page."""
    matches = list(re.finditer(pattern, text, re.I | re.M))
    return matches[-1] if matches else None


def parse(fid: str, text: str) -> dict[str, Any]:
    """Symbols with the names of `procesos/pago-facturas.json`. Missing ones are None."""
    nifs = [n for n in re.findall(r"\b([A-Z]\d{7}[A-Z0-9]|\d{8}[A-Z])\b", text) if n != CLIENT_NIF]
    iban = re.search(r"\bES\d{2}(?: ?\d{4}){5}\b", text)
    order = re.search(r"\bPO-\d{4}-\d{3,5}\b", text)
    number = next((m[1] for p in NUMBER_LABELS if (m := re.search(p, text))), None)
    base, vat, total = (last(LABELS[k], text) for k in ("base", "vat", "total"))
    return {
        "file_id": fid,
        "nif_emisor": nifs[0] if nifs else None,
        "iban": iban.group() if iban else None,
        "numero_factura": number,
        "fecha": printed_date(text),
        "pedido": order.group() if order else None,
        "base": as_json_number(amount(base[1])) if base else None,
        "tipo_iva": as_json_number(amount(vat[1] + ",00")) if vat else None,
        "cuota_iva": as_json_number(amount(vat[2])) if vat else None,
        "total": as_json_number(amount(total[1])) if total else None,
    }


# --- Independent reading of Norma_Pagos_v3 -----------------------------------------------

# Each finding and the outcome it leads to. ESCALAR > NO_PAGAR > PAGAR.
OUTCOME = {
    "MISSING_SYMBOL": "ESCALAR",
    "NIF_NOT_IN_MASTER": "NO_PAGAR",
    "IBAN_MISMATCH": "NO_PAGAR",
    "MASTER_CONFLICT": "ESCALAR",
    "PO_NOT_FOUND": "NO_PAGAR",
    "PO_OTHER_VENDOR": "NO_PAGAR",
    "AMOUNT_NE_PO": "NO_PAGAR",
    "VAT_MISCALCULATED": "NO_PAGAR",
    "VAT_RATE_NOT_21": "ESCALAR",
    "TOTAL_NE_BASE_PLUS_VAT": "NO_PAGAR",
    "IMPOSSIBLE_DATE": "NO_PAGAR",
    "FUTURE_DATE": "NO_PAGAR",
    "PO_NOT_IN_ERP": "NO_PAGAR",
    "ERP_NE_PO": "NO_PAGAR",
    "ERP_PAID": "NO_PAGAR",
    "DUPLICATE_PO": "ESCALAR",
}
RANK = {"PAGAR": 1, "NO_PAGAR": 2, "ESCALAR": 3}

# The trap table of `.artifacts/specs/2026-09-18-analisis-caja-v3.md`, found by a different
# quick scan. Every listed file must show the finding here too, or the build fails.
TRAPS = {
    "IBAN_MISMATCH": [
        "FA-7311", "FA-4290", "FA-5633", "FA-9104", "FA-5044_mensajería2", "F26-8812",
        "2026-07-08_P010", "F26-9007",
    ],
    "NIF_NOT_IN_MASTER": ["FA-2508", "factura_4485", "factura_7265"],
    "PO_OTHER_VENDOR": ["2026-07-08_P010", "F26-9007"],
    "VAT_MISCALCULATED": ["F26-5240", "F26-6702", "F26-6964", "F26-8801", "F26-9012", "FA-5590"],
    "AMOUNT_NE_PO": ["factura_1936", "factura_2018", "factura_3184", "factura_8801", "FA-5077"],
    "TOTAL_NE_BASE_PLUS_VAT": ["2026-0811-B", "2026-14500-C"],
    "IMPOSSIBLE_DATE": ["2026-03-19_P008", "FA-1123", "FA-2967"],
    "ERP_PAID": [
        "2026-03-28_P002", "2026-04-08_P007", "2026-05-28_P003", "2026-06-04_P006",
        "2026-17547", "FA-1016", "FA-2116", "factura_4619", "factura_5911",
    ],
    "DUPLICATE_PO": ["factura_41082", "2026-0233-A"],
    "INVISIBLE_CHARS": ["FA-4488", "F26-3011"],
    "INJECTED_TEXT": ["factura_1936"],
}  # fmt: skip
# Findings whose outcome is a team decision, not the norm's wording: confidence "medium".
POLICY = {
    "DUPLICATE_PO", "VAT_RATE_NOT_21", "NIF_NOT_IN_MASTER", "IBAN_MISMATCH", "MISSING_SYMBOL",
}  # fmt: skip


def key(value: Any) -> str:
    return re.sub(r"[\s.\-]", "", str(value or "")).upper()


def cents(value: Any) -> int:
    return int((Decimal(str(value)) * 100).quantize(Decimal(1), ROUND_HALF_UP))


def near(a: Any, b: Any) -> bool:
    return abs(cents(a) - cents(b)) <= 1


def real_date(printed: str) -> bool:
    y, m, d = (int(p) for p in printed.split("-"))
    return 1 <= m <= 12 and 1 <= d <= calendar.monthrange(y, m)[1]


@dataclass
class Reference:
    file_id: str
    symbols: dict[str, Any] | None
    findings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def findings(s: dict[str, Any], src: dict[str, list[dict[str, Any]]]) -> list[str]:
    required = ["nif_emisor", "iban", "pedido", "fecha", "base", "tipo_iva", "cuota_iva", "total"]
    out = [f"MISSING_SYMBOL: {', '.join(k for k in required if s[k] is None)}"]
    if all(s[k] is not None for k in required):
        out = []
    nif, po = key(s["nif_emisor"]), key(s["pedido"])
    master = [r for r in src["proveedores"] if key(r["nif"]) == nif]
    variants = {(r["id"], key(r["iban"])) for r in master}
    order = next((r for r in src["pedidos"] if key(r["pedido"]) == po), None)
    erp = next((r for r in src["erp"] if key(r["pedido"]) == po), None)
    if nif and not master:
        out.append(f"NIF_NOT_IN_MASTER: {nif}")
    if len(variants) > 1:
        out.append(f"MASTER_CONFLICT: {sorted(variants)}")
    elif variants and s["iban"] and key(s["iban"]) != next(iter(variants))[1]:
        out.append(f"IBAN_MISMATCH: {key(s['iban'])} vs master {next(iter(variants))[1]}")
    if po and order is None:
        out.append(f"PO_NOT_FOUND: {s['pedido']}")
    if order is not None:
        if order["nif"]:
            other = key(order["nif"]) != nif
        else:
            other = bool(master) and order["proveedor_id"] != master[0]["id"]
        if nif and other:
            out.append(f"PO_OTHER_VENDOR: {s['pedido']} belongs to {order['proveedor_id']}")
        if s["total"] is not None and not near(s["total"], order["importe_total"]):
            out.append(f"AMOUNT_NE_PO: {s['total']} vs {order['importe_total']}")
        if erp is None:
            out.append(f"PO_NOT_IN_ERP: {s['pedido']}")
    if None not in (s["base"], s["tipo_iva"], s["cuota_iva"]):
        due = (Decimal(str(s["base"])) * Decimal(str(s["tipo_iva"])) / 100).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )
        if not near(s["cuota_iva"], due):
            out.append(f"VAT_MISCALCULATED: {s['cuota_iva']} vs {due} at {s['tipo_iva']}%")
    if s["tipo_iva"] is not None and cents(s["tipo_iva"]) != 2100:
        out.append(f"VAT_RATE_NOT_21: {s['tipo_iva']}%")
    if None not in (s["base"], s["cuota_iva"], s["total"]):
        added = Decimal(str(s["base"])) + Decimal(str(s["cuota_iva"]))
        if not near(s["total"], added):
            out.append(f"TOTAL_NE_BASE_PLUS_VAT: {s['total']} vs {added}")
    if s["fecha"] is not None:
        if not real_date(s["fecha"]):
            out.append(f"IMPOSSIBLE_DATE: {s['fecha']}")
        elif s["fecha"] > src["parametros"][0]["fecha_corte"]:
            out.append(f"FUTURE_DATE: {s['fecha']}")
    if order is not None and erp is not None:
        differ = [
            name
            for name, same in [
                ("importe", near(erp["importe"], order["importe_total"])),
                ("proveedor_id", erp["proveedor_id"] == order["proveedor_id"]),
                ("nif", not (erp["nif"] and order["nif"]) or key(erp["nif"]) == key(order["nif"])),
            ]
            if not same
        ]
        if differ:
            out.append(f"ERP_NE_PO: {', '.join(differ)}")
    if erp is not None and erp["estado"].strip().upper() != "PENDIENTE":
        out.append(f"ERP_PAID: {erp['asiento_id']} is {erp['estado']}")
    return out


def build() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    src = challenge.sources()
    refs: list[Reference] = []
    for pdf in challenge.invoice_paths():
        fid = challenge.file_id(pdf)
        raw = text_of(pdf)
        if len(raw.strip()) < 50:
            refs.append(Reference(fid, None, notes=["image-only scan: needs OCR or vision"]))
            continue
        text = INVISIBLE.sub("", raw)
        ref = Reference(fid, parse(fid, text))
        if text != raw:
            ref.notes.append("INVISIBLE_CHARS stripped before parsing")
        if INJECTION.search(text):
            ref.notes.append("INJECTED_TEXT ignored: the invoice addresses its processor")
        ref.findings = findings(ref.symbols, src)
        refs.append(ref)

    by_order = defaultdict(list)
    for ref in refs:
        if ref.symbols and ref.symbols["pedido"]:
            by_order[key(ref.symbols["pedido"])].append(ref.file_id)
    for ref in refs:
        if ref.symbols and len(twins := by_order[key(ref.symbols["pedido"])]) > 1:
            others = ", ".join(t for t in twins if t != ref.file_id)
            ref.findings.append(f"DUPLICATE_PO: {ref.symbols['pedido']} also in {others}")

    check_traps(refs)

    expected, symbols = [], []
    for ref in refs:
        if ref.symbols is None:
            row = {"file_id": ref.file_id, "expected": None, "confidence": "none"}
            expected.append({**row, "why": "; ".join(ref.notes)})
            continue
        tags = {f.split(":")[0] for f in ref.findings}
        outcome = max((OUTCOME[t] for t in tags), key=RANK.__getitem__, default="PAGAR")
        doubtful = tags & POLICY or any(n.startswith("INJECTED_TEXT") for n in ref.notes)
        confidence = "medium" if doubtful else "high"
        why = "; ".join(ref.findings + ref.notes) or "clean: no finding"
        expected.append(
            {"file_id": ref.file_id, "expected": outcome, "confidence": confidence, "why": why}
        )
        symbols.append(ref.symbols)
    return expected, symbols


def check_traps(refs: list[Reference]) -> None:
    missing = []
    for tag, stems in TRAPS.items():
        for stem in stems:
            hits = [r for r in refs if r.file_id.startswith(stem)]
            said = [x for r in hits for x in r.findings + r.notes if x.startswith(tag)]
            if len(hits) != 1 or not said:
                missing.append(f"{tag}: {stem} ({len(hits)} files)")
    if missing:
        raise SystemExit("Trap table not reproduced:\n  " + "\n  ".join(missing))


def dump(rows: list[dict[str, Any]], path: Path) -> None:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=False) + "\n" for r in rows),
        encoding="utf-8",
    )


def main() -> None:
    expected, symbols = build()
    dump(expected, EXPECTED)
    dump(symbols, SYMBOLS)
    counts = Counter(str(r["expected"]) for r in expected)
    print(f"{len(expected)} files -> {dict(sorted(counts.items()))}")


if __name__ == "__main__":
    main()
