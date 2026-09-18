"""Emergency and test fallback: build the `erp` rows from the challenge ERP's embedded data,
without calling its API.

The final delivery must use a snapshot downloaded from the API (the norm requires checking
against the ERP, and the ERP may change during the weekend); a fallback snapshot is labelled
`origin="erp:manual-fallback"` so it can never be mistaken for one. `alberto_erp.py` is read
as text, never imported, and never modified.

The rows are what the API would return after the connector's conversions, so a fallback
snapshot and a real one compare equal while the ERP holds batch 1.
"""

import base64
import csv
import io
import re
import zlib
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ORIGIN = "erp:manual-fallback"
DEFAULT_SCRIPT = (
    Path(__file__).resolve().parents[4] / ".context/500-sombras-de-alberto/alberto_erp.py"
)


def _embedded_csv(script: Path) -> str:
    text = script.read_text(encoding="utf-8")
    block = re.search(r"_DATOS_ERP = \((.*?)\n\)", text, re.S)
    if block is None:
        raise ValueError(f"{script}: no embedded data block")
    encoded = "".join(re.findall(r'"([^"]*)"', block.group(1)))
    return zlib.decompress(base64.b64decode(encoded)).decode("utf-8")


def _latin1(value: str) -> str:
    """What survives the bridge's ISO-8859-1 encoding."""
    return value.encode("iso-8859-1", errors="replace").decode("iso-8859-1").strip()


def fallback_rows(script: Path = DEFAULT_SCRIPT) -> list[dict[str, Any]]:
    rows = []
    for line in csv.DictReader(io.StringIO(_embedded_csv(script))):
        row: dict[str, Any] = {
            "entry_id": _latin1(line["asiento_id"]),
            "date": line["fecha_registro"].strip(),
            "supplier_id": _latin1(line["proveedor_id"]),
            "nif": _latin1(line["nif"]),
            "purchase_order": _latin1(line["pedido"]),
            "amount": line["importe_esperado"].strip(),
            "status": _latin1(line["estado"]),
        }
        invalid = []
        try:
            row["date"] = datetime.strptime(row["date"], "%Y-%m-%d").date().isoformat()
        except ValueError:
            invalid.append("date")
        try:
            row["amount"] = str(Decimal(f"{float(row['amount']):.2f}"))
        except (ValueError, InvalidOperation):
            invalid.append("amount")
        if invalid:
            row["_invalid"] = invalid
        rows.append(row)
    return sorted(rows, key=lambda r: r["entry_id"])
