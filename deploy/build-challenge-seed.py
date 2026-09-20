"""Build a full challenge fixture from original files and saved application readings."""

import argparse
import ast
import base64
import csv
import hashlib
import io
import json
import re
import subprocess
import zlib
from copy import deepcopy
from pathlib import Path

import openpyxl


def erp_rows(rows):
    keys = {
        "entry_id": "asiento_id",
        "date": "fecha_registro",
        "supplier_id": "proveedor_id",
        "nif": "nif",
        "purchase_order": "pedido",
        "amount": "importe_esperado",
        "status": "estado",
    }
    return [{key: row[source] for key, source in keys.items()} for row in rows]


def reference_sources(root):
    with (root / "alberto_erp.py").open() as source:
        literal = re.search(
            r"^_DATOS_ERP = (\(.*?\n\))", source.read(), re.DOTALL | re.MULTILINE
        )
    raw = zlib.decompress(base64.b64decode(ast.literal_eval(literal.group(1)))).decode()
    original_erp = erp_rows(csv.DictReader(io.StringIO(raw)))
    book = openpyxl.load_workbook(
        root / "FINAL_v7_DEFINITIVO_ahorasi.xlsx", read_only=True, data_only=True
    )

    def sheet(name):
        header, *rows = book[name].values
        return [dict(zip(header, row, strict=True)) for row in rows if any(row)]

    suppliers = [
        {
            "id": r["ID"],
            "company_name": r["Razon Social"],
            "nif": r["NIF"],
            "iban": r["IBAN"],
        }
        for r in sheet("Proveedores")
    ]
    orders = [
        {
            "purchase_order": r["Pedido"],
            "supplier_id": r["ProveedorID"],
            "nif": r["NIF"],
            "total_amount": r["Importe_Total"],
            "status": r["Estado"],
            "order_date": r["Fecha_Pedido"],
        }
        for r in sheet("Pedidos_2026")
    ]
    book.close()
    first = {
        "suppliers": suppliers,
        "orders": orders,
        "erp": original_erp,
        "parameters": [{"cut_off_date": "2026-09-18"}],
    }
    second = deepcopy(first)

    def extra(name):
        with (root / name).open() as source:
            return list(csv.DictReader(source))

    second["suppliers"] += [
        {
            "id": r["ID"],
            "company_name": r["Razon Social"],
            "nif": r["NIF"],
            "iban": r["IBAN"],
        }
        for r in extra("proveedores_nuevos.csv")
    ]
    # New order rows can include existing keys: preserve the published latest row per key.
    merged = {r["purchase_order"]: r for r in orders}
    for r in extra("pedidos_nuevos.csv"):
        merged[r["pedido"]] = {
            "purchase_order": r["pedido"],
            "supplier_id": r["proveedor_id"],
            "nif": r["nif"],
            "total_amount": r["importe_total"],
            "status": r["estado"],
            "order_date": r["fecha_pedido"],
        }
    second["orders"] = list(merged.values())
    merged = {r["entry_id"]: r for r in original_erp}
    merged.update({r["entry_id"]: r for r in erp_rows(extra("erp_export_lote2.csv"))})
    second["erp"] = list(merged.values())
    second["parameters"] = [{"cut_off_date": "2026-09-19"}]
    return first, second


def build(root, base_seed, readings, cache):
    commit = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    # Verify source bytes against Git, excluding untracked Python caches.
    subprocess.run(
        ["git", "-C", str(root), "diff", "--exit-code", "HEAD", "--"],
        check=True,
        capture_output=True,
    )
    seed = deepcopy(base_seed)
    original = next(
        b for b in seed["rule_baselines"] if b["process_name"] == "Invoice payment"
    )
    seed["rule_baselines"] = [
        baseline
        for baseline in seed["rule_baselines"]
        if baseline["process_name"] != "Invoice payment - batch 2"
    ]
    first_id = original["process_id"]
    original["extraction_settings"] = cache["extraction_settings"][
        original["process_name"]
    ]
    # A later ordinary run must not replace batch 1 with the live batch-2 ERP.
    schemas = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "processes/invoice-payment/schema.json"
        ).read_text()
    )["sources"]
    schemas["erp"]["sync_before_run"] = False
    original["source_schemas"] = schemas
    seed["examples"] = [
        example
        for example in seed["examples"]
        if example["process_name"]
        not in {"Invoice payment", "Invoice payment - batch 2"}
    ]
    by_name = {r["name"]: r for r in readings}
    if len(by_name) != len(readings):
        raise ValueError("Duplicate saved readings")
    seed.update(
        version=4,
        challenge_commit=commit,
        ocr_cache=cache,
        batches=[],
        reference_files=[],
    )
    for number, folder, count, tables in (
        (
            1,
            "facturas",
            500,
            reference_sources(root)[0],
        ),
        (2, "facturas_primin", 40, reference_sources(root)[1]),
    ):
        documents = {}
        for pdf in sorted((root / folder).glob("*.pdf")):
            content = pdf.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            reading = by_name[pdf.name]
            if digest != reading["file_hash"]:
                raise ValueError(
                    f"PDF differs from cached application reading: {pdf.name}"
                )
            candidates = [
                e
                for e in reading["events"]
                if e["step"] in {"ingest_document", "extract_document"}
                and e.get("data", {}).get("extraction")
                and e["data"].get("symbols") == reading["symbols"]
            ]
            if not candidates:
                raise ValueError(
                    f"No matching original extraction evidence: {pdf.name}"
                )
            event = max(candidates, key=lambda e: e["id"])
            evidence = deepcopy(event["data"])
            text = reading.get("values", {}).get("free_text") or ""
            seed["examples"].append(
                {
                    "process_id": first_id,
                    "process_name": original["process_name"],
                    "name": pdf.name,
                    "symbols": reading["symbols"],
                    "hash": digest,
                    "content": base64.b64encode(content).decode(),
                    "text": text,
                    "evidence": evidence,
                    "trace_events": reading.get("trace_events", []),
                    "provenance": {
                        "source_instance_id": reading["id"],
                        "source_event_id": event["id"],
                        "challenge_commit": commit,
                        "source_path": folder + "/" + pdf.name,
                    },
                }
            )
            documents[pdf.name] = digest
        if len(documents) != count:
            raise ValueError("Incomplete original repository batch")
        batch = {
            "number": number,
            "process_id": first_id,
            "process_name": original["process_name"],
            "count": count,
            "documents": documents,
            "sources": tables,
            "erp_count": len(tables["erp"]),
        }
        seed["batches"].append(batch)
    for name in [
        "FINAL_v7_DEFINITIVO_ahorasi.xlsx",
        "alberto_erp.py",
        "erp_export_lote2.csv",
        "pedidos_nuevos.csv",
        "proveedores_nuevos.csv",
    ]:
        content = (root / name).read_bytes()
        seed["reference_files"].append(
            {
                "name": name,
                "hash": hashlib.sha256(content).hexdigest(),
                "content": base64.b64encode(content).decode(),
            }
        )
    return seed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("challenge", "base-seed", "readings", "cache", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    seed = build(
        args.challenge,
        json.loads(args.base_seed.read_text()),
        json.loads(args.readings.read_text()),
        json.loads(args.cache.read_text()),
    )
    with args.output.open("x") as out:
        json.dump(seed, out, ensure_ascii=False, default=str)
    print(
        json.dumps(
            {"examples": len(seed["examples"]), "commit": seed["challenge_commit"]}
        )
    )


if __name__ == "__main__":
    main()
