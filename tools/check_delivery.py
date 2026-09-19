"""Check a delivery JSONL against the hackathon contract (`make delivery`, `delivery/README.md`).

    python3 tools/check_delivery.py delivery/outcomes.jsonl [--files <folder of PDFs>]

One JSON object per line, `file_id` (the exact PDF name) and `result` in PAGAR / NO_PAGAR /
ESCALAR, no duplicates. With `--files`, every `file_id` must be a PDF of that folder and every
PDF must have a line. Extra top-level keys are the optional trace fields: a warning, never a
failure. Exits non-zero on a contract violation. Standard library only, no backend, no LLM.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

RESULTS = ("PAGAR", "NO_PAGAR", "ESCALAR")
CONTRACT = ("file_id", "result")


def check(text: str, files: set[str] | None) -> tuple[list[str], list[str], Counter]:
    """Contract violations, warnings and the count per result of one delivery file."""
    problems: list[str] = []
    seen: Counter = Counter()
    results: Counter = Counter()
    extra: set[str] = set()
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            problems.append(f"line {n}: empty")
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            problems.append(f"line {n}: not JSON ({e.msg})")
            continue
        if not isinstance(row, dict):
            problems.append(f"line {n}: not a JSON object")
            continue
        if not isinstance(row.get("file_id"), str) or not row["file_id"]:
            problems.append(f"line {n}: no file_id")
            continue
        if row.get("result") not in RESULTS:
            problems.append(f"line {n}: result {row.get('result')!r} is not one of {RESULTS}")
        else:
            results[row["result"]] += 1
        seen[row["file_id"]] += 1
        extra |= set(row) - set(CONTRACT)
    problems += [f"{name}: {times} lines" for name, times in sorted(seen.items()) if times > 1]
    if files is not None:
        problems += [f"{name}: not a PDF of the batch" for name in sorted(seen.keys() - files)]
        problems += [f"{name}: missing" for name in sorted(files - seen.keys())]
    warnings = (
        [f"extra top-level fields (optional trace fields): {', '.join(sorted(extra))}"]
        if extra
        else []
    )
    return problems, warnings, results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", type=Path, help="The delivery JSONL to check")
    parser.add_argument("--files", type=Path, help="Folder with the batch's PDFs")
    args = parser.parse_args()
    files = (
        {p.name for p in args.files.iterdir() if p.suffix.lower() == ".pdf"} if args.files else None
    )
    text = args.output.read_text(encoding="utf-8")
    problems, warnings, results = check(text, files)
    print(f"{args.output}: {len(text.splitlines())} lines, {dict(sorted(results.items()))}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    if problems:
        sys.exit(f"NOT deliverable ({len(problems)}):\n  " + "\n  ".join(problems[:50]))
    print("OK: contract satisfied")


if __name__ == "__main__":
    main()
