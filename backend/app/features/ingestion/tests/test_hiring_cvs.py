"""The generic reader maps the hiring CVs: the first documents that are not invoices.

No LLM, no OCR, no database. The text-layer CVs under `processes/hiring-screening/data` go
through the same `extract_schema` a process upload uses, with the field schema the manager
describes in `manager-notes.md`. Whatever this test reports is what discovery can build on
before any model is involved. The two scanned CVs need OCR weights; the demo covers them.
"""

import io
import json
from pathlib import Path

from app.features.ingestion.extraction_plan import ExtractionField, ExtractionPlan
from app.features.ingestion.process_extraction import schema_symbols
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService

from .conftest import NoOCR, NoVLM

ROOT = Path(__file__).resolve().parents[5]
DATA = ROOT / "processes" / "hiring-screening" / "data"

# The schema as manager-notes.md describes it: English and Spanish labels, three required.
FIELDS = [
    ExtractionField(name="candidate_id", type="text", source="filename"),
    ExtractionField(
        name="full_name", type="text", required=True, labels=["Full name", "Nombre completo"]
    ),
    ExtractionField(
        name="email", type="text", required=True, labels=["Email", "Correo electrónico"]
    ),
    ExtractionField(
        name="position_code",
        type="text",
        required=True,
        labels=["Position code", "Código de puesto"],
    ),
    ExtractionField(
        name="years_experience",
        type="integer",
        labels=["Years of experience", "Años de experiencia"],
    ),
    ExtractionField(
        name="expected_salary",
        type="number",
        labels=["Expected salary (EUR)", "Salario esperado (EUR)"],
    ),
    ExtractionField(
        name="available_from", type="date", labels=["Available from", "Disponible desde"]
    ),
    ExtractionField(name="skills", type="text", labels=["Skills", "Competencias"]),
]


def expected_rows() -> list[dict]:
    lines = (DATA / "expected.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def read(service: ExtractionService, file_id: str) -> dict:
    content = (DATA / "cvs" / file_id).read_bytes()
    item = service.ingest(io.BytesIO(content), file_id)
    plan = ExtractionPlan(process_id=1, fields=FIELDS)
    result = service.extract_schema(item, ExtractOptions(ocr=False, vlm=False), plan)
    return {name: symbol["value"] for name, symbol in schema_symbols(result, FIELDS).items()}


def test_text_cvs_yield_the_true_symbols_with_labels_alone(settings):
    service = ExtractionService(settings, NoOCR(), NoVLM())
    wrong = []
    for row in expected_rows():
        if row["scanned"]:
            continue
        got = read(service, row["file_id"])
        for name, value in row["symbols"].items():
            if got.get(name) != value:
                wrong.append((row["file_id"], row["category"], name, value, got.get(name)))
    assert not wrong, "\n".join(
        f"{fid} [{cat}] {name}: expected {exp!r}, read {got!r}"
        for fid, cat, name, exp, got in wrong
    )


def test_scanned_cvs_leave_required_symbols_empty_without_ocr(settings):
    """Nothing is invented for an image-only page: the required symbols stay None, so the
    engine escalates the instance instead of interviewing on a blank profile."""
    service = ExtractionService(settings, NoOCR(), NoVLM())
    scanned = [row for row in expected_rows() if row["scanned"]]
    assert len(scanned) == 2
    for row in scanned:
        got = read(service, row["file_id"])
        assert got["candidate_id"] == row["file_id"]
        assert got["full_name"] is None
        assert got["email"] is None
        assert got["position_code"] is None
