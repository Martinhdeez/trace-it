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
