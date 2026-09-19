import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load("build_hiring_seed", ROOT / "deploy/build-hiring-seed.py")
rule = load(
    "criminal_record_rule",
    ROOT / "processes/hiring-screening/rules/criminal-record-match.py",
)


def test_criminal_record_match_rejects_ana_and_ignores_other_candidates():
    records = builder.load_records(
        ROOT / "processes/hiring-screening/criminal_records_erp.py"
    )
    assert rule.evaluate(
        {"full_name": "  ANA   MOLINA "}, {"criminal_records": records}, []
    ) == {
        "fires": True,
        "reason": "CRIMINAL_RECORD_MATCH CR-00001",
    }
    assert rule.evaluate(
        {"full_name": "Aitana Blanco"}, {"criminal_records": records}, []
    ) == {"fires": False, "reason": ""}


def test_builder_caches_41_cvs_and_withholds_one_per_outcome():
    pack = ROOT / "processes/hiring-screening"
    expected = {
        row["file_id"]: row
        for line in (pack / "data/expected.jsonl").read_text().splitlines()
        if (row := json.loads(line))
    }
    readings = []
    for number, path in enumerate(sorted((pack / "data/cvs").glob("*.pdf")), 1):
        symbols = {
            name: {"value": value, "origin": "document:test"}
            for name, value in expected[path.name]["symbols"].items()
        }
        readings.append(
            {
                "id": number,
                "name": path.name,
                "process_name": "Hiring screening",
                "file_hash": __import__("hashlib")
                .sha256(path.read_bytes())
                .hexdigest(),
                "symbols": symbols,
                "values": {"free_text": "cached"},
                "events": [
                    {
                        "id": number,
                        "step": "extract_document",
                        "data": {"extraction": {"reader": "test"}, "symbols": symbols},
                    }
                ],
                "trace_events": [],
            }
        )
    base = {
        "version": 4,
        "examples": [],
        "rule_baselines": [
            {
                "process_id": 7,
                "process_name": "Hiring screening",
                "rules": [],
                "norm_rules": [],
                "guidance": {},
            }
        ],
        "ocr_cache": {"extraction_settings": {}},
    }
    seed = builder.build(pack, base, readings)
    assert seed["hiring"]["count"] == 41
    assert seed["hiring"]["withheld"] == [
        "cv-002.pdf",
        "cv-021.pdf",
        "cv-024.pdf",
    ]
    assert {row["name"] for row in seed["examples"]}.isdisjoint(
        seed["hiring"]["withheld"]
    )
    ana = next(row for row in seed["examples"] if row["name"] == "cv-001.pdf")
    assert (ana["expected"], ana["expected_reasons"]) == (
        "REJECT",
        ["CRIMINAL_RECORD_MATCH"],
    )
    scans = [
        row for row in seed["examples"] if row["name"] in {"cv-043.pdf", "cv-044.pdf"}
    ]
    assert {(row["expected"], tuple(row["expected_reasons"])) for row in scans} == {
        ("REVIEW", ("UNVERIFIED_DATA",))
    }
    baseline = seed["rule_baselines"][0]
    assert "criminal_records" in baseline["connectors"]
    assert baseline["rules"][-1]["decision"] == "REJECT"


def test_builder_requires_every_selected_reading():
    with pytest.raises(ValueError, match="Missing saved hiring readings"):
        builder.build(
            ROOT / "processes/hiring-screening",
            {
                "version": 4,
                "examples": [],
                "rule_baselines": [
                    {
                        "process_id": 7,
                        "process_name": "Hiring screening",
                        "rules": [],
                    }
                ],
            },
            [],
        )
