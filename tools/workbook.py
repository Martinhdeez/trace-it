"""Read the challenge workbook into source rows.

Stand-in for a spreadsheet connector; the ERP already has one in `features/sources`. Two
things matter here and will matter just as much in the real loader:

- Headers are mapped to the names the rules use: `ProveedorID` -> `supplier_id`,
  `Importe_Total` -> `total_amount`, `Razon Social` -> `company_name`. Every rule in the
  pack is written against those names, so the whole norm breaks at once if this is wrong.
- Values are made JSON-safe. Sources are stored as JSONB and the sandbox serialises each
  case, so an `openpyxl` date or a Decimal would blow up at the first rule.
"""

import datetime
import re
import unicodedata
from decimal import Decimal
from typing import Any

import openpyxl

SHEETS = {"suppliers": "Proveedores", "orders": "Pedidos_2026"}
# The workbook is in Spanish; the rules are written against these names.
COLUMNS = {
    "razon_social": "company_name",
    "proveedor_id": "supplier_id",
    "importe_total": "total_amount",
    "estado": "status",
    "fecha_pedido": "order_date",
    "pedido": "purchase_order",
    "ciudad": "city",
    "condiciones": "terms",
}


def column(name: Any) -> str:
    """'ProveedorID' -> 'proveedor_id'. 'Razon Social' -> 'razon_social'."""
    text = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text.strip())
    spanish = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return COLUMNS.get(spanish, spanish)


def jsonable(value: Any) -> Any:
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def sheet(book: openpyxl.Workbook, name: str) -> list[dict[str, Any]]:
    rows = list(book[name].iter_rows(values_only=True))
    keys = [column(c) for c in rows[0]]
    return [
        {k: jsonable(v) for k, v in zip(keys, row, strict=False) if k}
        for row in rows[1:]
        if not all(v is None for v in row)
    ]


def sources(path: str, cutoff: str) -> dict[str, list[dict[str, Any]]]:
    """The workbook's sources, plus `parameters`, which is where a rule reads the cut-off
    date from: a rule never reads the clock."""
    book = openpyxl.load_workbook(path, data_only=True)
    loaded = {name: sheet(book, tab) for name, tab in SHEETS.items()}
    return {**loaded, "parameters": [{"cut_off_date": cutoff}]}
