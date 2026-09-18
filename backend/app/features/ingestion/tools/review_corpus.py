"""File-by-file audit: independent Poppler transcription, field checks, and XLSX XML cells.

This consistency audit is not ground truth or a visual review of every native PDF.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from app.features.ingestion.tools.evaluate_scans import compare

FIELDS = {
    "supplier_tax_id": r"\bNIF\s*[:.]?\s*([A-Z][\s.-]*\d(?:[\s.-]*\d){7})(?!\d)",
    "payment_iban": r"\bIBAN\)?\s*[:.-]?\s*([A-Z]{2}\d{2}(?:[ -]*\d){10,30})",
    "purchase_order_ref": r"\b(PO-\d{4}-\d{4})(?!\d)",
    "net_amount": r"^(?:BASE(?: IMPONIBLE)?|IMPORTE BASE|SUBTOTAL)[ .:]*((?:EUR\s*)?[\d.,]+)",
    "vat_amount": (
        r"^(?:CUOTA\s+)?I\.?\s*V\.?\s*A\.?\s*\(?\s*"
        r"\d+(?:[.,]\d+)?\s*%\)?[ .:]*((?:EUR\s*)?[\d.,]+)"
    ),
    "vat_rate": r"^(?:CUOTA\s+)?I\.?\s*V\.?\s*A\.?\s*\(?\s*(\d+(?:[.,]\d+)?)\s*%",
    "gross_amount": r"^(?:TOTAL(?: A PAGAR| FACTURA)?|IMPORTE TOTAL)[ .:]*((?:EUR\s*)?[\d.,]+)",
    "issued_on": (
        r"\bFECHA(?:\s+(?:DE EMISION|"
        r"FACTURA))?\s*[:.]?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{4}|"
        r"\d{4}-\d{2}-\d{2}|\d{1,2} DE [A-Z]+ DE \d{4})"
    ),
    "invoice_number": (
        r"^(?:(?:N[Oº°]\s+DE|REF)\s+)?(?:FACTURA(?: SIMPLIFICADA)?(?: "
        r"N[Oº°])?|INVOICE)\s*[:#]?\s*([A-Z0-9]+[-/][A-Z0-9/-]+)"
    ),
}


def compact(value):
    value = unicodedata.normalize("NFKC", value)
    return "".join(c for c in value if not c.isspace() and unicodedata.category(c) != "Cf").upper()


def number(value):
    value = value.replace("EUR", "").strip()
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    return Decimal(value)


def check_native(path, result, executable, output):
    run = subprocess.run(
        [executable, "-layout", "-enc", "UTF-8", str(path), "-"],
        capture_output=True,
        check=True,
        timeout=30,
    )
    text = run.stdout.decode("utf-8")
    (output / "text" / (path.name + ".txt")).write_text(text, encoding="utf-8")
    references = {key: set() for key in FIELDS}
    for line in text.splitlines():
        upper = unicodedata.normalize("NFKC", line.strip()).upper()
        upper = "".join(c for c in upper if unicodedata.category(c) != "Cf")
        upper = "".join(
            c for c in unicodedata.normalize("NFD", upper) if not unicodedata.combining(c)
        )
        if upper.startswith(("CLIENTE", "DESTINATARIO")):
            continue
        for key, pattern in FIELDS.items():
            for match in re.finditer(pattern, upper):
                raw = match[1]
                if key in {"net_amount", "vat_amount", "gross_amount", "vat_rate"}:
                    value = str(number(raw))
                elif key == "issued_on":
                    value = "INVALID_DATE"
                    if " DE " in raw:
                        day, month, year = raw.split(" DE ")
                        names = [
                            "ENERO",
                            "FEBRERO",
                            "MARZO",
                            "ABRIL",
                            "MAYO",
                            "JUNIO",
                            "JULIO",
                            "AGOSTO",
                            "SEPTIEMBRE",
                            "OCTUBRE",
                            "NOVIEMBRE",
                            "DICIEMBRE",
                        ]
                        raw = f"{year}-{names.index(month) + 1:02}-{int(day):02}"
                    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d"):
                        try:
                            value = datetime.strptime(raw, fmt).date().isoformat()
                            break
                        except ValueError:
                            pass
                elif key in {"supplier_tax_id", "payment_iban"}:
                    value = re.sub(r"[ .-]", "", raw)
                else:
                    value = raw
                references[key].add(value)
    checks = {}
    for key, field in result["fields"].items():
        errors = []
        for candidate in field["candidates"]:
            if candidate["evidence"]["method"] == "native" and compact(
                candidate["evidence"]["text"]
            ) not in compact(text):
                errors.append("EVIDENCE_NOT_IN_INDEPENDENT_TEXT")
        if key in references:
            refs = references[key]
            equal = (
                number(field["value"]) in {number(v) for v in refs}
                if key in {"net_amount", "vat_amount", "gross_amount", "vat_rate"}
                and field["value"]
                else field["value"] in refs
            )
            if key == "issued_on" and refs == {"INVALID_DATE"} and field["status"] == "INVALID":
                equal = True
            if not refs and key == "invoice_number" and field["status"] == "MISSING":
                pass
            elif not refs:
                errors.append("REFERENCE_PARSER_UNSUPPORTED")
            elif not equal:
                errors.append("INDEPENDENT_VALUE_MISMATCH")
            elif len(refs) > 1:
                errors.append("MULTIPLE_REFERENCE_VALUES")
        checks[key] = {
            "value": field["value"],
            "status": field["status"],
            "independent_values": sorted(references.get(key, [])),
            "issues": sorted(set(errors)),
        }
    return {
        "file_id": path.name,
        "sha256": result["sha256"],
        "method": "independent_text",
        "field_checks": checks,
        "warnings": result["warnings"],
        "pages": result["pages"],
    }


def check_workbook(path, result):
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    relns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    emitted = {
        s["name"]: {c["cell"]: c for row in s["rows"] for c in row["cells"]}
        for s in result["data"]["sheets"]
    }
    sheets = []
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared = [
                "".join(si.itertext()) for si in ET.fromstring(archive.read("xl/sharedStrings.xml"))
            ]
        rels = {
            r.attrib["Id"]: r.attrib["Target"]
            for r in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        }
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        for sheet in workbook.findall("m:sheets/m:sheet", ns):
            name = sheet.attrib["name"]
            target = rels[sheet.attrib[f"{{{relns}}}id"]]
            target = target.lstrip("/") if target.startswith("/") else "xl/" + target
            checks = []
            for cell in ET.fromstring(archive.read(target)).findall(".//m:sheetData/m:row/m:c", ns):
                coord, kind = cell.attrib["r"], cell.attrib.get("t", "n")
                formula = cell.find("m:f", ns)
                value = cell.findtext("m:v", default="", namespaces=ns)
                if formula is not None:
                    expected = "=" + (formula.text or "")
                elif kind == "inlineStr":
                    expected = "".join(t.text or "" for t in cell.findall(".//m:t", ns))
                elif kind == "s":
                    expected = shared[int(value)]
                else:
                    expected = value
                if expected == "":
                    continue
                actual = emitted[name].get(coord)
                equal = actual is not None and (
                    Decimal(actual.get("xml_numeric_value") or str(actual["raw"]))
                    == Decimal(expected)
                    if kind == "n" and formula is None
                    else str(actual["raw"]) == expected
                )
                checks.append(
                    {
                        "cell": coord,
                        "source_raw": expected,
                        "api_raw": actual["raw"] if actual else None,
                        "api_xml_numeric_value": actual.get("xml_numeric_value")
                        if actual
                        else None,
                        "matches": equal,
                    }
                )
            sheets.append(
                {
                    "sheet": name,
                    "cells_checked": len(checks),
                    "cells": checks,
                    "extra_cells": sorted(set(emitted[name]) - {x["cell"] for x in checks}),
                }
            )
    # Independently transcribed schemas of the two official master sheets.
    # This is an audit oracle for this fixture, never production extraction logic.
    schemas = {
        "Proveedores": {
            "A": "supplier_ref",
            "B": "supplier_name",
            "C": "supplier_tax_id",
            "D": "authorized_iban",
        },
        "Pedidos_2026": {
            "A": "purchase_order_ref",
            "B": "supplier_ref",
            "C": "supplier_tax_id",
            "D": "expected_gross_amount",
            "E": "state",
            "F": "ordered_on",
        },
    }
    records = {(r["sheet"], r["row"]): r for r in result["data"]["records"]}
    canonical_checks = []
    for sheet in sheets:
        schema = schemas.get(sheet["sheet"])
        if not schema:
            continue
        for cell in sheet["cells"]:
            coordinate = re.fullmatch(r"([A-Z]+)(\d+)", cell["cell"])
            column, row = coordinate[1], int(coordinate[2])
            if row == 1 or column not in schema:
                continue
            key = schema[column]
            raw = cell["source_raw"]
            if key == "expected_gross_amount":
                expected = format(Decimal(raw).quantize(Decimal("0.01")), "f")
            elif key in {"supplier_tax_id", "authorized_iban"}:
                expected = compact(raw)
            else:
                expected = " ".join(raw.split())
            observed = records.get((sheet["sheet"], row), {}).get("fields", {}).get(key, {})
            canonical_checks.append(
                {
                    "locator": sheet["sheet"] + "!" + cell["cell"],
                    "field": key,
                    "expected": expected,
                    "observed": observed.get("value"),
                    "matches": expected == observed.get("value"),
                }
            )
    return {
        "file_id": path.name,
        "sha256": result["sha256"],
        "method": "independent_xlsx_xml",
        "sheets": sheets,
        "records": len(result["data"]["records"]),
        "canonical_checks": canonical_checks,
        "warnings": result["warnings"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("extractions", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/review"))
    parser.add_argument(
        "--scan-labels",
        type=Path,
        default=(Path(__file__).resolve().parents[1] / "tests/fixtures/scans-reviewed.json"),
    )
    args = parser.parse_args()
    (args.output / "text").mkdir(parents=True, exist_ok=True)
    executable = shutil.which("pdftotext")
    if not executable:
        raise RuntimeError("pdftotext is required")
    results = {
        r["file_id"]: r
        for r in map(json.loads, args.extractions.read_text(encoding="utf-8").splitlines())
    }
    files = sorted(args.input.rglob("*.pdf")) + sorted(args.input.rglob("*.xlsx"))
    labels = {r["file_id"]: r for r in json.loads(args.scan_labels.read_text(encoding="utf-8"))}

    def review(path):
        result = results[path.name]
        if hashlib.sha256(path.read_bytes()).hexdigest() != result["sha256"]:
            raise ValueError(f"Stale extraction: {path.name}")
        if path.suffix == ".xlsx":
            return check_workbook(path, result)
        if result["metrics"]["ocr_calls"]:
            reference = labels.get(path.name)
            if reference and reference["sha256"] != result["sha256"]:
                raise ValueError(f"Stale visual labels: {path.name}")
            return {
                "file_id": path.name,
                "sha256": result["sha256"],
                "method": "visual_development_labels" if reference else "visual_review_required",
                "comparison": compare(result, reference) if reference else None,
                "fields": result["fields"],
                "warnings": result["warnings"],
            }
        return check_native(path, result, executable, args.output)

    with ThreadPoolExecutor(max_workers=4) as pool:
        reviews = list(pool.map(review, files))
    with (args.output / "files.jsonl").open("w", encoding="utf-8") as stream:
        for row in reviews:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {
        "files": len(reviews),
        "methods": dict(Counter(r["method"] for r in reviews)),
        "pdf_field_issues": dict(
            Counter(
                issue
                for r in reviews
                for f in r.get("field_checks", {}).values()
                for issue in f["issues"]
            )
        ),
        "xlsx_cells_checked": sum(s["cells_checked"] for r in reviews for s in r.get("sheets", [])),
        "xlsx_mismatches": sum(
            not c["matches"] for r in reviews for s in r.get("sheets", []) for c in s["cells"]
        ),
        "xlsx_canonical_fields_checked": sum(len(r.get("canonical_checks", [])) for r in reviews),
        "xlsx_canonical_mismatches": sum(
            not c["matches"] for r in reviews for c in r.get("canonical_checks", [])
        ),
        "scan_labeled_fields": sum(
            len(r["comparison"]["checks"]) for r in reviews if r.get("comparison")
        ),
        "scan_matching_values": sum(
            c["matches"]
            for r in reviews
            if r.get("comparison")
            for c in r["comparison"]["checks"].values()
        ),
        "scan_wrong_observed_values": sum(
            not c["matches"] and c["status"] == "OBSERVED"
            for r in reviews
            if r.get("comparison")
            for c in r["comparison"]["checks"].values()
        ),
        "note": (
            "Poppler and XML consistency audit; scan development labels "
            "transcribed visually by assistant, not independent "
            "organizer ground truth."
        ),
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
