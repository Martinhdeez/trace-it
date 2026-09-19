import hashlib

import pytest

from app.common.exceptions import ConflictError
from app.features.processes.draft_schemas import DraftPlan, SourceProposal
from app.features.processes.tests.test_drafts import workbook_bytes
from app.features.sources import discovery


def mapping_data(formula=False):
    content = workbook_bytes(formula)
    digest = hashlib.sha256(content).hexdigest()
    source = SourceProposal(
        name="reference",
        kind="workbook",
        explanation="Confirmed table",
        document=digest,
        sheet="Reference",
        first_row=2,
        last_row=3,
        columns={"id": "A", "maximum": "B"},
        evidence=[{"reference": f"{digest}:Reference!A1", "explanation": "Header"}],
    )
    data = {
        "documents": {
            digest: {"name": "reference.xlsx", "workbook": discovery.read_workbook(content)}
        },
        "snapshots": {},
        "messages": [],
    }
    return DraftPlan(sources=[source]), data


def test_formula_is_not_silently_a_source_of_truth():
    plan, data = mapping_data(formula=True)
    with pytest.raises(ConflictError, match="formula"):
        discovery.materialize(plan, data)


def test_reversed_model_column_mapping_is_rejected():
    from pydantic import ValidationError

    plan, _ = mapping_data()
    proposed = plan.model_dump()
    proposed["sources"][0]["columns"] = {"A": "supplier_id", "B": "maximum"}
    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        DraftPlan.model_validate(proposed)


def test_nonexistent_sheet_and_empty_table_are_rejected():
    plan, data = mapping_data()
    plan.sources[0].sheet = "Missing"
    with pytest.raises(ConflictError, match="Unknown sheet"):
        discovery.materialize(plan, data)
    plan.sources[0].sheet = "Reference"
    plan.sources[0].first_row = 100
    plan.sources[0].last_row = 101
    with pytest.raises(ConflictError, match="no data"):
        discovery.materialize(plan, data)


def test_excel_dates_keep_iso_values_instead_of_serial_numbers():
    import io
    from datetime import datetime

    from openpyxl import Workbook

    book = Workbook()
    book.active.title = "Reference"
    book.active.append(["Date", "Maximum"])
    book.active.append([datetime(2026, 9, 18), 100.01])
    stream = io.BytesIO()
    book.save(stream)
    plan, data = mapping_data()
    digest = plan.sources[0].document
    data["documents"][digest]["workbook"] = discovery.read_workbook(stream.getvalue())
    rows = discovery.materialize(plan, data)["reference"]
    assert rows == [{"id": "2026-09-18T00:00:00", "maximum": "100.01"}]


@pytest.mark.parametrize(
    ("name", "content", "sheet"),
    [
        ("suppliers.csv", b"id;name\nSUP-1;Acme\n", "suppliers"),
        (
            "sources.json",
            b'{"suppliers":[{"id":"SUP-1","name":"Acme"}]}',
            "suppliers",
        ),
    ],
)
def test_csv_and_json_assets_use_the_reviewed_mapping_path(name, content, sheet):
    workbook = discovery.read_asset(name, content)
    source = SourceProposal(
        name="suppliers",
        kind="workbook",
        explanation="Reviewed supplier mapping",
        document="asset",
        sheet=sheet,
        first_row=2,
        last_row=2,
        columns={"id": "A", "name": "B"},
        evidence=[{"reference": f"asset:{sheet}!A1", "explanation": "Header"}],
    )
    data = {"documents": {"asset": {"name": name, "workbook": workbook}}}
    assert discovery.materialize(DraftPlan(sources=[source]), data) == {
        "suppliers": [{"id": "SUP-1", "name": "Acme"}]
    }


def test_unsupported_evidence_format_is_rejected():
    with pytest.raises(ConflictError, match="Supported evidence formats"):
        discovery.read_asset("policy.pdf", b"not a table")


def test_real_invoice_workbook_inventory_and_mapping():
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[5]
        / ".context/500-sombras-de-alberto/FINAL_v7_DEFINITIVO_ahorasi.xlsx"
    )
    if not path.exists():
        pytest.skip("Challenge workbook not installed")
    workbook = discovery.read_workbook(path.read_bytes())
    names = {sheet["name"] for sheet in workbook["sheets"]}
    assert {"Norma_Pagos_v3", "notas_alberto", "pendiente_revisar"} <= names
    source = SourceProposal(
        name="suppliers",
        kind="workbook",
        explanation="Supplier master",
        document="book",
        sheet="Proveedores",
        first_row=2,
        last_row=100,
        columns={"id": "A", "company_name": "B", "nif": "C", "iban": "D"},
        evidence=[{"reference": "book:Proveedores!A1", "explanation": "Header"}],
    )
    data = {"documents": {"book": {"name": path.name, "workbook": workbook}}}
    rows = discovery.materialize(DraftPlan(sources=[source]), data)["suppliers"]
    assert len(rows) >= 11
    assert all("id" in r and "iban" in r for r in rows)
