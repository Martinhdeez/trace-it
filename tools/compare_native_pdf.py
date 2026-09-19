"""Compare native PDF evidence in two checkouts, without OCR, providers or a database.

Run with the candidate backend's Python environment. Field differences fail the gate;
layout annotations and reading order may change, but original lines may not disappear.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

READ = """
import contextlib, hashlib, json, sys, time
from pathlib import Path
from app.features.ingestion.config import Settings
from app.features.ingestion.pdf.native import native_pages
from app.features.ingestion.pdf.invoice import parse_invoice
settings = Settings(ocr_profile='experimental')
results = {}
started = time.perf_counter()
with contextlib.redirect_stdout(sys.stderr):
    for path in sorted(Path(sys.argv[1]).glob('*.pdf')):
        content = path.read_bytes()
        pages = native_pages(content, settings)
        lines = [line for page in pages for line in page['lines']]
        fields, warnings = parse_invoice(lines)
        results[path.name] = {
            'sha256': hashlib.sha256(content).hexdigest(),
            'fields': {name: value.model_dump() for name, value in fields.items()},
            'warnings': warnings,
            'lines': sorted([{'id': line.id, 'raw': line.raw, 'text': line.text,
                              'bbox': line.bbox, 'page': line.page} for line in lines],
                            key=lambda item: item['id']),
            'order': [line.id for line in lines],
        }
print(json.dumps({'documents': results, 'seconds': time.perf_counter() - started}))
"""


def read(checkout: Path, corpus: Path) -> dict:
    backend = checkout.resolve() / "backend"
    environment = {**os.environ, "PYTHONPATH": str(backend), "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        [sys.executable, "-c", READ, str(corpus.resolve())],
        cwd=backend,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    before, after = read(args.baseline, args.corpus), read(args.candidate, args.corpus)
    originals, current = before["documents"], after["documents"]
    if not originals or originals.keys() != current.keys():
        parser.error("The corpus must be non-empty and contain the same PDFs for both readers")
    changes = {name: [] for name in ("fields", "warnings", "lines", "order")}
    for filename, old in originals.items():
        new = current[filename]
        if old["sha256"] != new["sha256"]:
            parser.error(f"Document bytes changed during comparison: {filename}")
        for key in changes:
            if old[key] != new[key]:
                changes[key].append(filename)
    passed = not any(changes[key] for key in ("fields", "warnings", "lines"))
    summary = {
        "passed": passed,
        "documents": len(originals),
        "native_documents": sum(bool(doc["lines"]) for doc in originals.values()),
        "changed_documents": changes,
        "baseline_seconds": before["seconds"],
        "candidate_seconds": after["seconds"],
        "scope": "Native lines, invoice fields/candidates and parser warnings; no scan OCR calls",
    }
    rendered = json.dumps(summary, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
