"""Reproducible extraction audit; never claims payment accuracy without ground truth."""

import argparse
import json
import os
import platform
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path

from app.core import events
from app.features.ingestion.config import Settings
from app.features.ingestion.schemas import ExtractOptions
from app.features.ingestion.service import ExtractionService


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/extraction"))
    parser.add_argument("--no-ocr", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--mode", choices=["local", "api", "hybrid"])
    parser.add_argument("--dpi", type=int)
    parser.add_argument("--pdf-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    config = Settings()
    config = replace(
        config,
        data_dir=args.output / "cache",
        workers=args.workers or config.workers,
        ocr_mode=args.mode or config.ocr_mode,
        ocr_dpi=args.dpi or config.ocr_dpi,
    )
    service = ExtractionService(config)
    files = sorted(args.input.rglob("*.pdf")) + (
        [] if args.pdf_only else sorted(args.input.rglob("*.xlsx"))
    )
    if args.limit:
        files = files[: args.limit]
    counts = Counter()
    issues = Counter()

    def extract(path):
        with path.open("rb") as stream:
            item = service.ingest(stream, path.name)
        return service.extract(item, ExtractOptions(ocr=not args.no_ocr))

    started = time.perf_counter()
    previous_writer = events._write
    trace_lock = threading.Lock()
    provider_counts = Counter()
    with (
        (args.output / "files.jsonl").open("w", encoding="utf-8") as report,
        (args.output / "spans.jsonl").open("w", encoding="utf-8") as traces,
    ):

        def capture(rows):
            with trace_lock:
                for row in rows:
                    traces.write(json.dumps(row, default=str, ensure_ascii=False) + "\n")
                    if row["step"] == "provider_call" and row["data"].get("network_attempted"):
                        data = row["data"]
                        provider_counts["requests"] += 1
                        provider_counts["network_ms"] += data.get("network_latency_ms", 0)
                        provider_counts["slot_wait_ms"] += data.get("slot_wait_ms", 0)
                        provider_counts["errors"] += row["status"] == "error"
                traces.flush()

        events._write = capture
        try:
            with ThreadPoolExecutor(max_workers=config.workers) as executor:
                pending = {executor.submit(extract, path): path for path in files}
                for future in as_completed(pending):
                    path = pending[future]
                    try:
                        result = future.result()
                        report.write(result.model_dump_json() + "\n")
                        counts["EXTRACTED"] += 1
                        counts["cache_hits"] += result.cache_hit
                        for reader in ("ocr", "vlm", "jev"):
                            counts[reader + "_calls"] += result.metrics.get(
                                reader + "_calls_this_request", 0
                            )
                        counts["accepted_fields"] += sum(
                            f.value is not None for f in result.fields.values()
                        )
                        if result.metrics.get("native_pages") == 0:
                            counts["scans"] += 1
                            counts["scan_accepted_fields"] += sum(
                                f.value is not None for f in result.fields.values()
                            )
                        issues.update(w["code"] for w in result.warnings)
                    except Exception as exc:
                        counts["FAILED"] += 1
                        report.write(
                            json.dumps(
                                {"file_id": path.name, "error_type": type(exc).__name__},
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                    report.flush()
        finally:
            events._write = previous_writer
            service.close()
    elapsed = time.perf_counter() - started
    summary = {
        "files": len(files),
        "workers": config.workers,
        "dpi": config.ocr_dpi,
        "readers": config.summary(),
        "providers": dict(provider_counts),
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
