"""The challenge's delivery check: one JSON line per file of a batch, nothing else.

The organisers' verifier is private; this repeats what their README states, so a bad file
is caught before it is pushed: exactly one line per file, no extra lines, valid results.
"""

import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from app.core.config import settings

RESULTS = {"PAGAR", "NO_PAGAR", "ESCALAR"}
# The codes the engine writes as a reason by itself (ADR 0028). Any other reason is the
# reason code of the rule that fired.
ENGINE_CODES = (
    "MISSING_DATA",
    "UNVERIFIED_DATA",
    "RULE_ERROR",
    "RULE_NEEDS_DATA",
    "RULE_COMPILE_FAILED",
    "RULE_CONFLICT",
    "SOURCE_UNAVAILABLE",
    "SCAN_REVIEW",
)
MAX_TEXT = 200  # a longer value is a page of text (`free_text`), not evidence for a line


def trace_url(process_id: int, instance_id: int) -> str:
    """The console screen that opens this case's trace: Revisión on that instance."""
    return f"{settings.console_base_url}/processes/{process_id}/review?i={instance_id}"


def _short(value: Any) -> str:
    text = str(value)
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + "…"


def trace_fields(
    *,
    author: str,
    reason: str | None,
    decided_at: str,
    results: list[dict[str, Any]],
    rules_hash: str | None,
    process_version: int | None,
    rules: dict[int, tuple[str, str]],  # rule id -> (summary, decision)
    symbols: dict[str, Any] | None,
    sources_read: list[dict[str, Any]],
    trace_id: str | None,
) -> dict[str, Any]:
    """The whole trace of one exported line, from what the database already holds.

    Nothing is recomputed: every value is a stored row or column, and a field with no data
    is left out rather than written as null.
    """
    fired = [r for r in results if r.get("fires")]
    codes = [p.split()[0].rstrip(":") for p in (reason or "").split(" | ") if p.strip()]
    row: dict[str, Any] = {
        "reason_code": next((c for c in codes if c in ENGINE_CODES), "RULE_MATCH" if fired else ""),
        "reason": _short(reason or ""),
        "decided_by": "engine" if author == "engine" else "person",
        "decided_at": decided_at,
        "process_version": process_version,
        "rules_hash": rules_hash,
        "rules_fired": [
            {
                "id": r["rule_id"],
                "summary": _short(rules[r["rule_id"]][0]),
                "result": rules[r["rule_id"]][1],
            }
            for r in fired
            if r["rule_id"] in rules
        ],
        "evidence": [
            {"symbol": name, "value": _short(field["value"]), "origin": field.get("origin")}
            for name, field in (symbols or {}).items()
            if field.get("value") is not None
        ],
        "sources_read": sources_read,
        "trace_id": trace_id,
    }
    return {k: v for k, v in row.items() if v not in (None, "", [])}


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
