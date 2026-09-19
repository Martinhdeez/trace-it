"""Tabular evidence and deterministic extraction of reviewed source mappings."""

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook
from openpyxl.utils.cell import column_index_from_string

from app.common.exceptions import ConflictError
from app.features.processes.draft_schemas import DraftPlan
from app.features.sources.excel import extract_workbook


@dataclass
class Limits:
    max_excel_rows: int = 20000
    max_excel_cols: int = 100
    max_excel_cells: int = 200000


def read_workbook(content: bytes) -> dict:
    try:
        workbook, warnings = extract_workbook(content, Limits())
        return {**workbook, "warnings": warnings}
    except (ValueError, KeyError, TypeError) as error:
        raise ConflictError(f"Cannot read workbook: {error}") from error


def _sheet_name(name: str, used: set[str]) -> str:
    base = "".join("_" if char in "[]:*?/\\" else char for char in name).strip()[:31]
    base = base or "Data"
    candidate = base
    number = 2
    while candidate in used:
        suffix = f"_{number}"
        candidate = f"{base[: 31 - len(suffix)]}{suffix}"
        number += 1
    used.add(candidate)
    return candidate


def _json_tables(value: object, fallback: str) -> list[tuple[str, list[object]]]:
    if isinstance(value, list):
        return [(fallback, value)]
    if isinstance(value, dict) and value and all(isinstance(rows, list) for rows in value.values()):
        return [(str(name), rows) for name, rows in value.items()]
    if isinstance(value, dict):
        return [(fallback, [value])]
    raise ConflictError("JSON evidence must contain an object, a list, or named lists")


def _cell_value(value: object) -> object:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def _tabular_workbook(name: str, content: bytes) -> bytes:
    suffix = Path(name).suffix.lower()
    book = Workbook()
    book.remove(book.active)
    used: set[str] = set()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ConflictError(f"Cannot read {suffix[1:].upper()} evidence as UTF-8") from error
    if suffix == ".csv":
        try:
            dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.reader(io.StringIO(text), dialect=dialect))
        if not any(any(cell.strip() for cell in row) for row in rows):
            raise ConflictError("CSV evidence is empty")
        sheet = book.create_sheet(_sheet_name(Path(name).stem, used))
        for row in rows:
            sheet.append(row)
    else:
        try:
            tables = _json_tables(json.loads(text), Path(name).stem)
        except json.JSONDecodeError as error:
            raise ConflictError(f"Cannot read JSON evidence: {error.msg}") from error
        for table_name, records in tables:
            sheet = book.create_sheet(_sheet_name(table_name, used))
            if records and all(isinstance(record, dict) for record in records):
                headers = list(dict.fromkeys(key for record in records for key in record))
                sheet.append(headers)
                for record in records:
                    sheet.append([_cell_value(record.get(header)) for header in headers])
            else:
                sheet.append(["value"])
                for record in records:
                    sheet.append([_cell_value(record)])
    stream = io.BytesIO()
    book.save(stream)
    return stream.getvalue()


def read_asset(name: str, content: bytes) -> dict:
    """Normalize supported evidence into the workbook-shaped discovery representation."""
    suffix = Path(name).suffix.lower()
    if suffix == ".xlsx":
        return read_workbook(content)
    if suffix in {".csv", ".json"}:
        return read_workbook(_tabular_workbook(name, content))
    raise ConflictError("Supported evidence formats are .xlsx, .csv and .json")


def inventory(documents: dict) -> list[dict]:
    return [
        {
            "document": digest,
            "name": document["name"],
            "format": Path(document["name"]).suffix.lower().lstrip("."),
            "warnings": document["workbook"]["warnings"],
            "sheets": [
                {
                    "name": sheet["name"],
                    "visibility": sheet["visibility"],
                    "last_row": max((r["row"] for r in sheet["rows"]), default=0),
                    "sample": sheet["rows"][:12],
                }
                for sheet in document["workbook"]["sheets"]
            ],
        }
        for digest, document in documents.items()
    ]


def sheet_rows(documents: dict, document: str, sheet: str, first: int, last: int) -> list[dict]:
    if document not in documents:
        raise ValueError("Unknown workbook")
    found = next((s for s in documents[document]["workbook"]["sheets"] if s["name"] == sheet), None)
    if found is None:
        raise ValueError("Unknown sheet")
    return [r for r in found["rows"] if first <= r["row"] <= last]


def evidence_references(data: dict) -> set[str]:
    references = {f"chat:{i + 1}" for i in range(len(data["messages"]))}
    references.update(f"snapshot:{name}" for name in data["snapshots"])
    references.update(data.get("base_references", []))
    references.update((data.get("case_context") or {}).get("evidence", {}))
    sampling = (data.get("case_context") or {}).get("sampling", {})
    references.update(
        f"sampling.{key}" for key in ("outcome_counts", "author_counts") if key in sampling
    )
    for digest, document in data["documents"].items():
        for sheet in document["workbook"]["sheets"]:
            for row in sheet["rows"]:
                references.update(f"{digest}:{sheet['name']}!{c['cell']}" for c in row["cells"])
    return references


def _row_key(row: dict, fields: list[str], source: str) -> tuple:
    values = tuple(row.get(field) for field in fields)
    if any(value is None or value == "" for value in values):
        raise ConflictError(f"{source}: mutation key {fields} is missing in a row")
    return values


def _indexed(rows: list[dict], fields: list[str], source: str) -> dict[tuple, dict]:
    indexed = {}
    for row in rows:
        key = _row_key(row, fields, source)
        if key in indexed:
            raise ConflictError(f"{source}: duplicate mutation key {key}")
        indexed[key] = row
    return indexed


def _mutate(proposal, incoming: list[dict], base: list[dict]) -> list[dict]:
    if proposal.operation == "replace":
        return incoming
    if proposal.operation == "append":
        combined = [*base, *incoming]
        if proposal.key:
            _indexed(combined, proposal.key, proposal.name)
        return combined
    existing = _indexed(base, proposal.key, proposal.name)
    changes = _indexed(incoming, proposal.key, proposal.name)
    if proposal.operation == "delete":
        return [row for row in base if _row_key(row, proposal.key, proposal.name) not in changes]
    result = [changes.pop(key, row) for key, row in existing.items()]
    return [*result, *changes.values()]


def materialize(plan: DraftPlan, data: dict) -> dict[str, list[dict]]:
    tables = {}
    for proposal in plan.sources:
        if proposal.kind == "constant":
            incoming = proposal.rows
        elif proposal.kind == "snapshot":
            if proposal.snapshot not in data["snapshots"]:
                raise ConflictError(f"Missing complete snapshot {proposal.snapshot}")
            incoming = data["snapshots"][proposal.snapshot]["rows"]
        else:
            if not proposal.columns or proposal.first_row > proposal.last_row:
                raise ConflictError(f"Invalid mapping for {proposal.name}")
            try:
                columns = {
                    name: column_index_from_string(col) for name, col in proposal.columns.items()
                }
                rows = sheet_rows(
                    data["documents"],
                    proposal.document,
                    proposal.sheet,
                    proposal.first_row,
                    proposal.last_row,
                )
            except ValueError as error:
                raise ConflictError(f"{proposal.name}: {error}") from error
            extracted = []
            for row in rows:
                cells = {c["column"]: c for c in row["cells"]}
                values = {}
                for name, col in columns.items():
                    cell = cells.get(col)
                    if cell and (cell["formula"] or cell["excel_type"] == "e"):
                        raise ConflictError(
                            f"Unverified formula or error at {proposal.sheet}!{cell['cell']}"
                        )
                    values[name] = None
                    if cell:
                        # Excel dates have numeric XML storage too; keep the reader's
                        # ISO date, not the underlying serial day number.
                        values[name] = (
                            cell.get("xml_numeric_value") or cell["value"]
                            if cell["excel_type"] == "n"
                            else cell["value"]
                        )
                if any(v is not None for v in values.values()):
                    extracted.append(values)
            if not extracted:
                raise ConflictError(f"{proposal.name}: mapping contains no data")
            incoming = extracted
        base = data.get("base_sources", {}).get(proposal.name, [])
        tables[proposal.name] = _mutate(proposal, incoming, base)
    return tables


def mutation_summary(plan: DraftPlan, data: dict, tables: dict[str, list[dict]]) -> list[dict]:
    return [
        {
            "source": proposal.name,
            "operation": proposal.operation,
            "key": proposal.key,
            "before": len(data.get("base_sources", {}).get(proposal.name, [])),
            "after": len(tables[proposal.name]),
        }
        for proposal in plan.sources
    ]
