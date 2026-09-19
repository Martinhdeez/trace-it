import json
from pathlib import Path

import pytest

from app.features.decisions.demo_seed import load_references

ROOT = Path(__file__).resolve().parents[5]


def write(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def test_reference_files_map_outcomes_and_hiring_reason_codes(tmp_path):
    invoice = tmp_path / "invoice.jsonl"
    hiring = tmp_path / "hiring.jsonl"
    write(invoice, [{"file_id": "invoice.pdf", "expected": "PAGAR", "why": "clean"}])
    write(
        hiring,
        [
            {
                "file_id": "cv.pdf",
                "expected": "REVIEW",
                "why": ["MISSING_DATA: email", "SALARY_OVER_CAP"],
            }
        ],
    )

    references = load_references([invoice, hiring])

    assert references["invoice.pdf"].decision == "PAGAR"
    assert references["invoice.pdf"].reasons is None
    assert references["cv.pdf"].decision == "REVIEW"
    assert references["cv.pdf"].reasons == {"MISSING_DATA", "SALARY_OVER_CAP"}


def test_reference_files_reject_duplicate_names(tmp_path):
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    row = {"file_id": "same.pdf", "expected": "REVIEW", "why": []}
    write(first, [row])
    write(second, [row])

    with pytest.raises(ValueError, match="Duplicate outcome reference for same.pdf"):
        load_references([first, second])


def test_committed_reference_files_cover_both_demo_processes():
    references = load_references(
        [
            ROOT / "backend/tests/golden/batch1_expected.jsonl",
            ROOT / "processes/hiring-screening/data/expected.jsonl",
        ]
    )

    assert len(references) == 544
    assert references["2026-01-08_P001.pdf"].decision == "PAGAR"
    assert references["cv-011.pdf"].decision == "REVIEW"
