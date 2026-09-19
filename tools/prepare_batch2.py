"""Prepare cumulative reference tables; no network or application database writes."""

import argparse
import csv
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl

SUPPLIERS = {
    "ID": "ID",
    "Razon Social": "Razon Social",
    "NIF": "NIF",
    "IBAN": "IBAN",
    "Ciudad": "Ciudad",
    "Condiciones": "Condiciones",
}
ORDERS = {
    "pedido": "Pedido",
    "proveedor_id": "ProveedorID",
    "nif": "NIF",
    "importe_total": "Importe_Total",
    "estado": "Estado",
    "fecha_pedido": "Fecha_Pedido",
}


def read_csv(path, columns):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or ()) != set(columns):
            raise ValueError(f"Unexpected columns in {path}")
        rows = list(reader)
    for row in rows:
        if any(not isinstance(v, str) or not v.strip() for v in row.values()):
            raise ValueError(f"Incomplete row in {path}")
        if any(v.lstrip().startswith(("=", "+", "@")) for v in row.values()):
            raise ValueError("Spreadsheet formulas are not reference values")
    return rows


def prepare(book, suppliers, orders, output):
    book, output = Path(book), Path(output)
    if output.resolve() == book.resolve() or output.exists():
        raise ValueError("Output must be a new file; preserve the original workbook")
    workbook = openpyxl.load_workbook(book)
    counts = {}
    for sheet, path, mapping, key in (
        ("Proveedores", suppliers, SUPPLIERS, "ID"),
        ("Pedidos_2026", orders, ORDERS, "pedido"),
    ):
        table = workbook[sheet]
        header = [cell.value for cell in table[1]]
        if not set(mapping.values()) <= set(header):
            raise ValueError(f"Unexpected workbook header: {sheet}")
        rows = read_csv(path, mapping)
        existing = [
            dict(zip(header, row, strict=True))
            for row in table.iter_rows(min_row=2, values_only=True)
        ]
        added = 0
        for row in rows:
            item = {mapping[k]: v for k, v in row.items()}
            if sheet == "Pedidos_2026":
                try:
                    value = Decimal(item["Importe_Total"])
                    if not value.is_finite():
                        raise ValueError("Non-finite order amount")
                    item["Importe_Total"] = format(value, "f")
                except InvalidOperation as exc:
                    raise ValueError("Invalid order amount") from exc
            matches = [r for r in existing if str(r.get(mapping[key])) == row[key]]

            def same(previous, item=item):
                return all(
                    Decimal(str(previous[k])) == Decimal(str(v))
                    if k == "Importe_Total"
                    else str(previous[k] or "").strip() == str(v).strip()
                    for k, v in item.items()
                )

            if any(same(r) for r in matches):
                continue
            if matches:
                raise ValueError(f"Conflicting {sheet} key {row[key]}; no workbook written")
            table.append([item.get(k) for k in header])
            existing.append(item)
            added += 1
        counts[sheet] = {"added": added, "rows": sum(any(r.values()) for r in existing)}
    output.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output)
    manifest = {
        "inputs": {
            str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest()
            for p in (book, suppliers, orders)
        },
        "tables": counts,
    }
    output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("book", "suppliers", "orders", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.book, args.suppliers, args.orders, args.output), indent=2))


if __name__ == "__main__":
    main()
