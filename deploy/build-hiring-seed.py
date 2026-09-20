"""Add the reviewed hiring corpus and pinned criminal-records source to a v4 seed."""

import argparse
import base64
import hashlib
import importlib.util
import json
from copy import deepcopy
from pathlib import Path

WITHHELD = {"cv-002.pdf", "cv-021.pdf", "cv-024.pdf"}
RULE_TEXT = (
    "Reject a candidate when their full name appears in the criminal-records registry."
)


def load_records(script: Path) -> list[dict]:
    spec = importlib.util.spec_from_file_location("hiring_criminal_records", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return deepcopy(module.RECORDS)


def connector() -> dict:
    return {
        "type": "http",
        "base_url": {
            "env": "TRACE_CRIMINAL_RECORDS_URL",
            "default": "http://127.0.0.1:8010",
        },
        "format": {
            "type": "xml",
            "encoding": "iso-8859-1",
            "error_code_path": "code",
        },
        "auth": {"type": "none"},
        "pagination": {
            "path": "/criminal/records",
            "page_param": "page",
            "page_size": 10,
            "records_path": "records/record",
            "total_path": "meta/total",
            "pages_path": "meta/pages",
        },
        "key": "record_id",
        "fields": {
            "record_id": {"source": "id"},
            "full_name": {"source": "name"},
            "conviction_date": {"source": "conviction_date"},
            "offense": {"source": "offense"},
            "status": {"source": "status"},
        },
    }


def build(pack: Path, base_seed: dict, readings: list[dict]) -> dict:
    if base_seed.get("version") != 4:
        raise ValueError("Hiring requires the version-4 cached seed")
    seed = deepcopy(base_seed)
    baseline = next(
        (b for b in seed["rule_baselines"] if b["process_name"] == "Hiring screening"),
        None,
    )
    if baseline is None:
        raise ValueError("The seed has no reviewed Hiring screening baseline")
    process_id = baseline["process_id"]
    expected = {
        row["file_id"]: row
        for line in (pack / "data/expected.jsonl").read_text().splitlines()
        if (row := json.loads(line))
    }
    pdfs = {path.name: path for path in (pack / "data/cvs").glob("*.pdf")}
    if len(pdfs) != 44 or set(expected) != set(pdfs) or not WITHHELD <= set(pdfs):
        raise ValueError("Expected the complete 44-CV hiring corpus")
    selected = set(pdfs) - WITHHELD
    by_name = {
        row["name"]: row
        for row in readings
        if row.get("name") in selected
        and row.get("process_name", "Hiring screening") == "Hiring screening"
    }
    if set(by_name) != selected:
        missing = sorted(selected - set(by_name))
        raise ValueError(f"Missing saved hiring readings: {', '.join(missing)}")

    seed["examples"] = [e for e in seed["examples"] if e["process_id"] != process_id]
    documents = {}
    for name in sorted(selected):
        content = pdfs[name].read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        reading = by_name[name]
        if reading["file_hash"] != digest:
            raise ValueError(f"PDF differs from cached application reading: {name}")
        candidates = [
            event
            for event in reading["events"]
            if event["step"] in {"ingest_document", "extract_document"}
            and event.get("data", {}).get("extraction")
            and event["data"].get("symbols") == reading["symbols"]
        ]
        if not candidates:
            raise ValueError(f"No matching extraction evidence: {name}")
        evidence = deepcopy(max(candidates, key=lambda event: event["id"])["data"])
        reference = deepcopy(expected[name])
        if name == "cv-001.pdf":
            reference.update(expected="REJECT", why=["CRIMINAL_RECORD_MATCH: CR-00001"])
        elif reference["scanned"]:
            # The policy answer key ignores confidence. ADR 0025 sends these cached OCR
            # readings to a person because their required fields remain unverified.
            reference.update(expected="REVIEW", why=["UNVERIFIED_DATA"])
        seed["examples"].append(
            {
                "process_id": process_id,
                "process_name": "Hiring screening",
                "name": name,
                "symbols": reading["symbols"],
                "hash": digest,
                "content": base64.b64encode(content).decode(),
                "text": reading.get("values", {}).get("free_text") or "",
                "evidence": evidence,
                "trace_events": reading.get("trace_events", []),
                "expected": reference["expected"],
                "expected_reasons": [
                    reason.split(":", 1)[0] for reason in reference.get("why", [])
                ],
                "provenance": {
                    "source_instance_id": reading["id"],
                    "source_event_id": max(candidates, key=lambda event: event["id"])[
                        "id"
                    ],
                    "source_path": f"data/cvs/{name}",
                },
            }
        )
        documents[name] = digest

    code = (pack / "rules/criminal-record-match.py").read_text()
    rule_hash = hashlib.sha256(f"{RULE_TEXT}\0{code}".encode()).hexdigest()
    baseline["rules"] = [r for r in baseline["rules"] if r["text"] != RULE_TEXT]
    baseline["rules"].append(
        {
            "text": RULE_TEXT,
            "summary": "A registry name match rejects the candidate.",
            "type": "prohibition",
            "decision": "REJECT",
            "code": code,
            "hash": rule_hash,
            "tests": [],
            "report": {"valid": True, "source": "reviewed_hiring_seed"},
            "status": "active",
            "norm_rule_id": None,
        }
    )
    baseline["connectors"] = {"criminal_records": connector()}
    baseline["source_schemas"] = {
        "criminal_records": {
            "required": ["record_id", "full_name", "status"],
            "optional": ["conviction_date", "offense"],
            "sync_before_run": True,
        }
    }
    records = load_records(pack / "criminal_records_erp.py")
    seed["hiring"] = {
        "process_id": process_id,
        "process_name": "Hiring screening",
        "count": 41,
        "documents": documents,
        "withheld": sorted(WITHHELD),
        "source": "criminal_records",
        "source_rows": records,
        "erp_count": len(records),
    }
    if baseline.get("extraction_settings"):
        cache = seed.setdefault("ocr_cache", {})
        cache.setdefault("extraction_settings", {})["Hiring screening"] = baseline[
            "extraction_settings"
        ]
    return seed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--base-seed", type=Path, required=True)
    parser.add_argument("--readings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    seed = build(
        args.pack,
        json.loads(args.base_seed.read_text()),
        json.loads(args.readings.read_text()),
    )
    with args.output.open("x") as output:
        json.dump(seed, output, ensure_ascii=False, default=str)
    print(json.dumps({"hiring_examples": seed["hiring"]["count"]}))


if __name__ == "__main__":
    main()
