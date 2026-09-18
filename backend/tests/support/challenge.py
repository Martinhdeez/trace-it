"""Read-only access to the challenge data in `.context/500-sombras-de-alberto`.

Sources come out as rows shaped the way `processes/invoice-payment.json` describes them, so
the rules see what a real source connector would give them. Nothing here imports the app.
"""

import ast
import csv
import io
import re
import unicodedata
import zlib
from base64 import b64decode
from functools import cache
from pathlib import Path
from typing import Any

import openpyxl

REPO = Path(__file__).resolve().parents[3]
CHALLENGE = REPO / ".context" / "500-sombras-de-alberto"
INVOICES = CHALLENGE / "facturas"
WORKBOOK = CHALLENGE / "FINAL_v7_DEFINITIVO_ahorasi.xlsx"
ERP_SERVER = CHALLENGE / "alberto_erp.py"

# Batch 1 arrived on Friday 18 Sep 2026. No invoice may be dated after it (norm rule 4).
CUT_OFF = "2026-09-18"


def available() -> bool:
    return INVOICES.is_dir() and WORKBOOK.is_file() and ERP_SERVER.is_file()


def file_id(path: Path) -> str:
    return unicodedata.normalize("NFC", path.name)


def invoice_paths() -> list[Path]:
    return sorted(INVOICES.glob("*.pdf"), key=file_id)


def _sheet(name: str) -> list[dict[str, Any]]:
    workbook = openpyxl.load_workbook(WORKBOOK, read_only=True)
    header, *rows = workbook[name].iter_rows(values_only=True)
    return [dict(zip(header, row, strict=True)) for row in rows if any(row)]


def erp_entries() -> list[dict[str, str]]:
    """The ERP's own export, embedded (zlib + base64 CSV) in `alberto_erp.py`.

    Read as text, never imported: importing it would write `__pycache__` into the submodule.
    It is the same data the bridge serves over HTTP, before its legacy formatting.
    """
    source = ERP_SERVER.read_text(encoding="utf-8")
    literal = re.search(r"^_DATOS_ERP = (\(.*?\n\))", source, re.S | re.M)
    if literal is None:
        raise RuntimeError("No embedded ERP data block in alberto_erp.py")
    raw = zlib.decompress(b64decode(ast.literal_eval(literal.group(1)))).decode("utf-8")
    return list(csv.DictReader(io.StringIO(raw)))


@cache
def sources() -> dict[str, list[dict[str, Any]]]:
    """The four sources of the invoice process, with the column names its rules use."""
    return {
        "suppliers": [
            {"id": r["ID"], "company_name": r["Razon Social"], "nif": r["NIF"], "iban": r["IBAN"]}
            for r in _sheet("Proveedores")
        ],
        "orders": [
            {
                "purchase_order": r["Pedido"],
                "supplier_id": r["ProveedorID"],
                "nif": r["NIF"],
                "total_amount": r["Importe_Total"],
                "status": r["Estado"],
                "order_date": r["Fecha_Pedido"],
            }
            for r in _sheet("Pedidos_2026")
        ],
        "erp": [
            {
                "entry_id": r["asiento_id"],
                "date": r["fecha_registro"],
                "supplier_id": r["proveedor_id"],
                "nif": r["nif"],
                "purchase_order": r["pedido"],
                "amount": r["importe_esperado"],
                "status": r["estado"],
            }
            for r in erp_entries()
        ],
        "parameters": [{"cut_off_date": CUT_OFF}],
    }
