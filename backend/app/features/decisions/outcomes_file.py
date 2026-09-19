"""The challenge's delivery check: one JSON line per file of a batch, nothing else.

The organisers' verifier is private; this repeats what their README states, so a bad file
is caught before it is pushed: exactly one line per file, no extra lines, valid results.
"""

import json
import unicodedata
from collections import Counter
from pathlib import Path

from app.core.config import settings

RESULTS = {"PAGAR", "NO_PAGAR", "ESCALAR"}


def trace_url(process_id: int, instance_id: int) -> str:
    """The console screen that opens this case's trace: Revisión on that instance."""
    return f"{settings.console_base_url}/processes/{process_id}/review?i={instance_id}"


def batch_files(folder: Path) -> set[str]:
    """The file names of a batch as the organisers ship them: every PDF in the folder."""
    return {p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"}


def problems(text: str, files: set[str]) -> list[str]:
    """What is wrong with an outcomes file for `files`; empty when it can be delivered."""
    found: list[str] = []
    seen: Counter[str] = Counter()
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            found.append(f"line {n}: empty")
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            found.append(f"line {n}: not JSON ({e.msg})")
            continue
        if not isinstance(row, dict) or not isinstance(row.get("file_id"), str):
            found.append(f"line {n}: no file_id")
            continue
        if row.get("result") not in RESULTS:
            found.append(f"line {n}: result {row.get('result')!r} is not one of {sorted(RESULTS)}")
        seen[row["file_id"]] += 1
    found += [f"{name}: {times} lines" for name, times in seen.items() if times > 1]
    # A name that only matches after Unicode normalisation (macOS NFD vs NFC) is reported
    # apart: it is the same file spelled with other bytes, and the verifier compares bytes.
    nfc = {unicodedata.normalize("NFC", f): f for f in files}
    for name in sorted(seen.keys() - files):
        twin = nfc.get(unicodedata.normalize("NFC", name))
        hint = f" (same as {twin!r} once normalised)" if twin else ""
        found.append(f"{name}: not a file of the batch{hint}")
    found += [f"{name}: missing" for name in sorted(files - seen.keys())]
    return found
