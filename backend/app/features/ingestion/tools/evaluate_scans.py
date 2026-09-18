"""Development comparison against visually transcribed scans, not organizer ground truth."""

import argparse
import hashlib
import json
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

from app.features.ingestion.config import REPOSITORY_ROOT, Settings
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService


def compare(result, reference):
    checks = {}
    for key, expected in reference["fields"].items():
        field = result["fields"][key]
        checks[key] = {
            "expected": expected,
            "value": field["value"],
            "status": field.get("status", "READING"),
            "matches": field["value"] == expected,
        }
    return {
        "file_id": result["file_id"],
        "checks": checks,
        "not_verifiable": reference["not_verifiable"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", type=Path, default=(REPOSITORY_ROOT / ".context/500-sombras-de-alberto/facturas")
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=(Path(__file__).resolve().parents[1] / "tests/fixtures/scans-reviewed.json"),
    )
    parser.add_argument("--output", type=Path, default=Path("reports/scans"))
    parser.add_argument("--extractions", type=Path)
    parser.add_argument("--dpi", type=int, default=240)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    references = json.loads(args.labels.read_text(encoding="utf-8"))
    service = (
        ExtractionService(replace(Settings(), ocr_dpi=args.dpi)) if not args.extractions else None
    )
    existing = (
        {}
        if service
        else {
            r["file_id"]: r
            for r in map(json.loads, args.extractions.read_text(encoding="utf-8").splitlines())
        }
    )
    reports, counts = [], Counter()
    started = time.perf_counter()
    with (args.output / "files.jsonl").open("w", encoding="utf-8") as stream:
        for reference in references:
            path = args.input / reference["file_id"]
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            if reference.get("sha256") != sha:
                raise ValueError(f"Reference checksum mismatch: {path.name}")
            if service:
                with path.open("rb") as source:
                    result = service.extract(
                        service.ingest(source, path.name), ExtractOptions()
                    ).model_dump()
            else:
                result = existing[path.name]
                if result["sha256"] != sha:
                    raise ValueError(f"Stale extraction: {path.name}")
            stream.write(json.dumps(result, ensure_ascii=False) + "\n")
            report = compare(result, reference)
            reports.append(report)
            for check in report["checks"].values():
                counts["labeled_fields"] += 1
                counts["matching_values"] += check["matches"]
                counts["wrong_nonnull_values"] += (
                    not check["matches"] and check["value"] is not None
                )
                counts["wrong_observed_values"] += (
                    not check["matches"] and check["status"] == "OBSERVED"
                )
                counts["matching_observed_values"] += (
                    check["matches"] and check["status"] == "OBSERVED"
                )
    (args.output / "comparison.json").write_text(
        json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    summary = {
        "files": len(reports),
        "seconds": round(time.perf_counter() - started, 3),
        **counts,
        "note": (
            "Development labels transcribed visually by assistant; not "
            "independent human or organizer ground truth."
        ),
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
