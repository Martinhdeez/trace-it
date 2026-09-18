"""Reproducible extraction audit; never claims payment accuracy without ground truth."""

import argparse
import json
import os
import platform
import time
from collections import Counter
from pathlib import Path

from app.features.ingestion.config import Settings
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/extraction"))
    parser.add_argument("--no-ocr", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    service = ExtractionService(Settings())
    files = sorted(args.input.rglob("*.pdf")) + sorted(args.input.rglob("*.xlsx"))
    if args.limit:
        files = files[: args.limit]
    counts = Counter()
    issues = Counter()
    started = time.perf_counter()
    with (args.output / "files.jsonl").open("w", encoding="utf-8") as report:
        for path in files:
            try:
                with path.open("rb") as stream:
                    item = service.ingest(stream, path.name)
                result = service.extract(item, ExtractOptions(ocr=not args.no_ocr))
                report.write(result.model_dump_json() + "\n")
                counts[result.status] += 1
                counts["cache_hits"] += result.cache_hit
                counts["ocr_calls"] += result.metrics["ocr_calls_this_request"]
                counts["vlm_calls"] += result.metrics["vlm_calls_this_request"]
                issues.update(w["code"] for w in result.warnings)
            except Exception as exc:
                counts["FAILED"] += 1
                report.write(
                    json.dumps({"file_id": path.name, "error": str(exc)}, ensure_ascii=False) + "\n"
                )
    elapsed = time.perf_counter() - started
    summary = {
        "files": len(files),
        "seconds": round(elapsed, 3),
        "files_per_second": round(len(files) / max(elapsed, 0.001), 2),
        "counts": dict(counts),
        "warnings": dict(issues),
        "python": platform.python_version(),
        "os": platform.platform(),
        "cpu_threads": os.cpu_count(),
        "note": "Extraction completeness and observed anomalies, NOT ground-truth payment accuracy",
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
