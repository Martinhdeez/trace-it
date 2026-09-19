"""Capture real extraction runs for old/new corpora without modifying application state."""

import argparse
import concurrent.futures
import hashlib
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--env", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("local", "hybrid", "api"), default="hybrid")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument(
        "--sources", type=Path, help="Reference snapshot for source-triggered checks"
    )
    parser.add_argument(
        "--reuse-readers",
        type=Path,
        help="Copy immutable reader responses for a controlled comparison",
    )
    args = parser.parse_args()
    sys.path.insert(0, str(args.backend.resolve()))
    from dotenv import load_dotenv

    if args.env:
        load_dotenv(args.env)
    from app.core import events
    from app.features.ingestion.config import Settings
    from app.features.ingestion.payment_verification import extract_for_payment, payment_symbols
    from app.features.ingestion.schemas import ExtractOptions
    from app.features.ingestion.service import ExtractionService

    args.output.mkdir(parents=True, exist_ok=True)
    if args.reuse_readers:
        for name in ("provider-journal", "reader-cache"):
            shutil.copytree(
                args.reuse_readers / "cache" / name,
                args.output / "cache" / name,
                dirs_exist_ok=True,
            )
    sources = json.loads(args.sources.read_text(encoding="utf-8")) if args.sources else None
    # Standalone diagnostics keep traces alongside the report, not in the application DB.
    events._write = lambda rows: None
    settings = Settings(
        data_dir=args.output / "cache",
        model_dir=args.models.resolve(),
        ocr_mode=args.mode,
        ocr_profile="experimental",
        workers=args.workers,
    )
    service = ExtractionService(settings)
    (args.output / "config.json").write_text(
        json.dumps(settings.summary(), indent=2), encoding="utf-8"
    )
    names = {
        "issuer_nif",
        "iban",
        "date",
        "purchase_order",
        "base",
        "vat_rate",
        "vat_amount",
        "total",
        "currency",
        "file_id",
        "free_text",
        "invoice_number",
    }
    paths = [
        p
        for folder in ("facturas", "facturas_primin")
        for p in sorted((args.data / folder).glob("*.pdf"))
    ]
    started = time.monotonic()

    def extract(path):
        target = args.output / path.parent.name / (path.name + ".json")
        target.parent.mkdir(exist_ok=True)
        with path.open("rb") as stream:
            item = service.ingest(stream, path.name)
        options = ExtractOptions(mode=args.mode)
        result = (
            extract_for_payment(service, item, options, sources).result
            if sources
            else service.extract(item, options)
        )
        record = result.model_dump(mode="json")
        record["symbols"] = payment_symbols(result, names)
        target.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        print(path.parent.name, path.name, result.metrics.get("request_ms"), flush=True)
        return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        records = list(pool.map(extract, paths))
    totals = Counter()
    for row in records:
        for key in ("ocr_calls", "vlm_calls", "jev_calls"):
            totals[key] += row["metrics"].get(key, 0)
    summary = {
        "files": len(records),
        "seconds": round(time.monotonic() - started, 2),
        "calls": dict(totals),
        "manifest": {
            str(p.relative_to(args.data)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
        },
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "manifest"}), flush=True)


if __name__ == "__main__":
    main()
