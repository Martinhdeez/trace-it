"""Workbook evidence and deterministic extraction of reviewed table mappings."""

from dataclasses import dataclass

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


def inventory(documents: dict) -> list[dict]:
    return [
        {
            "document": digest,
            "name": document["name"],
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
    for digest, document in data["documents"].items():
        for sheet in document["workbook"]["sheets"]:
            for row in sheet["rows"]:
                references.update(f"{digest}:{sheet['name']}!{c['cell']}" for c in row["cells"])
    return references


def materialize(plan: DraftPlan, data: dict) -> dict[str, list[dict]]:
    tables = {}
    for proposal in plan.sources:
        if proposal.kind == "constant":
            tables[proposal.name] = proposal.rows
        elif proposal.kind == "snapshot":
            if proposal.snapshot not in data["snapshots"]:
                raise ConflictError(f"Missing complete snapshot {proposal.snapshot}")
            tables[proposal.name] = data["snapshots"][proposal.snapshot]["rows"]
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
                    values[name] = (
                        (cell.get("xml_numeric_value") or cell["value"]) if cell else None
                    )
                if any(v is not None for v in values.values()):
                    extracted.append(values)
            if not extracted:
                raise ConflictError(f"{proposal.name}: mapping contains no data")
            tables[proposal.name] = extracted
    return tables
