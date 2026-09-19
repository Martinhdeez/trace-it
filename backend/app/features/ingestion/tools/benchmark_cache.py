"""Measure local OCR reuse on difficult scans, without external provider requests.

Run from backend: python -m app.features.ingestion.tools.benchmark_cache
Each run uses a new data directory; existing results and journals are untouched.
"""

import argparse
import json
import time
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app.features.ingestion.config import REPOSITORY_ROOT, Settings
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService
from app.features.ingestion.tools.evaluate_scans import compare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=REPOSITORY_ROOT / ".context/500-sombras-de-alberto/facturas"
    )
    parser.add_argument("--models", type=Path, default=REPOSITORY_ROOT / ".models")
    parser.add_argument("--output", type=Path, default=REPOSITORY_ROOT / "reports/ocr-cache")
    parser.add_argument(
        "--files", nargs="+", default=[f"scan_{n:03}.pdf" for n in (21, 22, 23, 25, 26)]
    )
    parser.add_argument("--reparse-confidence", type=float, default=0.95)
    args = parser.parse_args()
    run = args.output / uuid4().hex[:12]
    run.mkdir(parents=True)
    settings = Settings(
        data_dir=run / "data",
        model_dir=args.models,
        workers=1,
        vlm_url=None,
        vlm_model=None,
        vlm_api_key=None,
        gemini_api_key=None,
        jev_api_key=None,
    )
    options = ExtractOptions(vlm=False, jev=False)
    refs = json.loads(
        (Path(__file__).resolve().parents[1] / "tests/fixtures/scans-reviewed.json").read_text(
            encoding="utf-8"
        )
    )
    references = {row["file_id"]: row for row in refs}
    baseline = {}
    summaries = []

    def save_trace(rows):
        traces.write("".join(json.dumps(row, default=str) + "\n" for row in rows))

    # This isolated benchmark must not write events to an application's database.
    with (
        (run / "traces.jsonl").open("w", encoding="utf-8") as traces,
        patch("app.core.events._write", save_trace),
        (run / "extractions.jsonl").open("w", encoding="utf-8") as output,
    ):
        for stage, config in (
            ("cold", settings),
            ("warm", settings),
            ("reparse", replace(settings, ocr_min_confidence=args.reparse_confidence)),
        ):
            # Separate service objects also exercise reuse across restarts.
            service = ExtractionService(config)
            for name in args.files:
                path = args.input / name
                started = time.perf_counter()
                with path.open("rb") as stream:
                    item = service.ingest(stream, name)
                result = service.extract(item, options).model_dump(mode="json")
                output.write(json.dumps({"stage": stage, **result}, ensure_ascii=False) + "\n")
                output.flush()
                values = {key: reading["value"] for key, reading in result["fields"].items()}
                if stage == "cold":
                    baseline[name] = values
                row = {
                    "stage": stage,
                    "file_id": name,
                    "sha256": result["sha256"],
                    "seconds": round(time.perf_counter() - started, 3),
                    "cache_hit": result["cache_hit"],
                    "ocr_calls": result["metrics"]["ocr_calls_this_request"],
                    "ocr_cache_hits": result["metrics"]["ocr_cache_hits_this_request"],
                    "values_unchanged": values == baseline[name],
                    "confidence_threshold": config.ocr_min_confidence,
                }
                if name in references:
                    reference = references[name]
                    if reference["sha256"] != result["sha256"]:
                        raise ValueError(f"Reference checksum mismatch: {name}")
                    checks = compare(result, reference)["checks"].values()
                    row.update(
                        labeled_fields=len(reference["fields"]),
                        matching_values=sum(check["matches"] for check in checks),
                        wrong_nonnull_values=sum(
                            not check["matches"] and check["value"] is not None for check in checks
                        ),
                    )
                summaries.append(row)
                print(json.dumps(row), flush=True)
    (run / "summary.json").write_text(
        json.dumps(
            {
                "runs": summaries,
                "limitations": "Local-only development references, not official ground truth. "
                "Reparse changes the confidence threshold and may change field acceptance. "
                "Cold timings include lazy model loading. No remote provider requests.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Report: {run}")


if __name__ == "__main__":
    main()
